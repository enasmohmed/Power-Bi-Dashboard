from datetime import datetime, timedelta, timezone as dt_utc
from django import forms
from django.contrib import admin
from django.shortcuts import render, redirect
from django.urls import path
from django.contrib import messages
from django.utils import timezone
from .models import MeetingPoint, InboundShipmentRemark, WarehouseAccountOverview, CapacityVolume, WarehouseImportLog


def _warehouse_available_dates():
    """تواريخ لها داتا (نفس .dates() اللي بيستخدم UTC في الداتابيز)."""
    return list(
        WarehouseAccountOverview.objects.dates("created_at", "day", order="DESC")
    )


def _warehouse_last_import_date():
    """تاريخ آخر ملف إكسل اترفع (شيت Warehouse) — الافتراضي في الأدمن والهوم."""
    last = WarehouseImportLog.objects.order_by("-imported_at").first()
    return last.effective_date if last else None


def _warehouse_day_range(target_date):
    """نطاق اليوم بـ UTC (للاستيراد والحذف)."""
    start = datetime.combine(target_date, datetime.min.time()).replace(tzinfo=dt_utc.utc)
    return start, start + timedelta(days=1)


class WarehouseDayFilter(admin.SimpleListFilter):
    title = "Day"
    parameter_name = "day"

    def lookups(self, request, model_admin):
        dates = _warehouse_available_dates()
        return [(d.strftime("%Y-%m-%d"), d.strftime("%d %b %Y")) for d in dates]

    def queryset(self, request, queryset):
        value = self.value()
        dates = _warehouse_available_dates()
        dates_set = {d for d in dates}
        last_import = _warehouse_last_import_date()
        last_data_date = (last_import if last_import and last_import in dates_set else None) or (
            dates[0] if dates else timezone.now().date()
        )
        if value is None:
            target_date = last_data_date
        else:
            try:
                target_date = datetime.strptime(value, "%Y-%m-%d").date()
            except ValueError:
                return queryset
        # نفس منطق .dates() حتى يطابق قائمة التواريخ ويظهر الداتا (created_at__date)
        return queryset.filter(created_at__date=target_date)


class ZeroAsNoDataInput(forms.NumberInput):
    """قيمة فارغة أو No Data = لا تظهر رقم؛ الصفر يظهر 0."""
    attrs = {"placeholder": "No Data"}

    def get_context(self, name, value, attrs):
        if value is None or (isinstance(value, str) and value.strip() == ""):
            value = ""
        attrs = {**(self.attrs or {}), **(attrs or {})}
        attrs.setdefault("placeholder", "No Data")
        return super().get_context(name, value, attrs)


def _clean_metric(v):
    """فارغ / No Data → NULL في الداتابيز؛ 0 يبقى 0."""
    if v is None or v == "":
        return None
    if isinstance(v, str):
        s = v.strip()
        if not s:
            return None
        if s.lower() in ("no data", "nodata", "n/a", "na", "#n/a", "-", "—"):
            return None
        try:
            return int(s, 10)
        except ValueError:
            return None
    try:
        return int(v)
    except (ValueError, TypeError):
        return None


class WarehouseAccountOverviewChangelistForm(forms.ModelForm):
    """الأرقام: 0 أو رقم؛ الفراغ أو نص No Data يحفظ كـ NULL."""
    class Meta:
        model = WarehouseAccountOverview
        fields = "__all__"

    def clean_capacity(self):
        return _clean_metric(self.cleaned_data.get("capacity"))

    def clean_clearance(self):
        return _clean_metric(self.cleaned_data.get("clearance"))

    def clean_inbound(self):
        return _clean_metric(self.cleaned_data.get("inbound"))

    def clean_outbound(self):
        return _clean_metric(self.cleaned_data.get("outbound"))

    def clean_transportation(self):
        return _clean_metric(self.cleaned_data.get("transportation"))

    def clean_pods(self):
        return _clean_metric(self.cleaned_data.get("pods"))

    def clean_occupied_location(self):
        return _clean_metric(self.cleaned_data.get("occupied_location"))

    def clean_created_at(self):
        """
        عند التعديل من شاشة الـ changelist:
        - لو تركتِ خانة التاريخ فاضية، نحافظ على نفس قيمة created_at القديمة
          حتى لا تختفي الصفوف من التقارير والهوم.
        - لو كان الصف جديدًا تمامًا بدون تاريخ، نستخدم تاريخ اليوم.
        """
        value = self.cleaned_data.get("created_at")
        if value in (None, ""):
            if self.instance and self.instance.pk:
                return self.instance.created_at or timezone.now()
            return timezone.now()
        return value


@admin.register(WarehouseAccountOverview)
class WarehouseAccountOverviewAdmin(admin.ModelAdmin):
    list_display = (
        "warehouse",
        "account",
        "capacity_display",
        "clearance_display",
        "inbound_display",
        "outbound_display",
        "transportation_display",
        "pods_display",
        "occupied_location_display",
        "updated_at",
        "created_at",
    )
    list_editable = ("created_at",)
    list_filter = ("warehouse", WarehouseDayFilter)  # لا نضيف created_at لتفادي تعارضه مع فلتر Day
    search_fields = ("warehouse", "account")
    ordering = ("warehouse", "account")
    change_list_template = "admin/dashboard/warehouseaccountoverview/change_list.html"
    date_hierarchy = None
    form = WarehouseAccountOverviewChangelistForm

    def formfield_for_dbfield(self, db_field, request, **kwargs):
        if db_field.name in ("capacity", "clearance", "inbound", "outbound", "transportation", "pods", "occupied_location"):
            kwargs["widget"] = ZeroAsNoDataInput()
        return super().formfield_for_dbfield(db_field, request, **kwargs)

    def get_changelist_form(self, request, **kwargs):
        form = super().get_changelist_form(request, **kwargs)
        for fname in ("capacity", "clearance", "inbound", "outbound", "transportation", "pods", "occupied_location"):
            if fname in form.base_fields:
                form.base_fields[fname].required = False
        return form

    @staticmethod
    def _display_metric(obj, raw_field, num_field):
        raw_val = getattr(obj, raw_field, None)
        if raw_val is not None and str(raw_val).strip() != "":
            return raw_val
        return getattr(obj, num_field, None)

    def capacity_display(self, obj):
        return self._display_metric(obj, "capacity_raw", "capacity")

    capacity_display.short_description = "Capacity"

    def clearance_display(self, obj):
        return self._display_metric(obj, "clearance_raw", "clearance")

    clearance_display.short_description = "Clearance"

    def inbound_display(self, obj):
        return self._display_metric(obj, "inbound_raw", "inbound")

    inbound_display.short_description = "Inbound"

    def outbound_display(self, obj):
        return self._display_metric(obj, "outbound_raw", "outbound")

    outbound_display.short_description = "Outbound"

    def transportation_display(self, obj):
        return self._display_metric(obj, "transportation_raw", "transportation")

    transportation_display.short_description = "Transportation"

    def pods_display(self, obj):
        return self._display_metric(obj, "pods_raw", "pods")

    pods_display.short_description = "PODs"

    def occupied_location_display(self, obj):
        return self._display_metric(obj, "occupied_location_raw", "occupied_location")

    occupied_location_display.short_description = "Occupied Location"

    def changelist_view(self, request, extra_context=None):
        # لو warehouse__exact فاضي في الرابط، نوجّه بدونه حتى يظهر كل الشيت لليوم (كل المستودعات)
        if request.GET.get("warehouse__exact") == "":
            from django.http import HttpResponseRedirect
            from urllib.parse import urlencode
            q = request.GET.copy()
            q.pop("warehouse__exact", None)
            return HttpResponseRedirect(request.path + ("?" + q.urlencode() if q else ""))
        dates = _warehouse_available_dates()
        dates_set = {d for d in dates}
        last_import = _warehouse_last_import_date()
        last_data_date = (last_import if last_import and last_import in dates_set else None) or (dates[0] if dates else timezone.now().date())
        day_param = (request.GET.get("day") or "").strip()
        try:
            selected_date = datetime.strptime(day_param, "%Y-%m-%d").date() if day_param else last_data_date
        except ValueError:
            selected_date = last_data_date
        # إعادة توجيه عند عدم وجود day لضبط الفلتر على تاريخ آخر رفع إكسل (أو آخر تاريخ فيه داتا)
        # ملاحظة: لا نعمل إعادة توجيه إذا لم يكن هناك أي تواريخ بيانات (لتجنّب حلقة redirect لا نهائية).
        if not day_param and dates:
            from django.http import HttpResponseRedirect
            from urllib.parse import urlencode
            q = request.GET.copy()
            q["day"] = last_data_date.strftime("%Y-%m-%d")
            return HttpResponseRedirect(request.path + "?" + q.urlencode())
        # لو التاريخ المختار مش في القائمة نوجّه لآخر رفع (أو آخر تاريخ فيه داتا)
        # بشرط أن تكون هناك تواريخ متاحة فعلاً، وإلا نعرض القائمة كما هي بدون redirect.
        available_set = {d for d in dates}
        if dates and selected_date not in available_set:
            from django.http import HttpResponseRedirect
            from urllib.parse import urlencode
            q = request.GET.copy()
            q["day"] = last_data_date.strftime("%Y-%m-%d")
            return HttpResponseRedirect(request.path + "?" + q.urlencode())
        # قائمة المستودعات للتاريخ المحدد (نفس فلتر created_at__date)
        day_filtered = WarehouseAccountOverview.objects.filter(created_at__date=selected_date)
        warehouse_choices = list(day_filtered.values_list("warehouse", flat=True).distinct().order_by("warehouse"))
        extra_context = extra_context or {}
        extra_context["warehouse_available_dates"] = dates
        extra_context["warehouse_selected_date"] = selected_date
        extra_context["warehouse_choices"] = warehouse_choices
        return super().changelist_view(request, extra_context)

    def get_urls(self):
        urls = super().get_urls()
        custom = [
            path("import-excel/", self.admin_site.admin_view(self.import_excel_view), name="operations_warehouseaccountoverview_import"),
            path("delete-day/", self.admin_site.admin_view(self.delete_day_view), name="operations_warehouseaccountoverview_delete_day"),
        ]
        return custom + urls

    def delete_day_view(self, request):
        """Delete all data for a specific day after confirmation. Requires delete permission."""
        from django.http import HttpResponse
        from django.template.response import TemplateResponse
        if not request.user.has_perm("operations.delete_warehouseaccountoverview"):
            messages.error(request, "You don't have permission to delete Warehouse and Account Overview data.")
            return redirect("admin:operations_warehouseaccountoverview_changelist")
        day_param = (request.GET.get("day") or request.POST.get("day") or "").strip()
        if not day_param:
            messages.error(request, "Date not specified.")
            return redirect("admin:operations_warehouseaccountoverview_changelist")
        try:
            target_date = datetime.strptime(day_param, "%Y-%m-%d").date()
        except ValueError:
            messages.error(request, "Invalid date format. Please use YYYY-MM-DD.")
            return redirect("admin:operations_warehouseaccountoverview_changelist")
        qs = WarehouseAccountOverview.objects.filter(created_at__date=target_date)
        count = qs.count()
        if request.method == "POST" and request.POST.get("confirm") == "yes":
            qs.delete()
            messages.success(request, f"Deleted {count} row(s) for {target_date.strftime('%Y-%m-%d')}.")
            return redirect("admin:operations_warehouseaccountoverview_changelist")
        context = {
            "title": "Delete Day Data",
            "opts": self.model._meta,
            "target_date": target_date,
            "day_param": day_param,
            "count": count,
        }
        return TemplateResponse(
            request,
            "admin/dashboard/warehouseaccountoverview/delete_day_confirm.html",
            context,
        )

    def import_excel_view(self, request):
        from .excel_import import import_operations_excel
        if request.method == "POST" and request.FILES.get("excel_file"):
            effective_date_str = (request.POST.get("effective_date") or "").strip()
            try:
                effective_date = (
                    datetime.strptime(effective_date_str, "%Y-%m-%d").date()
                    if effective_date_str
                    else timezone.now().date()
                )
            except Exception:
                effective_date = timezone.now().date()
            ok, message = import_operations_excel(
                request.FILES["excel_file"],
                effective_date=effective_date,
                sheet_name=request.POST.get("sheet_name", ""),
            )
            if ok:
                messages.success(request, message)
                return redirect("admin:operations_warehouseaccountoverview_changelist")
            messages.error(request, message)
            return redirect("admin:operations_warehouseaccountoverview_import")
        context = {
            "title": "Import from Excel — Warehouse and Account Overview",
            "opts": self.model._meta,
            "default_effective_date": timezone.now().date().isoformat(),
        }
        return render(request, "admin/dashboard/warehouseaccountoverview/import_excel.html", context)


@admin.register(CapacityVolume)
class CapacityVolumeAdmin(admin.ModelAdmin):
    list_display = ("warehouse", "capacity", "updated_at")
    list_editable = ("capacity",)
    search_fields = ("warehouse",)
    ordering = ("warehouse",)


@admin.register(InboundShipmentRemark)
class InboundShipmentRemarkAdmin(admin.ModelAdmin):
    list_display = ("shipment_nbr", "facility", "remark_short", "updated_at")
    list_editable = ()
    list_filter = ("facility",)
    search_fields = ("shipment_nbr", "facility", "remark")
    ordering = ("-updated_at",)

    def remark_short(self, obj):
        return (obj.remark[:50] + "…") if obj.remark and len(obj.remark) > 50 else (obj.remark or "")

    remark_short.short_description = "Remark"


@admin.register(MeetingPoint)
class MeetingPointAdmin(admin.ModelAdmin):
    list_display = ("description", "is_done", "created_at", "target_date")
    list_editable = ("is_done", "target_date",)
    list_filter = ("is_done", "created_at", "target_date")
    search_fields = ("description",)
    ordering = ("-created_at", "target_date", "assigned_to")

    # ✅ السماح بتعديل created_at من صفحة التفاصيل
    fields = ("description", "is_done", "created_at", "target_date", "assigned_to")
