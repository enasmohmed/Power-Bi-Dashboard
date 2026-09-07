import calendar
import json
from io import BytesIO
from datetime import datetime, date

import pandas as pd
from django.contrib import messages
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib.auth.mixins import LoginRequiredMixin
from django.db import transaction
from django.db.models import Sum
from django.http import JsonResponse, HttpResponseForbidden, HttpResponse
from django.shortcuts import render, redirect
from django.urls import reverse
from django.utils.decorators import method_decorator
from django.views import View
from django.views.decorators.csrf import csrf_exempt
from django.views.generic import TemplateView

from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer


from .forms import (
    AdminDataForm,
    AdminInboundForm,
    AdminOutboundForm,
    AdminReturnsForm,
    AdminCapacityForm,
    AdminInventoryForm,
)
from .models import (
    AdminInbound,
    AdminOutbound,
    AdminReturns,
    AdminCapacity,
    AdminInventory,
    AdminData,
    EmployeeProfile,
    Company,
)


#### View Dashborad Admin
class DashboardView(LoginRequiredMixin, TemplateView):
    template_name = "index.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        current_user = self.request.user

        # Filter AdminData entries by current user
        admin_data_entries = AdminData.objects.filter(user=current_user)

        context["admin_data_entries"] = admin_data_entries
        context["breadcrumb"] = {
            "title": "Healthcare Dashboard",
            "parent": "Dashboard",
            "child": "Default",
        }

        hc_business = self.request.GET.get("hc_business")
        year = self.request.GET.get("year")
        month = self.request.GET.get("month")
        day = self.request.GET.get("day")

        # Retrieve all data without role-specific filters
        inbound_data = AdminInbound.objects.all()
        outbound_data = AdminOutbound.objects.all()
        returns_data = AdminReturns.objects.all()
        capacity_data = AdminCapacity.objects.all()
        inventory_data = AdminInventory.objects.all()

        # Apply optional filters based on query parameters
        if hc_business:
            inbound_data = inbound_data.filter(
                admin_data__company__hc_business=hc_business
            )
            outbound_data = outbound_data.filter(
                admin_data__company__hc_business=hc_business
            )
            returns_data = returns_data.filter(
                admin_data__company__hc_business=hc_business
            )
            capacity_data = capacity_data.filter(
                admin_data__company__hc_business=hc_business
            )
            inventory_data = inventory_data.filter(
                admin_data__company__hc_business=hc_business
            )

        if year:
            inbound_data = inbound_data.filter(time__year=year)
            outbound_data = outbound_data.filter(time__year=year)
            returns_data = returns_data.filter(time__year=year)
            capacity_data = capacity_data.filter(time__year=year)
            inventory_data = inventory_data.filter(time__year=year)

        if month:
            inbound_data = inbound_data.filter(time__month=month)
            outbound_data = outbound_data.filter(time__month=month)
            returns_data = returns_data.filter(time__month=month)
            capacity_data = capacity_data.filter(time__month=month)
            inventory_data = inventory_data.filter(time__month=month)

        if day:
            inbound_data = inbound_data.filter(time__day=day)
            outbound_data = outbound_data.filter(time__day=day)
            returns_data = returns_data.filter(time__day=day)
            capacity_data = capacity_data.filter(time__day=day)
            inventory_data = inventory_data.filter(time__day=day)

        # Inbound
        context["total_vehicles_daily"] = (
            inbound_data.aggregate(Sum("number_of_vehicles_daily"))[
                "number_of_vehicles_daily__sum"
            ]
            or 0
        )
        context["total_pallets"] = (
            inbound_data.aggregate(Sum("number_of_pallets"))["number_of_pallets__sum"]
            or 0
        )
        context["total_pending_shipments"] = (
            inbound_data.aggregate(Sum("pending_shipments"))["pending_shipments__sum"]
            or 0
        )
        context["total_number_of_shipments"] = (
            inbound_data.aggregate(Sum("number_of_shipments"))[
                "number_of_shipments__sum"
            ]
            or 0
        )

        context["total_quantity"] = (
            inbound_data.aggregate(Sum("total_quantity"))["total_quantity__sum"] or 0
        )

        context["total_number_of_line"] = (
            inbound_data.aggregate(Sum("number_of_line"))["number_of_line__sum"] or 0
        )

        shipment_types = ["bulk", "loose", "cold", "frozen", "ambient"]
        shipment_data = {
            stype: inbound_data.aggregate(Sum(stype))[stype + "__sum"] or 0
            for stype in shipment_types
        }
        context["shipment_data"] = shipment_data

        # Outbound
        context["tender_sum"] = (
            outbound_data.aggregate(Sum("tender"))["tender__sum"] or 0
        )
        context["private_sum"] = (
            outbound_data.aggregate(Sum("private"))["private__sum"] or 0
        )
        context["bulk_sum"] = outbound_data.aggregate(Sum("bulk"))["bulk__sum"] or 0
        context["loose_sum"] = outbound_data.aggregate(Sum("loose"))["loose__sum"] or 0
        context["lines_sum"] = outbound_data.aggregate(Sum("lines"))["lines__sum"] or 0
        context["total_quantities_sum"] = (
            outbound_data.aggregate(Sum("total_quantities"))["total_quantities__sum"]
            or 0
        )
        context["pending_orders_sum"] = (
            outbound_data.aggregate(Sum("pending_orders"))["pending_orders__sum"] or 0
        )

        context["chart_name_tender"] = "Tender"
        context["chart_name_private"] = "Private"
        context["chart_name_bulk"] = "Bulk"
        context["chart_name_loose"] = "Loose"

        # Capacity
        context["WH_storage"] = (
            capacity_data.aggregate(Sum("WH_storage"))["WH_storage__sum"] or 0
        )
        context["occupied_location"] = (
            capacity_data.aggregate(Sum("occupied_location"))["occupied_location__sum"]
            or 0
        )
        context["available_location"] = (
            capacity_data.aggregate(Sum("available_location"))[
                "available_location__sum"
            ]
            or 0
        )

        # Returns
        context["total_number_of_return"] = (
            returns_data.aggregate(Sum("number_of_return"))["number_of_return__sum"]
            or 0
        )
        context["total_number_of_lines"] = (
            returns_data.aggregate(Sum("number_of_lines"))["number_of_lines__sum"] or 0
        )
        context["total_quantities"] = (
            returns_data.aggregate(Sum("total_quantities"))["total_quantities__sum"]
            or 0
        )

        # Inventory
        context["total_last_movement"] = (
            inventory_data.aggregate(Sum("last_movement"))["last_movement__sum"] or 0
        )

        # Calculate count of years, months, and days
        year_count = AdminInbound.objects.dates("time", "year").count()
        month_count = AdminInbound.objects.dates("time", "month").count()
        day_count = AdminInbound.objects.dates("time", "day").count()

        # Get all years, months, and days
        years = AdminInbound.objects.dates("time", "year")
        months = list(calendar.month_name)[1:]
        days = range(1, 32)  # Get days of the month

        # Get all company names from AdminData
        businesses = AdminData.objects.values_list(
            "company__hc_business", flat=True
        ).distinct()

        context.update(
            {
                "year_count": year_count,
                "month_count": month_count,
                "day_count": day_count,
                "years": years,
                "months": months,
                "days": days,
                "businesses": businesses,
                "filtered_inbound": inbound_data,
                "filtered_outbound": outbound_data,
                "filtered_returns": returns_data,
                "filtered_capacity": capacity_data,
                "filtered_inventory": inventory_data,
                "hc_business": hc_business,
                "selected_year": year,
                "selected_month": month,
                "selected_day": day,
            }
        )

        # Determine user_type based on user roles
        if self.request.user.is_superuser:
            context["user_type"] = "Super Admin"
        elif self.request.user.groups.filter(name="Admin").exists():
            context["user_type"] = "Admin"
        elif self.request.user.groups.filter(name="Employee").exists():
            context["user_type"] = "Employee"
        else:
            context["user_type"] = "Unknown"

        return context


#### Edit Data Dashboard Admin


def is_employee(user):
    return user.groups.filter(name="Employee").exists()


def is_customer(user):
    return user.groups.filter(name="Customer").exists()


def is_employee(user):
    return user.groups.filter(name="Employee").exists()


@method_decorator([login_required, csrf_exempt], name="dispatch")
class AdminEditDataView(View):
    model_map = {
        "AdminData": AdminData,
        "AdminInbound": AdminInbound,
        "AdminOutbound": AdminOutbound,
        "AdminReturns": AdminReturns,
        "AdminCapacity": AdminCapacity,
        "AdminInventory": AdminInventory,
    }

    def is_employee_user(self, user):
        return user.groups.filter(name="Employee").exists()

    def is_customer_user(self, user):
        return user.groups.filter(name="Customer").exists()

    def has_permission(self, user, model_instance):
        if self.is_employee_user(user) or user.is_staff:
            return True
        return user == model_instance.user

    def get(self, request):
        user = request.user
        is_admin = user.is_staff
        is_employee = self.is_employee_user(user)
        is_customer = self.is_customer_user(user)

        dashboard_choice = request.session.get("dashboard_choice", "admin")

        if dashboard_choice not in ["admin", "customer"]:
            dashboard_choice = "admin"

        if dashboard_choice == "customer" and not (is_customer or is_employee):
            return HttpResponseForbidden(
                "You do not have permission to access this page."
            )

        user_type = "employee" if is_employee else "customer"

        if "download" in request.GET:
            if request.GET.get("format") == "pdf":
                return self.download_pdf(request)
            else:
                return self.download_excel(request)

        context = {
            "user": user,
            "is_admin": is_admin,
            "is_employee": is_employee,
            "is_customer": is_customer,
            "dashboard_choice": dashboard_choice,
            "user_type": user_type,
            "breadcrumb": {
                "title": (
                    "Admin Dashboard"
                    if dashboard_choice == "admin"
                    else "Customer Dashboard"
                ),
                "parent": "Edit Data",
                "child": "Default",
            },
        }

        if is_admin or (is_employee and dashboard_choice == "admin"):
            admin_data = AdminData.objects.filter(
                company=EmployeeProfile.objects.get(user=user).company
            )
            admin_inbound_data = AdminInbound.objects.filter(admin_data__in=admin_data)
            admin_outbound_data = AdminOutbound.objects.filter(
                admin_data__in=admin_data
            )
            admin_returns_data = AdminReturns.objects.filter(admin_data__in=admin_data)
            admin_capacity_data = AdminCapacity.objects.filter(
                admin_data__in=admin_data
            )
            admin_inventory_data = AdminInventory.objects.filter(
                admin_data__in=admin_data
            )

            context.update(
                {
                    "admin_data": admin_data,
                    "admin_inbound_data": admin_inbound_data,
                    "admin_outbound_data": admin_outbound_data,
                    "admin_returns_data": admin_returns_data,
                    "admin_capacity_data": admin_capacity_data,
                    "admin_inventory_data": admin_inventory_data,
                }
            )

        return render(request, "excel.html", context)

    def download_excel(self, request):
        user = request.user
        is_employee = self.is_employee_user(user)

        # جلب البيانات المراد تحميلها
        admin_data = AdminData.objects.filter(
            company=EmployeeProfile.objects.get(user=user).company
        )
        admin_inbound_data = AdminInbound.objects.filter(admin_data__in=admin_data)
        admin_outbound_data = AdminOutbound.objects.filter(admin_data__in=admin_data)
        admin_returns_data = AdminReturns.objects.filter(admin_data__in=admin_data)
        admin_capacity_data = AdminCapacity.objects.filter(admin_data__in=admin_data)
        admin_inventory_data = AdminInventory.objects.filter(admin_data__in=admin_data)

        # إعداد البيانات للتصدير إلى Excel
        output = BytesIO()
        with pd.ExcelWriter(output, engine="openpyxl") as writer:
            pd.DataFrame(list(admin_data.values())).to_excel(
                writer, sheet_name="AdminData"
            )
            pd.DataFrame(list(admin_inbound_data.values())).to_excel(
                writer, sheet_name="AdminInbound"
            )
            pd.DataFrame(list(admin_outbound_data.values())).to_excel(
                writer, sheet_name="AdminOutbound"
            )
            pd.DataFrame(list(admin_returns_data.values())).to_excel(
                writer, sheet_name="AdminReturns"
            )
            pd.DataFrame(list(admin_capacity_data.values())).to_excel(
                writer, sheet_name="AdminCapacity"
            )
            pd.DataFrame(list(admin_inventory_data.values())).to_excel(
                writer, sheet_name="AdminInventory"
            )

        response = HttpResponse(
            content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )
        response["Content-Disposition"] = "attachment; filename=admin_data.xlsx"
        response.write(output.getvalue())
        return response

    def download_pdf(self, request):
        user = request.user
        is_employee = self.is_employee_user(user)

        # جلب البيانات المراد تحميلها
        admin_data = AdminData.objects.filter(
            company=EmployeeProfile.objects.get(user=user).company
        )
        admin_inbound_data = AdminInbound.objects.filter(admin_data__in=admin_data)
        admin_outbound_data = AdminOutbound.objects.filter(admin_data__in=admin_data)
        admin_returns_data = AdminReturns.objects.filter(admin_data__in=admin_data)
        admin_capacity_data = AdminCapacity.objects.filter(admin_data__in=admin_data)
        admin_inventory_data = AdminInventory.objects.filter(admin_data__in=admin_data)

        # إعداد ملف PDF
        response = HttpResponse(content_type="application/pdf")
        response["Content-Disposition"] = "attachment; filename=admin_data.pdf"

        doc = SimpleDocTemplate(response, pagesize=letter)
        elements = []

        # تخصيص الأنماط
        styles = getSampleStyleSheet()
        heading_style = ParagraphStyle(
            "HeadingStyle",
            parent=styles["Heading1"],
            fontSize=16,
            textColor=colors.darkblue,
            spaceAfter=20,
        )

        normal_style = ParagraphStyle(
            "NormalStyle",
            parent=styles["Normal"],
            fontName="Helvetica",
            fontSize=12,
            textColor=colors.black,
            spaceAfter=10,
        )

        data_sets = [
            ("AdminData", admin_data),
            ("AdminInbound", admin_inbound_data),
            ("AdminOutbound", admin_outbound_data),
            ("AdminReturns", admin_returns_data),
            ("AdminCapacity", admin_capacity_data),
            ("AdminInventory", admin_inventory_data),
        ]

        for title, data in data_sets:
            # إضافة العنوان
            elements.append(Paragraph(f"{title}", heading_style))

            # إعداد البيانات كجدول
            if data.exists():  # تحقق مما إذا كان هناك بيانات
                data_list = [
                    [key for key in data.values()[0].keys()]
                ]  # إضافة العناوين كصف أول
                for item in data.values():
                    data_list.append([value for value in item.values()])  # إضافة القيم

                table = Table(data_list)
                table.setStyle(
                    TableStyle(
                        [
                            ("BACKGROUND", (0, 0), (-1, 0), colors.lightblue),
                            ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                            ("ALIGN", (0, 0), (-1, -1), "CENTER"),
                            ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
                            ("FONT", (0, 0), (-1, -1), "Helvetica", 10),  # تخصيص الخط
                            (
                                "TEXTCOLOR",
                                (0, 1),
                                (-1, -1),
                                colors.black,
                            ),  # تغيير لون النص في الصفوف
                        ]
                    )
                )
                elements.append(table)
            else:
                elements.append(
                    Paragraph(f"No data available for {title}.", normal_style)
                )

            elements.append(Spacer(0, 20))  # إضافة مساحة بعد كل جدول

        doc.build(elements)
        return response


def is_employee(user):
    return user.groups.filter(name="Employee").exists()


@method_decorator([login_required, user_passes_test(is_employee)], name="dispatch")
class AddAdminDataView(View):
    def get(self, request):
        current_user = request.user
        user_type = ""
        companies = Company.objects.none()  # default empty queryset
        preview_data = request.session.get("preview_data", {})
        selected_company_id = request.session.get("selected_company_id")

        try:
            employee_profile = EmployeeProfile.objects.get(user=request.user)
            company_name = employee_profile.company.hc_business
            user_type = "Employee"
            companies = Company.objects.filter(
                id=employee_profile.company.id
            )  # شركة واحدة فقط للـ Employee
        except EmployeeProfile.DoesNotExist:
            company_name = None
            user_type = "Unknown"
            companies = Company.objects.none()

        context = {
            "admin_data_form": AdminDataForm(user=request.user),
            "admin_inbound_form": AdminInboundForm(),
            "admin_outbound_form": AdminOutboundForm(),
            "admin_returns_form": AdminReturnsForm(),
            "admin_capacity_form": AdminCapacityForm(),
            "admin_inventory_form": AdminInventoryForm(),
            "current_user": current_user.username,
            "companies": companies,
            "user_type": user_type,
            "company_name": company_name,
            "preview_data": preview_data,  # 🟢 بيانات المعاينة من رفع الملف
            "selected_company_id": selected_company_id,  # 🟢 الشركة المختارة
            "breadcrumb": {
                "title": "Employee Dashboard",
                "parent": "Edit Data",
                "child": "Default",
            },
        }

        return render(
            request, "general/dashboard/default/components/add_admin_data.html", context
        )

    def post(self, request):
        admin_data_form = AdminDataForm(request.POST, user=request.user)
        admin_inbound_form = AdminInboundForm(request.POST)
        admin_outbound_form = AdminOutboundForm(request.POST)
        admin_returns_form = AdminReturnsForm(request.POST)
        admin_capacity_form = AdminCapacityForm(request.POST)
        admin_inventory_form = AdminInventoryForm(request.POST)

        forms = [
            admin_data_form,
            admin_inbound_form,
            admin_outbound_form,
            admin_returns_form,
            admin_capacity_form,
            admin_inventory_form,
        ]

        try:
            with transaction.atomic():
                # 🟢 لازم AdminDataForm يتحفظ الأول (أساسي)
                if admin_data_form.is_valid():
                    admin_data = admin_data_form.save(commit=False)
                    admin_data.user = request.user
                    admin_data.company = EmployeeProfile.objects.get(
                        user=request.user
                    ).company
                    admin_data.save()
                else:
                    messages.error(request, "Admin basic data is required.")
                    return redirect("administration:add_admin_data")

                # 🟢 باقي الفورمات: احفظها لو فيها داتا
                # ⚠️ مهم: البيانات الجديدة تُضاف للقديمة (تراكم) - لا يتم حذف أي بيانات قديمة
                for form in forms:
                    if form == admin_data_form:
                        continue  # ده اتحفظ فوق
                    if form.is_valid() and any(form.cleaned_data.values()):
                        instance = form.save(commit=False)
                        instance.admin_data = admin_data  # 👈 هنا
                        instance.save()  # 🟢 يضيف سجل جديد - لا يحذف القديم

            messages.success(request, "✅ Admin data added successfully.")
            return redirect("accounts:admin_dashboard")

        except Exception as e:
            messages.error(request, f"❌ Failed to save admin data. Error: {str(e)}")
            return redirect("administration:add_admin_data")


class UploadAdminDataView(LoginRequiredMixin, View):
    template_name = "components/ui-kits/tab-bootstrap/components/upload_admin_data.html"

    def get(self, request):
        companies = []
        preview_data = request.session.get("preview_data", {})

        try:
            employee_profile = EmployeeProfile.objects.get(user=request.user)
            companies = Company.objects.filter(id=employee_profile.company.id)
        except EmployeeProfile.DoesNotExist:
            pass

        if not companies.exists():
            for key in [
                "preview_data",
                "inbound_aggregations",
                "outbound_aggregations",
                "returns_aggregations",
                "capacity_aggregations",
                "inventory_aggregations",
                "selected_company_id",
            ]:
                request.session.pop(key, None)
            request.session.modified = True
            preview_data = {}

        selected_company_id = request.session.get("selected_company_id")

        return render(
            request,
            self.template_name,
            {
                "companies": companies,
                "selected_company_id": selected_company_id,
                "preview_data": preview_data,
            },
        )

    def clean_date(self, value):
        if not value or pd.isna(value):
            return None
        try:
            value = str(value).replace(""", "").replace(""", "").strip()
            return pd.to_datetime(value).date()
        except Exception:
            return None

    def convert_values(self, row):
        new_row = {}
        for key, value in row.items():
            if isinstance(value, (date, datetime)):
                new_row[key.strip()] = value.isoformat()
            else:
                new_row[key.strip()] = value
        return new_row

    def _to_int(self, v, default=0):
        try:
            if v is None or str(v).strip() == "":
                return default
            return int(float(str(v).strip()))
        except Exception:
            return default

    def post(self, request):
        try:
            company_id = request.POST.get("company")
            if not company_id:
                messages.error(request, "⚠️ من فضلك اختر الشركة قبل رفع الملف.")
                return redirect("administration:upload_admin_data")

            company = Company.objects.get(id=company_id)
            request.session["selected_company_id"] = company.id
            print(f"✅ الشركة المحددة: {company.hc_business}")

            if "excel_file" not in request.FILES:
                messages.error(request, "⚠️ من فضلك ارفع ملف Excel.")
                return redirect("administration:upload_admin_data")

            excel_file = request.FILES["excel_file"]
            print(f"📂 الملف المستلم: {excel_file.name}")
            all_sheets = pd.read_excel(
                excel_file, sheet_name=None, header=None, engine="openpyxl"
            )

            # 🟢 تنظيف السيشن قبل البدء
            for key in [
                "preview_data",
                "inbound_aggregations",
                "outbound_aggregations",
                "returns_aggregations",
                "capacity_aggregations",
                "inventory_aggregations",
            ]:
                request.session.pop(key, None)

            preview_data = {}

            # ================== معالجة كل شيت ==================
            for sheet_name, df_sheet in all_sheets.items():
                print(f"\n===== 📑 قراءة الشيت: {sheet_name} =====")
                df_sheet = df_sheet.ffill(axis=1)

                headers = df_sheet.iloc[0].astype(str).tolist()
                sub_headers = (
                    df_sheet.iloc[1].astype(str).tolist()
                    if len(df_sheet) > 1
                    else headers
                )
                df_sheet = df_sheet[2:]  # تجاهل الصفوف الأولى (الهيدر)

                df_sheet.columns = [
                    str(c).strip().replace("\n", "").replace("\r", "").lower()
                    for c in sub_headers
                ]

                rows_excel = df_sheet.fillna("").to_dict(orient="records")
                print(
                    f"📊 عدد الصفوف المقروءة من الشيت {sheet_name}: {len(rows_excel)}"
                )

                unique_rows = []

                # 🟢 Inbound
                if "inbound" in sheet_name.lower():
                    for row in rows_excel:
                        shipment_date = self.clean_date(
                            row.get("dates") or row.get("time")
                        )
                        if not shipment_date:
                            continue
                        row["time"] = shipment_date.isoformat()
                        unique_rows.append(self.convert_values(row))

                    if unique_rows:
                        df_preview = pd.DataFrame(unique_rows)
                        for col in [
                            "number of vehicles daily",
                            "number of pallet",
                            "pending shipments",
                            "total quantity",
                            "number of line",
                            "number of shipments",
                        ]:
                            if col in df_preview.columns:
                                df_preview[col] = (
                                    pd.to_numeric(df_preview[col], errors="coerce")
                                    .fillna(0)
                                    .astype(int)
                                )

                        request.session["inbound_aggregations"] = {
                            "number_of_shipments": len(df_preview),
                            "total_vehicles_daily": (
                                int(df_preview["number of vehicles daily"].sum())
                                if "number of vehicles daily" in df_preview.columns
                                else 0
                            ),
                            "total_pallets": (
                                int(df_preview["number of pallet"].sum())
                                if "number of pallet" in df_preview.columns
                                else 0
                            ),
                            "total_pending_shipments": (
                                int(df_preview["pending shipments"].sum())
                                if "pending shipments" in df_preview.columns
                                else 0
                            ),
                            "total_quantity": (
                                int(df_preview["total quantity"].sum())
                                if "total quantity" in df_preview.columns
                                else 0
                            ),
                            "total_number_of_line": (
                                int(df_preview["number of line"].sum())
                                if "number of line" in df_preview.columns
                                else 0
                            ),
                        }

                    preview_data[sheet_name.lower()] = {
                        "headers": list(df_sheet.columns),
                        "rows": unique_rows,
                    }

                # 🟢 Outbound
                elif "outbound" in sheet_name.lower():
                    for row in rows_excel:
                        shipment_date = self.clean_date(
                            row.get("dates") or row.get("time")
                        )
                        if not shipment_date:
                            continue
                        row["time"] = shipment_date.isoformat()
                        unique_rows.append(self.convert_values(row))

                    if unique_rows:
                        df_preview = pd.DataFrame(unique_rows)
                        for col in [
                            "tender",
                            "private",
                            "lines",
                            "total quantities",
                            "bulk",
                            "loose",
                            "pending orders",
                        ]:
                            if col in df_preview.columns:
                                df_preview[col] = (
                                    pd.to_numeric(df_preview[col], errors="coerce")
                                    .fillna(0)
                                    .astype(int)
                                )

                        request.session["outbound_aggregations"] = {
                            "number_of_records": len(df_preview),
                            "total_tender": (
                                int(df_preview["tender"].sum())
                                if "tender" in df_preview.columns
                                else 0
                            ),
                            "total_private": (
                                int(df_preview["private"].sum())
                                if "private" in df_preview.columns
                                else 0
                            ),
                            "total_lines": (
                                int(df_preview["lines"].sum())
                                if "lines" in df_preview.columns
                                else 0
                            ),
                            "total_quantities": (
                                int(df_preview["total quantities"].sum())
                                if "total quantities" in df_preview.columns
                                else 0
                            ),
                        }

                    preview_data[sheet_name.lower()] = {
                        "headers": list(df_sheet.columns),
                        "rows": unique_rows,
                    }

                # 🟢 Returns
                elif "returns" in sheet_name.lower():
                    temp = {}
                    for row in rows_excel:
                        parsed_date = self.clean_date(
                            row.get("dates") or row.get("time")
                        )
                        if not parsed_date:
                            continue
                        norm = {
                            "time": parsed_date.isoformat(),
                            "number_of_return": self._to_int(
                                row.get("number of return")
                                or row.get("number_of_return")
                            ),
                            "number_of_lines": self._to_int(
                                row.get("number of lines") or row.get("number_of_lines")
                            ),
                            "total_quantities": self._to_int(
                                row.get("total quantities")
                                or row.get("total_quantities")
                            ),
                        }
                        temp[norm["time"]] = norm

                    unique_rows = list(temp.values())

                    if unique_rows:
                        df_preview = pd.DataFrame(unique_rows)
                        request.session["returns_aggregations"] = {
                            "number_of_records": len(df_preview),
                            "total_number_of_return": int(
                                df_preview["number_of_return"].sum()
                            ),
                            "total_number_of_lines": int(
                                df_preview["number_of_lines"].sum()
                            ),
                            "total_quantities": int(
                                df_preview["total_quantities"].sum()
                            ),
                        }

                    preview_data[sheet_name.lower()] = {
                        "headers": [
                            "time",
                            "number_of_return",
                            "number_of_lines",
                            "total_quantities",
                        ],
                        "rows": unique_rows,
                    }

                # 🟢 Capacity
                elif "capacity" in sheet_name.lower():
                    temp = {}
                    for row in rows_excel:
                        parsed_date = self.clean_date(
                            row.get("dates") or row.get("time")
                        )
                        if not parsed_date:
                            continue
                        norm = {
                            "time": parsed_date.isoformat(),
                            "WH_storage": self._to_int(
                                row.get("wh storage")
                                or row.get("wh_storage")
                                or row.get("WH_storage")
                            ),
                            "occupied_location": self._to_int(
                                row.get("occupied location")
                                or row.get("occupied_location")
                            ),
                            "available_location": self._to_int(
                                row.get("available location")
                                or row.get("available_location")
                            ),
                        }
                        temp[norm["time"]] = norm

                    unique_rows = list(temp.values())

                    if unique_rows:
                        df_preview = pd.DataFrame(unique_rows)
                        request.session["capacity_aggregations"] = {
                            "number_of_days": len(df_preview),
                            "total_WH_storage": int(df_preview["WH_storage"].sum()),
                            "total_occupied_location": int(
                                df_preview["occupied_location"].sum()
                            ),
                            "total_available_location": int(
                                df_preview["available_location"].sum()
                            ),
                        }

                    preview_data[sheet_name.lower()] = {
                        "headers": [
                            "time",
                            "WH_storage",
                            "occupied_location",
                            "available_location",
                        ],
                        "rows": unique_rows,
                    }

                # 🟢 Inventory
                elif "inventory" in sheet_name.lower():
                    temp = {}
                    for row in rows_excel:
                        parsed_date = self.clean_date(
                            row.get("dates") or row.get("time")
                        )
                        if not parsed_date:
                            continue
                        norm = {
                            "time": parsed_date.isoformat(),
                            "last_movement": self._to_int(
                                row.get("last movement") or row.get("last_movement")
                            ),
                        }
                        temp[norm["time"]] = norm

                    unique_rows = list(temp.values())
                    preview_data[sheet_name.lower()] = {
                        "headers": ["time", "last_movement"],
                        "rows": unique_rows,
                    }

            # 🟢 حفظ preview في السيشن
            request.session["preview_data"] = preview_data
            request.session.modified = True

            messages.success(request, "✅ تم رفع الملف وعرض البيانات بنجاح.")
            return redirect("administration:upload_admin_data")

        except Exception as e:
            import traceback

            print(traceback.format_exc())
            messages.error(request, f"❌ خطأ أثناء قراءة الملف: {e}")
            return redirect("administration:upload_admin_data")


class SaveUploadedAdminDataView(LoginRequiredMixin, View):
    def parse_date(self, value):
        if not value:
            return None
        if isinstance(value, datetime):
            return value.date()
        try:
            return datetime.fromisoformat(str(value)).date()
        except Exception:
            try:
                return pd.to_datetime(value).date()
            except Exception:
                return None

    def _to_int(self, v, default=0):
        try:
            if v is None or str(v).strip() == "":
                return default
            return int(float(str(v).strip()))
        except Exception:
            return default

    def post(self, request):
        import json, ast
        from datetime import datetime
        from django.db import transaction

        try:
            company_id = request.session.get("selected_company_id")
            if not company_id:
                messages.error(request, "⚠️ من فضلك اختر الشركة أو ارفع الملف أولاً.")
                return redirect("administration:upload_admin_data")

            company = Company.objects.get(id=company_id)
            preview_data = request.session.get("preview_data", {})
            if not preview_data:
                messages.error(
                    request, "⚠️ لا توجد بيانات محفوظة للتحميل. ارفع ملف أولاً."
                )
                return redirect("administration:upload_admin_data")

            saved_counts = {}
            print(f"\n💾 بدء الحفظ للشركة: {company.hc_business}")

            # إنشاء AdminData أولاً
            employee_profile = EmployeeProfile.objects.get(user=request.user)
            # 🟢 التأكد من أن الشركة المختارة هي نفس شركة المستخدم
            if employee_profile.company.id != company.id:
                messages.error(request, "⚠️ الشركة المختارة لا تطابق شركة المستخدم.")
                return redirect("administration:upload_admin_data")

            admin_data, created = AdminData.objects.get_or_create(
                user=request.user, company=company, defaults={"total_quantities": 0}
            )

            for sheet_name, sheet_data in preview_data.items():
                rows = sheet_data.get("rows", [])
                sheet_lower = sheet_name.lower()
                print(f"\n===== 💾 حفظ البيانات من الشيت: {sheet_name} =====")
                print(f"📊 عدد الصفوف المحضّرة: {len(rows)}")

                # Safety: ensure rows are dicts
                normalized_rows = []
                for r in rows:
                    if isinstance(r, str):
                        try:
                            parsed = json.loads(r)
                        except Exception:
                            try:
                                parsed = ast.literal_eval(r)
                            except Exception:
                                print("⚠️ تعذر تحويل السطر:", r)
                                continue
                        normalized_rows.append(parsed)
                    else:
                        normalized_rows.append(r)

                # ===== Inbound =====
                if "inbound" in sheet_lower:
                    for row in normalized_rows:
                        shipment_date = self.parse_date(
                            row.get("time") or row.get("dates")
                        )
                        if not shipment_date:
                            continue

                        with transaction.atomic():
                            # 🟢 إضافة سجل جديد - لا يحذف البيانات القديمة (تراكم)
                            AdminInbound.objects.create(
                                admin_data=admin_data,
                                time=shipment_date,
                                assigned_day=shipment_date.strftime("%A"),
                                number_of_vehicles_daily=self._to_int(
                                    row.get("number_of_vehicles_daily")
                                    or row.get("number of vehicles daily")
                                ),
                                number_of_pallets=self._to_int(
                                    row.get("number_of_pallet")
                                    or row.get("number of pallet")
                                ),
                                bulk=self._to_int(row.get("bulk") or 0),
                                loose=self._to_int(row.get("loose") or 0),
                                cold=self._to_int(row.get("cold") or 0),
                                frozen=self._to_int(row.get("frozen") or 0),
                                ambient=self._to_int(row.get("ambient") or 0),
                                pending_shipments=self._to_int(
                                    row.get("pending_shipments")
                                    or row.get("pending shipments")
                                ),
                                number_of_shipments=self._to_int(
                                    row.get("number_of_shipments")
                                    or row.get("number of shipments")
                                ),
                                total_quantity=self._to_int(
                                    row.get("total_quantity")
                                    or row.get("total quantity")
                                ),
                                number_of_line=self._to_int(
                                    row.get("number_of_line")
                                    or row.get("number of line")
                                ),
                            )

                    saved_counts[sheet_lower] = saved_counts.get(sheet_lower, 0) + len(
                        normalized_rows
                    )

                # ===== Outbound =====
                elif "outbound" in sheet_lower:
                    for row in normalized_rows:
                        shipment_date = self.parse_date(
                            row.get("time") or row.get("dates")
                        )
                        if not shipment_date:
                            continue

                        with transaction.atomic():
                            # 🟢 إضافة سجل جديد - لا يحذف البيانات القديمة (تراكم)
                            AdminOutbound.objects.create(
                                admin_data=admin_data,
                                time=shipment_date,
                                assigned_day=shipment_date.strftime("%A"),
                                tender=self._to_int(row.get("tender") or 0),
                                private=self._to_int(row.get("private") or 0),
                                lines=self._to_int(row.get("lines") or 0),
                                total_quantities=self._to_int(
                                    row.get("total_quantities")
                                    or row.get("total quantities")
                                ),
                                bulk=self._to_int(row.get("bulk") or 0),
                                loose=self._to_int(row.get("loose") or 0),
                                pending_orders=self._to_int(
                                    row.get("pending_orders")
                                    or row.get("pending orders")
                                ),
                            )

                    saved_counts[sheet_lower] = saved_counts.get(sheet_lower, 0) + len(
                        normalized_rows
                    )

                # ===== Returns =====
                elif "returns" in sheet_lower:
                    for row in normalized_rows:
                        shipment_date = self.parse_date(row.get("time"))
                        if not shipment_date:
                            continue

                        with transaction.atomic():
                            # 🟢 إضافة سجل جديد - لا يحذف البيانات القديمة (تراكم)
                            AdminReturns.objects.create(
                                admin_data=admin_data,
                                time=shipment_date,
                                assigned_day=shipment_date.strftime("%A"),
                                number_of_return=self._to_int(
                                    row.get("number_of_return") or 0
                                ),
                                number_of_lines=self._to_int(
                                    row.get("number_of_lines") or 0
                                ),
                                total_quantities=self._to_int(
                                    row.get("total_quantities") or 0
                                ),
                            )

                    saved_counts[sheet_lower] = saved_counts.get(sheet_lower, 0) + len(
                        normalized_rows
                    )

                # ===== Capacity =====
                elif "capacity" in sheet_lower:
                    for row in normalized_rows:
                        shipment_date = self.parse_date(row.get("time"))
                        if not shipment_date:
                            continue

                        with transaction.atomic():
                            # 🟢 إضافة سجل جديد - لا يحذف البيانات القديمة (تراكم)
                            AdminCapacity.objects.create(
                                admin_data=admin_data,
                                time=shipment_date,
                                assigned_day=shipment_date.strftime("%A"),
                                WH_storage=self._to_int(row.get("WH_storage") or 0),
                                occupied_location=self._to_int(
                                    row.get("occupied_location") or 0
                                ),
                                available_location=self._to_int(
                                    row.get("available_location") or 0
                                ),
                            )

                    saved_counts[sheet_lower] = saved_counts.get(sheet_lower, 0) + len(
                        normalized_rows
                    )

                    # ===== Inventory =====
                elif "inventory" in sheet_lower:
                    for row in normalized_rows:
                        shipment_date = self.parse_date(row.get("time"))
                        if not shipment_date:
                            continue

                        with transaction.atomic():
                            # 🟢 إضافة سجل جديد - لا يحذف البيانات القديمة (تراكم)
                            AdminInventory.objects.create(
                                admin_data=admin_data,
                                time=shipment_date,
                                assigned_day=shipment_date.strftime("%A"),
                                last_movement=self._to_int(
                                    row.get("last_movement") or 0
                                ),
                            )

                    saved_counts[sheet_lower] = saved_counts.get(sheet_lower, 0) + len(
                        normalized_rows
                    )

            print("\n✅ ملخص الحفظ:", saved_counts)
            msg = f"✅ تم حفظ البيانات بنجاح للشركة {company.hc_business}."
            for sheet, count in saved_counts.items():
                msg += f" 🟢 {sheet}: {count} صف محفوظ."
            messages.success(request, msg)

            # نظف السيشن بعد الحفظ
            for key in [
                "preview_data",
                "inbound_aggregations",
                "outbound_aggregations",
                "returns_aggregations",
                "capacity_aggregations",
                "inventory_aggregations",
                "selected_company_id",
            ]:
                request.session.pop(key, None)
            request.session.modified = True

            return redirect("accounts:admin_dashboard")

        except Exception as e:
            import traceback

            print("❌ خطأ أثناء الحفظ:")
            print(traceback.format_exc())
            messages.error(request, f"❌ خطأ أثناء الحفظ: {e}")
            return redirect("administration:upload_admin_data")
