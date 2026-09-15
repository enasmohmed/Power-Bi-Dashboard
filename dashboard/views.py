from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin
from django.db import OperationalError, ProgrammingError
from django.db.models import Prefetch
from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
from django.views.generic import TemplateView

import copy
import json

from .daily_tracker_parse import parse_daily_tracker_workbook, tier_for_value

from .models import (
    BarrierChallenge,
    BarrierProgram,
    DashboardWorkbook,
    PickingMethodPhase,
    PickingMethodPhaseTag,
    PickingMethodProgram,
    PickingMethodSummaryCard,
    PickerPerformanceProgram,
    ProcessImprovementItem,
    ProcessImprovementProgram,
    ProductivityDashboard,
    ProductivityDashboardCard,
    RolloutPlanCard,
    RolloutProgram,
)
from .picker_performance_service import (
    build_performance_context,
    lines_from_db_rows,
)


class HomeView(LoginRequiredMixin, TemplateView):
    template_name = "productivity/home.html"

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["page"] = "productivity"
        ctx["page_title"] = "Productivity"
        ctx["kpi_footer"] = "Tamer Logistics — Warehouse Productivity"
        ctx["year_range"] = ""
        cards_qs = ProductivityDashboardCard.objects.order_by("sort_order", "id")
        dash = (
            ProductivityDashboard.objects.filter(is_active=True)
            .prefetch_related(Prefetch("cards", queryset=cards_qs))
            .order_by("-updated_at")
            .first()
        )
        ctx["productivity_dashboard"] = dash

        tag_qs = PickingMethodPhaseTag.objects.order_by("sort_order", "id")
        phase_qs = (
            PickingMethodPhase.objects.order_by("sort_order", "id").prefetch_related(
                Prefetch("tags", queryset=tag_qs)
            )
        )
        summary_qs = PickingMethodSummaryCard.objects.order_by("sort_order", "id")
        picking = (
            PickingMethodProgram.objects.filter(is_active=True)
            .prefetch_related(
                Prefetch("phases", queryset=phase_qs),
                Prefetch("summary_cards", queryset=summary_qs),
            )
            .order_by("-updated_at")
            .first()
        )
        ctx["picking_method_program"] = picking

        ch_qs = BarrierChallenge.objects.order_by("sort_order", "id")
        barrier = (
            BarrierProgram.objects.filter(is_active=True)
            .prefetch_related(Prefetch("challenges", queryset=ch_qs))
            .order_by("-updated_at")
            .first()
        )
        ctx["barrier_program"] = barrier

        card_qs = RolloutPlanCard.objects.order_by("sort_order", "id")
        rollout = (
            RolloutProgram.objects.filter(is_active=True)
            .prefetch_related(Prefetch("plan_cards", queryset=card_qs))
            .order_by("-updated_at")
            .first()
        )
        ctx["rollout_program"] = rollout

        pip_qs = ProcessImprovementItem.objects.order_by("sort_order", "id")
        pip = (
            ProcessImprovementProgram.objects.filter(is_active=True)
            .prefetch_related(Prefetch("items", queryset=pip_qs))
            .order_by("-updated_at")
            .first()
        )
        ctx["process_improvement_program"] = pip

        try:
            pp = (
                PickerPerformanceProgram.objects.filter(is_active=True)
                .prefetch_related("shifts")
                .order_by("-updated_at")
                .first()
            )
            ctx["picker_performance_program"] = pp

            line_dicts = []
            period_label = ""
            if pp is not None:
                period_label = pp.period_label or ""
                line_dicts = lines_from_db_rows(pp.shifts.all())

            ctx["picker_performance"] = build_performance_context(
                line_dicts,
                period_label=period_label,
            )
            ctx["picker_performance_workbook"] = {
                "used_file": False,
                "filename": "",
                "sheet": (pp.excel_sheet_name if pp else "") or "Data",
            }
        except (OperationalError, ProgrammingError):
            ctx["picker_performance_program"] = None
            ctx["picker_performance"] = build_performance_context([])
            ctx["picker_performance_workbook"] = {
                "used_file": False,
                "filename": "",
                "sheet": "",
            }

        plan_rail_steps = []
        for obj, anchor, label, accent in (
            (dash, "plan-productivity", "Productivity", "amber"),
            (picking, "plan-picking", "Picking method", "blue"),
            (barrier, "plan-barriers", "Barriers", "rose"),
            (rollout, "plan-rollout", "Rollout", "emerald"),
            (pip, "plan-improvements", "Improvements", "violet"),
        ):
            if obj is not None:
                plan_rail_steps.append(
                    {"anchor": anchor, "label": label, "accent": accent}
                )
        for idx, step in enumerate(plan_rail_steps, start=1):
            step["num"] = f"{idx:02d}"
        ctx["plan_rail_steps"] = plan_rail_steps

        if self.request.user.is_superuser:
            ctx["user_type"] = "Super Admin"
        elif self.request.user.groups.filter(name="Admin").exists():
            ctx["user_type"] = "Admin"
        elif self.request.user.groups.filter(name="Employee").exists():
            ctx["user_type"] = "Employee"
        else:
            ctx["user_type"] = "User"

        return ctx


SESSION_WORKBOOK_DT = "workbook_daily_tracker"
SESSION_WORKBOOK_FN = "workbook_file_name"


@login_required
@require_http_methods(["GET", "POST", "DELETE"])
def workbook_api(request):
    """
    GET: Daily Tracker payload from session upload, else from the active Admin workbook.
    POST: multipart file `file` — parse "Daily Tracker" sheet and store in session.
    DELETE: clear workbook session data (Admin default workbook is unchanged).
    """
    if request.method == "DELETE":
        request.session.pop(SESSION_WORKBOOK_DT, None)
        request.session.pop(SESSION_WORKBOOK_FN, None)
        request.session.modified = True
        return JsonResponse({"ok": True})

    if request.method == "GET":
        data = request.session.get(SESSION_WORKBOOK_DT)
        name = request.session.get(SESSION_WORKBOOK_FN)
        source = None
        if data:
            source = "session"
        else:
            wb = (
                DashboardWorkbook.objects.filter(is_active=True)
                .exclude(parsed_snapshot__isnull=True)
                .order_by("-uploaded_at")
                .first()
            )
            if wb and wb.parsed_snapshot:
                data = wb.parsed_snapshot
                name = wb.file.name.rsplit("/", 1)[-1]
                source = "admin"
        if not data:
            return JsonResponse({"ok": True, "file_name": None, "daily_tracker": None, "source": None})
        return JsonResponse({"ok": True, "file_name": name, "daily_tracker": data, "source": source})

    # POST
    f = request.FILES.get("file")
    if not f:
        return JsonResponse({"ok": False, "error": "Missing file field (expected name: file)."}, status=400)
    fname = (f.name or "").lower()
    if not fname.endswith((".xlsx", ".xlsm")):
        return JsonResponse(
            {"ok": False, "error": "Only .xlsx and .xlsm workbooks are supported."},
            status=400,
        )
    try:
        raw = f.read()
        if len(raw) > 15 * 1024 * 1024:
            return JsonResponse(
                {"ok": False, "error": "File is too large (max 15 MB)."},
                status=400,
            )
        data = parse_daily_tracker_workbook(raw)
    except ValueError as exc:
        return JsonResponse({"ok": False, "error": str(exc)}, status=400)
    except Exception:
        return JsonResponse(
            {"ok": False, "error": "Could not read that Excel file. It may be corrupt or password-protected."},
            status=400,
        )

    request.session[SESSION_WORKBOOK_DT] = data
    request.session[SESSION_WORKBOOK_FN] = f.name
    request.session.modified = True

    return JsonResponse({"ok": True, "file_name": f.name, "daily_tracker": data})


@login_required
@require_http_methods(["POST"])
def workbook_edit_api(request):
    """
    JSON body: {"picker": "...", "iso": "YYYY-MM-DD", "value": <int|null|string empty for blank>}.
    Updates the grid in session (copying from Admin workbook into session on first edit if needed).
    """
    try:
        body = json.loads(request.body.decode("utf-8"))
    except json.JSONDecodeError:
        return JsonResponse({"ok": False, "error": "Invalid JSON body."}, status=400)

    picker = (body.get("picker") or "").strip()
    iso = (body.get("iso") or "").strip()
    raw_val = body.get("value", "__missing__")

    if not picker or not iso:
        return JsonResponse({"ok": False, "error": "Missing picker or iso."}, status=400)

    data = request.session.get(SESSION_WORKBOOK_DT)
    name = request.session.get(SESSION_WORKBOOK_FN)

    if not data:
        wb = (
            DashboardWorkbook.objects.filter(is_active=True)
            .exclude(parsed_snapshot__isnull=True)
            .order_by("-uploaded_at")
            .first()
        )
        if not wb or not wb.parsed_snapshot:
            return JsonResponse(
                {"ok": False, "error": "No workbook loaded. Upload a file or add one in Admin."},
                status=400,
            )
        data = copy.deepcopy(wb.parsed_snapshot)
        name = wb.file.name.rsplit("/", 1)[-1]

    columns = data.get("columns") or []
    col_idx = None
    for i, col in enumerate(columns):
        if col.get("iso") == iso:
            col_idx = i
            break
    if col_idx is None:
        return JsonResponse({"ok": False, "error": "That date is not in the grid."}, status=400)

    row_obj = None
    for r in data.get("rows") or []:
        if r.get("picker") == picker:
            row_obj = r
            break
    if not row_obj:
        return JsonResponse({"ok": False, "error": "That picker is not in the grid."}, status=400)

    vals = row_obj.get("values")
    tiers = row_obj.get("tiers")
    if not isinstance(vals, list) or not isinstance(tiers, list):
        return JsonResponse({"ok": False, "error": "Invalid grid shape."}, status=400)
    if col_idx >= len(vals) or col_idx >= len(tiers):
        return JsonResponse({"ok": False, "error": "Column index out of range."}, status=400)

    if raw_val in ("__missing__", None, "", "—", "-"):
        n = None
    else:
        try:
            n = int(float(str(raw_val).replace(",", "")))
        except (TypeError, ValueError):
            return JsonResponse(
                {"ok": False, "error": "Enter a whole number or leave empty for a blank cell."},
                status=400,
            )

    vals[col_idx] = n
    tiers[col_idx] = tier_for_value(n)

    request.session[SESSION_WORKBOOK_DT] = data
    request.session[SESSION_WORKBOOK_FN] = name
    request.session.modified = True

    return JsonResponse({"ok": True, "file_name": name, "daily_tracker": data, "source": "session"})
