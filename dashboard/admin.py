from django.contrib import admin, messages
from django.http import HttpResponseRedirect
from django.shortcuts import get_object_or_404, render
from django.urls import path, reverse

from .forms import DashboardWorkbookAdminForm, ExcelUploadAdminForm
from .models import (
    BarrierChallenge,
    BarrierProgram,
    DashboardWorkbook,
    PickingMethodPhase,
    PickingMethodPhaseTag,
    PickingMethodProgram,
    PickingMethodSummaryCard,
    ProcessImprovementItem,
    PickerPerformanceProgram,
    PickerShiftRecord,
    ProcessImprovementProgram,
    ProductivityDashboard,
    ProductivityDashboardCard,
    RolloutPlanCard,
    RolloutProgram,
)
from .picker_performance_service import import_picker_shifts_from_excel


class ProductivityDashboardCardInline(admin.TabularInline):
    model = ProductivityDashboardCard
    extra = 1
    ordering = ("sort_order",)
    fields = ("sort_order", "icon_kind", "icon_image", "card_title", "card_text")


@admin.register(ProductivityDashboard)
class ProductivityDashboardAdmin(admin.ModelAdmin):
    list_display = ("module_number", "dashboard_title", "is_active", "card_count", "updated_at")
    list_filter = ("is_active",)
    search_fields = ("dashboard_title", "intro_text", "banner_title", "banner_text")
    inlines = (ProductivityDashboardCardInline,)
    fieldsets = (
        (
            "Module header",
            {
                "fields": ("module_number", "dashboard_title", "intro_text", "is_active"),
                "description": "Example: 01 + MODULE + Productivity Dashboard.",
            },
        ),
        (
            "Black banner",
            {
                "fields": ("banner_title", "banner_text", "banner_value"),
                "description": "Example: Overtime Cap Rule, automated notification text, and 150 hrs on the right.",
            },
        ),
    )

    @staticmethod
    def card_count(obj):
        return obj.cards.count()

    card_count.short_description = "Cards"


class PickingMethodPhaseTagInline(admin.TabularInline):
    model = PickingMethodPhaseTag
    extra = 1
    ordering = ("sort_order",)


@admin.register(PickingMethodPhase)
class PickingMethodPhaseAdmin(admin.ModelAdmin):
    list_display = ("program", "sort_order", "week_label", "theme", "main_title", "test_badge")
    list_filter = ("theme", "program")
    search_fields = ("week_label", "main_title", "description")
    ordering = ("program", "sort_order")
    inlines = (PickingMethodPhaseTagInline,)
    autocomplete_fields = ("program",)


class PickingMethodPhaseInline(admin.StackedInline):
    model = PickingMethodPhase
    extra = 0
    ordering = ("sort_order",)
    show_change_link = True
    fields = ("sort_order", "week_label", "theme", "main_title", "test_badge", "description")


class PickingMethodSummaryCardInline(admin.TabularInline):
    model = PickingMethodSummaryCard
    extra = 1
    ordering = ("sort_order",)
    fields = ("sort_order", "display_value", "label")


@admin.register(PickingMethodProgram)
class PickingMethodProgramAdmin(admin.ModelAdmin):
    list_display = ("module_number", "module_keyword", "section_title", "is_active", "updated_at")
    list_filter = ("is_active",)
    search_fields = ("section_title", "intro_text", "module_keyword", "module_number")
    inlines = (PickingMethodPhaseInline, PickingMethodSummaryCardInline)
    fieldsets = (
        (
            "Header",
            {
                "fields": ("module_number", "module_keyword", "section_title", "intro_text", "is_active"),
            },
        ),
    )


class BarrierChallengeInline(admin.StackedInline):
    model = BarrierChallenge
    extra = 0
    ordering = ("sort_order",)
    fields = (
        "sort_order",
        "title",
        "impact",
        "problem_description",
        "mitigation_text",
        "mitigation_placeholder",
    )


@admin.register(BarrierProgram)
class BarrierProgramAdmin(admin.ModelAdmin):
    list_display = ("module_number", "module_keyword", "section_title", "is_active", "updated_at")
    list_filter = ("is_active",)
    search_fields = ("section_title", "intro_text", "module_keyword", "module_number")
    inlines = (BarrierChallengeInline,)
    fieldsets = (
        (
            "Header",
            {
                "fields": ("module_number", "module_keyword", "section_title", "intro_text", "is_active"),
            },
        ),
    )


class RolloutPlanCardInline(admin.TabularInline):
    model = RolloutPlanCard
    extra = 1
    ordering = ("sort_order",)
    fields = (
        "sort_order",
        "accent_theme",
        "icon_kind",
        "icon_image",
        "card_title",
        "card_description",
    )


@admin.register(RolloutProgram)
class RolloutProgramAdmin(admin.ModelAdmin):
    list_display = ("module_number", "module_keyword", "section_title", "is_active", "updated_at")
    list_filter = ("is_active",)
    search_fields = ("section_title", "intro_text", "module_keyword", "module_number")
    inlines = (RolloutPlanCardInline,)
    fieldsets = (
        (
            "Header",
            {
                "fields": ("module_number", "module_keyword", "section_title", "intro_text", "is_active"),
            },
        ),
    )


class ProcessImprovementItemInline(admin.StackedInline):
    model = ProcessImprovementItem
    extra = 1
    ordering = ("sort_order",)
    fields = (
        "sort_order",
        "surface",
        "improvement_label",
        "category_label",
        "card_title",
        "body_text",
    )


class PickerShiftRecordInline(admin.TabularInline):
    model = PickerShiftRecord
    extra = 0
    ordering = ("work_date", "picker_name", "id")
    fields = (
        "work_date",
        "picker_name",
        "business",
        "is_pick",
        "shift_band",
        "pick_duration_min",
        "delivery_number",
    )
    readonly_fields = (
        "work_date",
        "picker_name",
        "business",
        "is_pick",
        "shift_band",
        "pick_duration_min",
        "delivery_number",
    )
    can_delete = False
    max_num = 0


@admin.register(PickerPerformanceProgram)
class PickerPerformanceProgramAdmin(admin.ModelAdmin):
    change_list_template = "admin/dashboard/pickerperformanceprogram/change_list.html"
    change_form_template = "admin/dashboard/pickerperformanceprogram/change_form.html"
    list_display = (
        "title",
        "is_active",
        "target_lines",
        "period_label",
        "shift_count",
        "updated_at",
    )
    list_filter = ("is_active",)
    search_fields = ("title", "subtitle", "period_label")
    inlines = (PickerShiftRecordInline,)
    fieldsets = (
        (
            None,
            {
                "fields": (
                    "title",
                    "subtitle",
                    "period_label",
                    "target_lines",
                    "excel_sheet_name",
                    "is_active",
                ),
                "description": "Upload Excel from Admin: use “Upload .xlsx…” / “Import Excel (.xlsx)”. The Business column is shown as company name. Import replaces all line rows for the chosen program.",
            },
        ),
    )

    @staticmethod
    def shift_count(obj):
        return obj.shifts.count()

    shift_count.short_description = "Shifts"

    def _picker_import_excel_url(self) -> str:
        name = f"admin:{self.model._meta.app_label}_{self.model._meta.model_name}_import_excel"
        return reverse(name)

    def changelist_view(self, request, extra_context=None):
        extra_context = extra_context or {}
        extra_context["picker_import_excel_url"] = self._picker_import_excel_url()
        return super().changelist_view(request, extra_context=extra_context)

    def render_change_form(self, request, context, **kwargs):
        context["picker_import_excel_url"] = self._picker_import_excel_url()
        return super().render_change_form(request, context, **kwargs)

    def get_urls(self):
        info = (self.model._meta.app_label, self.model._meta.model_name)
        urls = super().get_urls()
        custom = [
            path(
                "import-excel/",
                self.admin_site.admin_view(self.import_excel_view),
                name="%s_%s_import_excel" % info,
            ),
        ]
        return custom + urls

    def import_excel_view(self, request):
        opts = self.model._meta
        if not (self.has_change_permission(request) or self.has_add_permission(request)):
            messages.error(request, "You do not have permission to import.")
            return HttpResponseRedirect(reverse("admin:index"))

        programs = PickerPerformanceProgram.objects.order_by("-is_active", "-updated_at")
        changelist_url = reverse("admin:%s_%s_changelist" % (opts.app_label, opts.model_name))

        def _initial_program_id():
            raw_pid = request.GET.get("program")
            if raw_pid:
                try:
                    return int(raw_pid)
                except ValueError:
                    return None
            return None

        if request.method == "POST":
            form = ExcelUploadAdminForm(request.POST, request.FILES)
            pid = request.POST.get("program")
            try:
                initial_program_id = int(pid) if pid else None
            except ValueError:
                initial_program_id = None

            new_title = (request.POST.get("new_program_title") or "").strip()
            sheet_name = (request.POST.get("excel_sheet_name") or "Data").strip() or "Data"
            import_sheet_override = (request.POST.get("import_sheet_name") or "").strip()

            if programs.exists():
                if not pid:
                    messages.error(request, "Select a program.")
                elif form.is_valid():
                    program = get_object_or_404(PickerPerformanceProgram, pk=pid)
                    f = form.cleaned_data["excel_file"]
                    try:
                        n, resolved = import_picker_shifts_from_excel(
                            program,
                            f,
                            sheet_name_override=import_sheet_override or None,
                        )
                        messages.success(
                            request,
                            "Imported %s shift row(s) into “%s” (sheet %s)."
                            % (n, program, resolved),
                        )
                        return HttpResponseRedirect(changelist_url)
                    except ValueError as exc:
                        messages.error(request, str(exc))
                else:
                    messages.error(
                        request, "Choose a valid .xlsx file. " + form.errors.as_text()
                    )
            else:
                # No program row yet — create one from this page, then import into it.
                created_program = None
                if not new_title:
                    messages.error(request, "Enter a program title (new program will be created).")
                elif not form.is_valid():
                    messages.error(
                        request, "Choose a valid .xlsx file. " + form.errors.as_text()
                    )
                else:
                    f = form.cleaned_data["excel_file"]
                    created_program = PickerPerformanceProgram.objects.create(
                        title=new_title,
                        excel_sheet_name=sheet_name[:64],
                        is_active=True,
                    )
                    try:
                        n, resolved = import_picker_shifts_from_excel(created_program, f)
                        messages.success(
                            request,
                            "Created program “%s” and imported %s shift row(s) (sheet %s)."
                            % (created_program, n, resolved),
                        )
                        return HttpResponseRedirect(changelist_url)
                    except ValueError as exc:
                        messages.error(request, str(exc))
                        if created_program.shifts.count() == 0:
                            created_program.delete()

            return render(
                request,
                "admin/dashboard/pickerperformanceprogram/import_excel.html",
                {
                    "title": "Import picker shifts (Excel)",
                    "programs": PickerPerformanceProgram.objects.order_by(
                        "-is_active", "-updated_at"
                    ),
                    "opts": opts,
                    "form": form,
                    "initial_program_id": initial_program_id,
                    "new_program_title": new_title,
                    "excel_sheet_name": sheet_name,
                    "import_sheet_name": import_sheet_override,
                },
            )

        initial_program_id = _initial_program_id()

        return render(
            request,
            "admin/dashboard/pickerperformanceprogram/import_excel.html",
            {
                "title": "Import picker shifts (Excel)",
                "programs": programs,
                "opts": opts,
                "form": ExcelUploadAdminForm(),
                "initial_program_id": initial_program_id,
                "new_program_title": "",
                "excel_sheet_name": "Data",
                "import_sheet_name": "",
            },
        )


@admin.register(PickerShiftRecord)
class PickerShiftRecordAdmin(admin.ModelAdmin):
    list_display = ("program", "work_date", "picker_name", "business", "is_pick", "shift_band", "pick_duration_min")
    list_filter = ("program", "business", "shift_band", "work_date")
    search_fields = ("picker_name", "business")
    date_hierarchy = "work_date"
    ordering = ("-work_date", "picker_name")


@admin.register(DashboardWorkbook)
class DashboardWorkbookAdmin(admin.ModelAdmin):
    form = DashboardWorkbookAdminForm
    list_display = ("title", "file_basename", "is_active", "uploaded_at", "snapshot_brief")
    list_filter = ("is_active",)
    readonly_fields = ("uploaded_at", "snapshot_brief")
    fieldsets = (
        (
            None,
            {
                "fields": ("title", "file", "is_active"),
                "description": (
                    "The workbook must include a sheet named Daily Tracker with a Picker Name "
                    "column and date columns (e.g. 01-Oct). Saving validates the sheet and feeds "
                    "the public Daily Tracker tab unless a visitor uploaded a different file in "
                    "the same browser session (Zone Dispatch tab)."
                ),
            },
        ),
        ("Status", {"fields": ("uploaded_at", "snapshot_brief")}),
    )

    def file_basename(self, obj):
        if not obj or not obj.file:
            return "—"
        return obj.file.name.rsplit("/", 1)[-1]

    file_basename.short_description = "File"

    def snapshot_brief(self, obj):
        if not obj or not obj.pk:
            return "—"
        snap = obj.parsed_snapshot
        if not snap:
            return "—"
        nrows = len(snap.get("rows") or [])
        nmonths = len(snap.get("months") or [])
        return f"{nrows} picker row(s), {nmonths} month(s) in grid"

    snapshot_brief.short_description = "Parsed snapshot"

    def save_model(self, request, obj, form, change):
        snapshot = form.instance.parsed_snapshot
        super().save_model(request, obj, form, change)
        DashboardWorkbook.objects.filter(pk=obj.pk).update(parsed_snapshot=snapshot)
        if obj.is_active:
            DashboardWorkbook.objects.exclude(pk=obj.pk).filter(is_active=True).update(is_active=False)


@admin.register(ProcessImprovementProgram)
class ProcessImprovementProgramAdmin(admin.ModelAdmin):
    list_display = ("module_number", "module_keyword", "section_title", "is_active", "updated_at")
    list_filter = ("is_active",)
    search_fields = ("section_title", "intro_text", "module_keyword", "module_number")
    inlines = (ProcessImprovementItemInline,)
    fieldsets = (
        (
            "Header",
            {
                "fields": ("module_number", "module_keyword", "section_title", "intro_text", "is_active"),
            },
        ),
    )
