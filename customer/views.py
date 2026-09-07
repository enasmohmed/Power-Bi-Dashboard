import calendar
import json
import os
from datetime import datetime, date
from io import BytesIO

import pandas as pd
from dateutil import parser
from django.contrib import messages
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib.auth.mixins import LoginRequiredMixin
from django.db import transaction
from django.db.models import Sum
from django.http import HttpResponse, HttpResponseForbidden, HttpResponseBadRequest
from django.http import JsonResponse
from django.shortcuts import render, redirect
from django.urls import reverse_lazy
from django.utils.decorators import method_decorator
from django.utils.timezone import now
from django.views import View
from django.views.decorators.csrf import csrf_exempt
from django.views.generic import TemplateView, FormView
from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Spacer, Paragraph

from administration.models import AdminData

from .forms import CustomerInboundForm, CustomerForm, CustomerReturnsForm, CustomerExpiryForm, \
    CustomerDamageForm, CustomerInventoryForm, CustomerPalletLocationAvailabilityForm, \
    CustomerHSEForm, CustomerTransportationOutboundForm, CustomerWHOutboundForm
from .models import Customer, CustomerInbound, CustomerTransportationOutbound, CustomerWHOutbound, CustomerReturns, \
    CustomerExpiry, CustomerDamage, \
    CustomerInventory, CustomerPalletLocationAvailability, CustomerHSE, EmployeeProfile, UploadedExcelData


### View Customer Dashboard
@method_decorator(login_required, name='dispatch')
class CustomerDashboardView(LoginRequiredMixin, TemplateView):
    template_name = 'index.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        if not CustomerInbound.objects.exists():
            for key in ["inbound_total_shipments", "inbound_total_vehicles", "preview_data",
                        "inbound_aggregations", "wh_outbound_aggregations", "selected_company_id"]:
                self.request.session.pop(key, None)
            self.request.session.modified = True

        # Check user's group membership
        user = self.request.user
        if user.is_authenticated:
            if user.groups.filter(name='Super Admin').exists() or user.groups.filter(name='Admin').exists():
                context['is_admin'] = True
            elif user.groups.filter(name='Employee').exists():
                context['is_employee'] = True
            elif user.groups.filter(name='Customer').exists():
                context['is_customer'] = True
            else:
                context['user_type'] = 'Unknown'
        else:
            context['user_type'] = 'Anonymous'

        context['breadcrumb'] = {
            "title": "Healthcare Dashboard",
            "parent": "Dashboard",
            "child": "Default"
        }

        year = self.request.GET.get('year')
        month = self.request.GET.get('month')
        day = self.request.GET.get('day')

        # فلترة البيانات بناءً على القيم المدخلة
        inbound_data = CustomerInbound.objects.all()
        transportation_outbound_data = CustomerTransportationOutbound.objects.all()
        wh_outbound_data = CustomerWHOutbound.objects.all()
        returns_data = CustomerReturns.objects.all()
        expiry_data = CustomerExpiry.objects.all()
        damage_data = CustomerDamage.objects.all()
        inventory_data = CustomerInventory.objects.all()
        pallet_location_availability_data = CustomerPalletLocationAvailability.objects.all()
        hse_data = CustomerHSE.objects.all()

        if year:
            inbound_data = inbound_data.filter(time__year=year)
            transportation_outbound_data = transportation_outbound_data.filter(time__year=year)
            wh_outbound_data = wh_outbound_data.filter(time__year=year)
            returns_data = returns_data.filter(time__year=year)
            expiry_data = expiry_data.filter(time__year=year)
            damage_data = damage_data.filter(time__year=year)
            inventory_data = inventory_data.filter(time__year=year)
            pallet_location_availability_data = pallet_location_availability_data.filter(time__year=year)
            hse_data = hse_data.filter(time__year=year)

        if month:
            inbound_data = inbound_data.filter(time__month=month)
            transportation_outbound_data = transportation_outbound_data.filter(time__month=month)
            wh_outbound_data = wh_outbound_data.filter(time__month=month)
            returns_data = returns_data.filter(time__month=month)
            expiry_data = expiry_data.filter(time__month=month)
            damage_data = damage_data.filter(time__month=month)
            inventory_data = inventory_data.filter(time__month=month)
            pallet_location_availability_data = pallet_location_availability_data.filter(time__month=month)
            hse_data = hse_data.filter(time__month=month)

        if day:
            inbound_data = inbound_data.filter(time__day=day)
            transportation_outbound_data = transportation_outbound_data.filter(time__day=day)
            wh_outbound_data = wh_outbound_data.filter(time__day=day)
            returns_data = returns_data.filter(time__day=day)
            expiry_data = expiry_data.filter(time__day=day)
            damage_data = damage_data.filter(time__day=day)
            inventory_data = inventory_data.filter(time__day=day)
            pallet_location_availability_data = pallet_location_availability_data.filter(time__day=day)
            hse_data = hse_data.filter(time__day=day)

        # إضافة البيانات المفلترة إلى السياق
        context['inbound_data'] = inbound_data
        context['transportation_outbound_data'] = transportation_outbound_data
        context['wh_outbound_data'] = wh_outbound_data
        context['returns_data'] = returns_data
        context['expiry_data'] = expiry_data
        context['damage_data'] = damage_data
        context['inventory_data'] = inventory_data
        context['pallet_location_availability_data'] = pallet_location_availability_data
        context['hse_data'] = hse_data

        # Inbound
        # context['inbound_data'] = inbound_data
        context["number_of_shipments"] = inbound_data.count()
        # قراءة القيم الجديدة من السيشن
        # لو فيه قيم جاهزة من السيشن اعرضها، لو مش موجودة اعمل aggregations من الـ DB
        inbound_total_shipments = self.request.session.get('inbound_total_shipments')
        if inbound_data.exists():
            context['number_of_shipments'] = inbound_data.count()
        else:
            # 🟢 امسح السيشن لو مفيش بيانات
            self.request.session.pop('inbound_total_shipments', None)
            context['number_of_shipments'] = 0

        context['total_vehicles_daily'] = self.request.session.get(
            'inbound_total_vehicles',
            inbound_data.aggregate(Sum('number_of_vehicles_daily'))['number_of_vehicles_daily__sum'] or 0
        )

        context['total_vehicles_daily'] = inbound_data.aggregate(Sum('number_of_vehicles_daily'))[
                                              'number_of_vehicles_daily__sum'] or 0
        context['total_pallets'] = inbound_data.aggregate(Sum('number_of_pallets'))['number_of_pallets__sum'] or 0
        context['total_pending_shipments'] = inbound_data.aggregate(Sum('pending_shipments'))[
                                                 'pending_shipments__sum'] or 0
        context['total_number_of_shipments'] = inbound_data.aggregate(Sum('number_of_shipments'))[
                                                   'number_of_shipments__sum'] or 0

        context['total_quantity'] = inbound_data.aggregate(Sum('total_quantity'))['total_quantity__sum'] or 0

        context['total_number_of_line'] = inbound_data.aggregate(Sum('number_of_line'))['number_of_line__sum'] or 0

        shipment_types = ['bulk', 'loose', 'cold', 'frozen', 'ambient']
        shipment_data = {
            stype: inbound_data.aggregate(Sum(stype))[stype + '__sum'] or 0
            for stype in shipment_types
        }
        context['shipment_data'] = shipment_data




        # الحصول على جميع بيانات Transportation Outbound_data
        # context['transportation_outbound_data'] = transportation_outbound_data
        #
        # context['total_released_order'] = transportation_outbound_data.aggregate(Sum('released_order'))['released_order__sum'] or 0
        #
        # context['total_pending_pick_orders'] = transportation_outbound_data.aggregate(Sum('pending_pick_orders'))['pending_pick_orders__sum'] or 0
        #
        # context['total_piked_order'] = transportation_outbound_data.aggregate(Sum('piked_order'))['piked_order__sum'] or 0
        #
        # context['total_number_of_PODs_collected_on_time'] = transportation_outbound_data.aggregate(Sum('number_of_PODs_collected_on_time'))['number_of_PODs_collected_on_time__sum'] or 0
        #
        # context['total_number_of_PODs_collected_Late'] = transportation_outbound_data.aggregate(Sum('number_of_PODs_collected_Late'))['number_of_PODs_collected_Late__sum'] or 0
        #


        # الحصول على جميع بيانات WH Outbound_data
        # 🟢 WH Outbound Data
        wh_outbound_data = CustomerWHOutbound.objects.all()
        print("📦 WH Outbound Raw Count:", wh_outbound_data.count())
        print("📦 WH Outbound Sample:", list(wh_outbound_data.values()[:5]))

        context['wh_outbound_data'] = wh_outbound_data

        # 🟢 Aggregations (WH Outbound)
        context['wh_total_released_order'] = wh_outbound_data.aggregate(Sum('released_order'))[
                                                 'released_order__sum'] or 0
        context['wh_total_piked_order'] = wh_outbound_data.aggregate(Sum('piked_order'))['piked_order__sum'] or 0
        context['wh_total_pending_pick_orders'] = wh_outbound_data.aggregate(Sum('pending_pick_orders'))[
                                                      'pending_pick_orders__sum'] or 0
        context['wh_total_number_of_PODs_collected_on_time'] = \
        wh_outbound_data.aggregate(Sum('number_of_PODs_collected_on_time'))[
            'number_of_PODs_collected_on_time__sum'] or 0
        context['wh_total_number_of_PODs_collected_Late'] = \
        wh_outbound_data.aggregate(Sum('number_of_PODs_collected_Late'))['number_of_PODs_collected_Late__sum'] or 0




        # الحصول على جميع بيانات Returns
        context['returns_data'] = returns_data
        context['total_orders_items_returned'] = returns_data.aggregate(Sum('total_orders_items_returned'))[
                                                     'total_orders_items_returned__sum'] or 0
        context['total_number_of_return_items_orders_updated_on_time'] = \
            returns_data.aggregate(Sum('number_of_return_items_orders_updated_on_time'))[
                'number_of_return_items_orders_updated_on_time__sum'] or 0
        context['total_number_of_return_items_orders_updated_late'] = \
            returns_data.aggregate(Sum('number_of_return_items_orders_updated_late'))[
                'number_of_return_items_orders_updated_late__sum'] or 0

        # الحصول على جميع بيانات Expiry
        context['expiry_data'] = expiry_data
        total_expired_SKUS_disposed = expiry_data.aggregate(Sum('total_expired_SKUS_disposed'))[
                                          'total_expired_SKUS_disposed__sum'] or 0
        total_nearly_expired_1_to_3_months = expiry_data.aggregate(Sum('nearly_expired_1_to_3_months'))[
                                                 'nearly_expired_1_to_3_months__sum'] or 0
        total_nearly_expired_3_to_6_months = expiry_data.aggregate(Sum('nearly_expired_3_to_6_months'))[
                                                 'nearly_expired_3_to_6_months__sum'] or 0

        total_SKUs_expired_calculated = (
                total_expired_SKUS_disposed +
                total_nearly_expired_1_to_3_months +
                total_nearly_expired_3_to_6_months
        )

        context['expiry_data'] = expiry_data
        context['total_SKUs_expired'] = expiry_data.aggregate(Sum('total_SKUs_expired'))['total_SKUs_expired__sum'] or 0
        context['total_expired_SKUS_disposed'] = total_expired_SKUS_disposed
        context['total_nearly_expired_1_to_3_months'] = total_nearly_expired_1_to_3_months
        context['total_nearly_expired_3_to_6_months'] = total_nearly_expired_3_to_6_months
        context['total_SKUs_expired_calculated'] = total_SKUs_expired_calculated

        # Damage
        context['damage_data'] = damage_data
        context['Total_QTYs_Damaged_by_WH'] = damage_data.aggregate(Sum('Total_QTYs_Damaged_by_WH'))['Total_QTYs_Damaged_by_WH__sum'] or 0
        context['Total_Number_of_Damaged_during_receiving'] = damage_data.aggregate(Sum('Number_of_Damaged_during_receiving'))[
                'Number_of_Damaged_during_receiving__sum'] or 0
        context['Total_Araive_Damaged'] = damage_data.aggregate(Sum('Total_Araive_Damaged'))['Total_Araive_Damaged__sum'] or 0

        # Inventory
        context['inventory_data'] = inventory_data
        context['Total_Locations_match'] = inventory_data.aggregate(Sum('Total_Locations_match'))['Total_Locations_match__sum'] or 0
        context['Total_Locations_not_match'] = inventory_data.aggregate(Sum('Total_Locations_not_match'))['Total_Locations_not_match__sum'] or 0


        # PalletLocationAvailability
        user = self.request.user
        if user.groups.filter(name='Employee').exists():
            companies = EmployeeProfile.objects.filter(user=user).first().company.all()
        elif user.groups.filter(name='Customer').exists():
            companies = Customer.objects.filter(employees__user=user)
        else:
            companies = Customer.objects.none()

        # رجع كل الداتا المرتبطة بالشركة/العميل
        CustomerPalletLocationAvailability.objects.all()

        last_shipment = CustomerPalletLocationAvailability.objects.order_by('-created_at').first()
        context['last_shipment'] = last_shipment

        pallet_location_availability_data = CustomerPalletLocationAvailability.objects.all()
        context['pallet_location_availability_data'] = pallet_location_availability_data

        context['Total_Storage_Pallet'] = pallet_location_availability_data.aggregate(Sum('Total_Storage_Pallet'))[
                                              'Total_Storage_Pallet__sum'] or 0
        context['Total_Storage_pallet_empty'] = \
            pallet_location_availability_data.aggregate(Sum('Total_Storage_pallet_empty'))[
                'Total_Storage_pallet_empty__sum'] or 0

        context['Total_Storage_Bin'] = pallet_location_availability_data.aggregate(Sum('Total_Storage_Bin'))[
                                           'Total_Storage_Bin__sum'] or 0
        context['Total_occupied_pallet_location'] = \
            pallet_location_availability_data.aggregate(Sum('Total_occupied_pallet_location'))[
                'Total_occupied_pallet_location__sum'] or 0

        context['Total_Storage_Bin_empty'] = \
            pallet_location_availability_data.aggregate(Sum('Total_Storage_Bin_empty'))[
                'Total_Storage_Bin_empty__sum'] or 0


        context['Total_occupied_Bin_location'] = \
            pallet_location_availability_data.aggregate(Sum('Total_occupied_Bin_location'))[
                'Total_occupied_Bin_location__sum'] or 0

        # HSE
        context['hse_data'] = hse_data
        context['Total_Incidents_on_the_side'] = hse_data.aggregate(Sum('Total_Incidents_on_the_side'))[
                                                     'Total_Incidents_on_the_side__sum'] or 0

        # Admin
        admin_data = AdminData.objects.all()
        context['admin_data'] = admin_data.all()
        context['total_no_of_employees'] = admin_data.aggregate(Sum('total_no_of_employees'))[
                                               'total_no_of_employees__sum'] or 0

        # الحصول على جميع السنين والشهور والأيام
        years = CustomerInbound.objects.dates('time', 'year')
        months = list(calendar.month_name)[1:]
        days = range(1, 32)  # للحصول على أيام الشهر

        if self.request.user.groups.filter(name='Customer'):
            context['user_type'] = "Customer"
        elif self.request.user.groups.filter(name='Employee').exists():
            context['user_type'] = "Employee"
        else:
            context['user_type'] = "Unknown"

        context.update({
            'years': years,
            'months': months,
            'days': days,
        })
        return context


### Edit Data Form Customer
class CustomerEditDataView(View):
    model_map = {
        'Customer': Customer,
        'CustomerInbound': CustomerInbound,
        'CustomerTransportationOutbound': CustomerTransportationOutbound,
        'CustomerWHOutbound': CustomerWHOutbound,
        'CustomerReturns': CustomerReturns,
        'CustomerExpiry': CustomerExpiry,
        'CustomerDamage': CustomerDamage,
        'CustomerInventory': CustomerInventory,
        'CustomerPalletLocationAvailability': CustomerPalletLocationAvailability,
        'CustomerHSE': CustomerHSE,
    }

    def is_employee_user(self, user):
        return user.groups.filter(name='Employee').exists()

    def is_customer_user(self, user):
        return user.groups.filter(name='Customer').exists()

    @method_decorator(login_required, name='dispatch')
    @method_decorator(csrf_exempt, name='dispatch')
    def get(self, request):
        user = request.user
        is_admin = user.is_staff
        is_employee = self.is_employee_user(user)
        is_customer = self.is_customer_user(user)

        dashboard_choice = request.session.get('dashboard_choice', 'customer_dashboard')

        if dashboard_choice not in ['admin_dashboard', 'customer_dashboard']:
            dashboard_choice = 'customer_dashboard'

        if dashboard_choice == 'admin_dashboard' and not is_admin:
            return HttpResponseForbidden("You do not have permission to access this page.")

        if dashboard_choice == 'customer_dashboard' and not (is_customer or is_employee):
            return HttpResponseForbidden("You do not have permission to access this page.")

        company = None
        if is_employee:
            company = EmployeeProfile.objects.filter(user=user).first().company
        elif is_customer:
            company = Customer.objects.filter(employees__user=user).first()

        if 'download' in request.GET:
            if request.GET.get('format') == 'pdf':
                return self.download_pdf(request)
            else:
                return self.download_excel(request, company)

        context = {
            "user": user,
            "user_type": "Employee" if is_employee else "Customer",
            "is_admin": is_admin,
            "is_employee": is_employee,
            "is_customer": is_customer,
            "dashboard_choice": dashboard_choice,
            "company": company,
            "breadcrumb": {
                "title": "Admin Dashboard" if dashboard_choice == 'admin_dashboard' else "Customer Dashboard",
                "parent": "Edit Data",
                "child": "Default"
            }
        }

        if dashboard_choice == 'admin_dashboard' and is_admin:
            admin_data = AdminData.objects.all()
            context["admin_data"] = admin_data

        elif dashboard_choice == 'customer_dashboard' and company:
            if is_employee:
                companies = EmployeeProfile.objects.filter(user=user).first().company.all()
            elif is_customer:
                companies = Customer.objects.filter(employees__user=user)
            else:
                companies = Customer.objects.none()

            inbounds = CustomerInbound.objects.filter(company__in=companies)
            transportation_outbounds = CustomerTransportationOutbound.objects.filter(company__in=companies)
            wh_outbounds = CustomerWHOutbound.objects.filter(company__in=companies)
            returns = CustomerReturns.objects.filter(company__in=companies)
            expiries = CustomerExpiry.objects.filter(company__in=companies)
            damages = CustomerDamage.objects.filter(company__in=companies)
            inventories = CustomerInventory.objects.filter(company__in=companies)
            # رجع كل الداتا المرتبطة بالشركة/العميل
            shipments = CustomerPalletLocationAvailability.objects.all()

            hses = CustomerHSE.objects.filter(company__in=companies)


            context.update({
                "companies": companies,
                "inbounds": inbounds,
                "transportation_outbounds": transportation_outbounds,
                "wh_outbounds": wh_outbounds,
                "returns": returns,
                "expiries": expiries,
                "damages": damages,
                "inventories": inventories,
                "shipments": shipments,
                "hses": hses,
            })

            preview_data = request.session.get("preview_data")
            if preview_data:
                context["preview_data"] = preview_data

        return render(request, "excel.html", context)

    @method_decorator(login_required, name='dispatch')
    @method_decorator(csrf_exempt, name='dispatch')
    def post(self, request):
        user = request.user
        is_admin = user.is_staff
        is_employee = self.is_employee_user(user)
        is_customer = self.is_customer_user(user)

        dashboard_choice = request.session.get('dashboard_choice', 'customer_dashboard')

        if dashboard_choice not in ['admin_dashboard', 'customer_dashboard']:
            dashboard_choice = 'customer_dashboard'

        if dashboard_choice == 'admin_dashboard' and not is_admin:
            return JsonResponse({"success": False, "error": "Permission denied."})

        if dashboard_choice == 'customer_dashboard' and not (is_customer or is_employee):
            return JsonResponse({"success": False, "error": "Permission denied."})

        if request.FILES.get("file"):
            file = request.FILES["file"]
            try:
                if file.name.endswith(".csv"):
                    df = pd.read_csv(file)
                elif file.name.endswith((".xls", ".xlsx")):
                    df = pd.read_excel(file)
                else:
                    messages.error(request, "❌ Unsupported file format. Please upload CSV or Excel.")
                    return redirect("accounts:edit_customer_data")

                df = df.drop_duplicates()

                if 'company' not in df.columns:
                    messages.error(request, "❌ Missing 'company' column in the file.")
                    return redirect("accounts:edit_customer_data")

                invalid_companies = []
                for company_name in df['company'].unique():
                    if not Customer.objects.filter(name=company_name).exists():
                        invalid_companies.append(company_name)
                if invalid_companies:
                    messages.error(request, f"❌ These companies do not exist: {', '.join(invalid_companies)}")
                    return redirect("accounts:edit_customer_data")

                request.session["preview_data"] = df.to_dict(orient="records")
                messages.success(request, "✅ File uploaded successfully. Preview the data below.")
                return redirect("accounts:edit_customer_data")

            except Exception as e:
                messages.error(request, f"❌ Error reading file: {str(e)}")
                return redirect("accounts:edit_customer_data")

        try:
            data = json.loads(request.body)
        except json.JSONDecodeError:
            return JsonResponse({"success": False, "error": "Invalid JSON"})

        if 'update' in data:
            model_name = data['update'].get('model')
            model_id = data['update'].get('id')
            field_name = data['update'].get('field')
            new_value = data['update'].get('value')

            if model_name in self.model_map:
                model = self.model_map[model_name]
                try:
                    obj = model.objects.get(id=model_id)
                except model.DoesNotExist:
                    return JsonResponse({"success": False, "error": "Object not found"})

                setattr(obj, field_name, new_value)
                obj.save()
                return JsonResponse({"success": True, "id": obj.id})
            else:
                return JsonResponse({"success": False, "error": "Invalid model"})

        elif 'add' in data:
            model_name = data['add'].get('model')
            fields = data['add'].get('fields', {})

            if model_name in self.model_map:
                if 'company' in fields and not Customer.objects.filter(id=fields['company']).exists():
                    return JsonResponse({"success": False, "error": "Customer does not exist"})

                model = self.model_map[model_name]
                obj = model(**fields)
                obj.save()
                return JsonResponse({"success": True, "id": obj.id})
            else:
                return JsonResponse({"success": False, "error": "Invalid model"})

        elif 'delete' in data:
            model_name = data['delete'].get('model')
            model_id = data['delete'].get('id')

            if model_name in self.model_map:
                model = self.model_map[model_name]
                try:
                    obj = model.objects.get(id=model_id)
                except model.DoesNotExist:
                    return JsonResponse({"success": False, "error": "Object not found"})

                obj.delete()
                return JsonResponse({"success": True})
            else:
                return JsonResponse({"success": False, "error": "Invalid model"})

        return JsonResponse({"success": False, "error": "Invalid operation"})

    def download_excel(self, request, company):
        user = request.user
        is_admin = user.is_staff
        is_employee = self.is_employee_user(user)
        is_customer = self.is_customer_user(user)

        dashboard_choice = request.session.get('dashboard_choice', 'customer_dashboard')

        if dashboard_choice not in ['admin_dashboard', 'customer_dashboard']:
            dashboard_choice = 'customer_dashboard'

        if dashboard_choice == 'admin_dashboard' and not is_admin:
            return HttpResponseForbidden("You do not have permission to access this page.")

        if dashboard_choice == 'customer_dashboard' and not (is_customer or is_employee):
            return HttpResponseForbidden("You do not have permission to access this page.")

        company = None
        if is_employee:
            company = EmployeeProfile.objects.filter(user=user).first().company
        elif is_customer:
            company = Customer.objects.filter(employees__user=user).first()

        output = BytesIO()
        with pd.ExcelWriter(output, engine='openpyxl') as writer:
            if dashboard_choice == 'admin_dashboard' and is_admin:
                admin_data = AdminData.objects.all().values()
                pd.DataFrame(list(admin_data)).to_excel(writer, sheet_name='AdminData')
            elif dashboard_choice == 'customer_dashboard' and company:
                companies = Customer.objects.filter(employees__user=user).values()
                inbounds = CustomerInbound.objects.filter(company=company).values()
                transportation_outbounds = CustomerTransportationOutbound.objects.filter(company=company).values()
                wh_outbounds = CustomerWHOutbound.objects.filter(company=company).values()
                returns = CustomerReturns.objects.filter(company=company).values()
                expiries = CustomerExpiry.objects.filter(company=company).values()
                damages = CustomerDamage.objects.filter(company=company).values()
                inventories = CustomerInventory.objects.filter(company=company).values()
                # ✅ هنا برضو اتعدلت لـ customer
                pallet_location_availabilities = CustomerPalletLocationAvailability.objects.filter(
                    customer=company).values()
                hses = CustomerHSE.objects.filter(company=company).values()

                pd.DataFrame(list(companies)).to_excel(writer, sheet_name='Companies')
                pd.DataFrame(list(inbounds)).to_excel(writer, sheet_name='Inbounds')
                pd.DataFrame(list(transportation_outbounds)).to_excel(writer, sheet_name='TransportationOutbound')
                pd.DataFrame(list(wh_outbounds)).to_excel(writer, sheet_name='WHOutbound')
                pd.DataFrame(list(returns)).to_excel(writer, sheet_name='Returns')
                pd.DataFrame(list(expiries)).to_excel(writer, sheet_name='Expiries')
                pd.DataFrame(list(damages)).to_excel(writer, sheet_name='Damages')
                pd.DataFrame(list(inventories)).to_excel(writer, sheet_name='Inventories')
                pd.DataFrame(list(pallet_location_availabilities)).to_excel(writer,
                                                                            sheet_name='PalletLocationAvailabilities')
                pd.DataFrame(list(hses)).to_excel(writer, sheet_name='HSEs')

        response = HttpResponse(content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
        response['Content-Disposition'] = 'attachment; filename=data.xlsx'
        response.write(output.getvalue())
        return response

    def download_pdf(self, request):
        user = request.user
        is_admin = user.is_staff
        is_employee = self.is_employee_user(user)
        is_customer = self.is_customer_user(user)

        dashboard_choice = request.session.get('dashboard_choice', 'customer_dashboard')

        if dashboard_choice not in ['admin_dashboard', 'customer_dashboard']:
            dashboard_choice = 'customer_dashboard'

        if dashboard_choice == 'admin_dashboard' and not is_admin:
            return HttpResponseForbidden("You do not have permission to access this page.")

        if dashboard_choice == 'customer_dashboard' and not (is_customer or is_employee):
            return HttpResponseForbidden("You do not have permission to access this page.")

        company = None
        if is_employee:
            company = EmployeeProfile.objects.filter(user=user).first().company
        elif is_customer:
            company = Customer.objects.filter(employees__user=user).first()

        if not company:
            return HttpResponseBadRequest("Company not found for current user.")

        companies = Customer.objects.filter(id=company.id)
        inbounds = CustomerInbound.objects.filter(company__in=company)
        transportation_outbounds = CustomerTransportationOutbound.objects.filter(company=company)
        wh_outbounds = CustomerWHOutbound.objects.filter(company=company)
        returns = CustomerReturns.objects.filter(company=company)
        expiries = CustomerExpiry.objects.filter(company=company)
        damages = CustomerDamage.objects.filter(company=company)
        inventories = CustomerInventory.objects.filter(company=company)
        # ✅ هنا برضو اتعدلت لـ customer
        pallet_location_availabilities = CustomerPalletLocationAvailability.objects.filter(customer=company)
        hses = CustomerHSE.objects.filter(company=company)

        response = HttpResponse(content_type='application/pdf')
        response['Content-Disposition'] = 'attachment; filename=data-customer.pdf'

        doc = SimpleDocTemplate(response, pagesize=letter)
        elements = []

        data_sets = [
            ('Companies', companies),
            ('Inbounds', inbounds),
            ('TransportationOutbound', transportation_outbounds),
            ('WHOutbounds', wh_outbounds),
            ('Returns', returns),
            ('Expiries', expiries),
            ('Damages', damages),
            ('Inventories', inventories),
            ('Pallet Location Availabilities', pallet_location_availabilities),
            ('HSEs', hses)
        ]

        styles = getSampleStyleSheet()
        heading_style = styles['Heading1']
        normal_style = styles['Normal']

        for title, data in data_sets:
            caption_text = f"<b>{title}</b>"
            caption = Paragraph(caption_text, heading_style)
            elements.append(caption)

            data_list = [[key, value] for item in data.values() for key, value in item.items()]
            table = Table(data_list, colWidths=[200, 200])
            table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), colors.gray),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
                ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                ('INNERGRID', (0, 0), (-1, -1), 0.25, colors.black),
                ('BOX', (0, 0), (-1, -1), 0.25, colors.black),
            ]))
            elements.append(table)
            elements.append(Spacer(0, 20))

        doc.build(elements)
        return response





### Add Data Form Customer
def is_employee(user):
    return user.groups.filter(name='Employee').exists()


@method_decorator([login_required, user_passes_test(is_employee)], name='dispatch')
class AddCustomerDataView(View):

    def get(self, request):
        current_user = request.user
        user_type = ''
        companies = Customer.objects.none()  # default empty queryset

        if request.user.groups.filter(name='Super Admin').exists():
            user_type = 'Super Admin'
            companies = Customer.objects.all()  # يشوف كل الشركات
        elif request.user.groups.filter(name='Admin').exists():
            user_type = 'Admin'
            companies = Customer.objects.all()
        elif request.user.groups.filter(name='Employee').exists():
            user_type = 'Employee'
            profile = EmployeeProfile.objects.filter(user=request.user).first()
            if profile:
                companies = profile.company.all()  # 🟢 ManyToMany
        elif request.user.groups.filter(name='Customer').exists():
            user_type = 'Customer'
            companies = Customer.objects.filter(employees__user=request.user)

        context = {
            'customer_form': CustomerForm(user=request.user),
            'customer_inbound_form': CustomerInboundForm(),
            'customer_transportation_outbound_form': CustomerTransportationOutboundForm(),
            'customer_wh_outbound_form': CustomerWHOutboundForm(),
            'customer_returns_form': CustomerReturnsForm(),
            'customer_expiry_form': CustomerExpiryForm(),
            'customer_damage_form': CustomerDamageForm(),
            'customer_inventory_form': CustomerInventoryForm(),
            'customer_pallet_location_availability_form': CustomerPalletLocationAvailabilityForm(),
            'customer_hse_form': CustomerHSEForm(),
            'current_user': current_user.username,
            'companies': companies,  # 🟢 هنرسل ليست الشركات للـ template
            'user_type': user_type,
            'breadcrumb': {
                'title': 'Employee Dashboard',
                'parent': 'Edit Data',
                'child': 'Default'
            }
        }
        return render(request, 'general/dashboard/default/components/add_admin_data.html', context)


    def post(self, request):
        customer_form = CustomerForm(request.POST, user=request.user)
        customer_inbound_form = CustomerInboundForm(request.POST)
        customer_transportation_outbound_form = CustomerTransportationOutboundForm(request.POST)
        customer_wh_outbound_form = CustomerWHOutboundForm(request.POST)
        customer_returns_form = CustomerReturnsForm(request.POST)
        customer_expiry_form = CustomerExpiryForm(request.POST)
        customer_damage_form = CustomerDamageForm(request.POST)
        customer_inventory_form = CustomerInventoryForm(request.POST)
        customer_pallet_location_availability_form = CustomerPalletLocationAvailabilityForm(request.POST)
        customer_hse_form = CustomerHSEForm(request.POST)

        forms = [
            customer_form,
            customer_inbound_form,
            customer_transportation_outbound_form,
            customer_wh_outbound_form,
            customer_returns_form,
            customer_expiry_form,
            customer_damage_form,
            customer_inventory_form,
            customer_pallet_location_availability_form,
            customer_hse_form
        ]

        try:
            with transaction.atomic():
                # 🟢 لازم CustomerForm يتحفظ الأول (أساسي)
                if customer_form.is_valid():
                    customer_data = customer_form.save(commit=False)
                    customer_data.user = request.user

                    # تحديد الشركة
                    company = None
                    if request.user.groups.filter(name='Employee').exists():
                        company = EmployeeProfile.objects.filter(user=request.user).first().company
                    elif request.user.groups.filter(name='Customer').exists():
                        company = Customer.objects.filter(employees__user=request.user).first()

                    customer_data.company = company
                    customer_data.save()
                else:
                    messages.error(request, "Customer basic data is required.")
                    return redirect('customer:add_customer_data')

                # 🟢 باقي الفورمات: احفظها لو فيها داتا
                for form in forms:
                    if form == customer_form:
                        continue  # ده اتحفظ فوق
                    if form.is_valid() and any(form.cleaned_data.values()):
                        instance = form.save(commit=False)
                        instance.customer = customer_data  # 👈 هنا
                        instance.company = company  # 👈 وهنا
                        instance.save()

            messages.success(request, '✅ Customer data added successfully.')
            return redirect('accounts:customer_dashboard')

        except Exception as e:
            messages.error(request, f'❌ Failed to save customer data. Error: {str(e)}')
            return redirect('customer:add_customer_data')


class UploadCustomerDataView(LoginRequiredMixin, View):
    template_name = "components/ui-kits/tab-bootstrap/components/upload_customer_data.html"

    def get(self, request):
        companies = []
        preview_data = request.session.get("preview_data", {})

        if hasattr(request.user, "employee_profile"):
            companies = request.user.employee_profile.company.all()

        if not companies.exists():
            for key in ["preview_data", "inbound_aggregations", "outbound_aggregations", "wh_outbound_aggregations", "returns_aggregations", "selected_company_id"]:
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
            value = str(value).replace("“", "").replace("”", "").strip()
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

    def post(self, request):
        try:
            company_id = request.POST.get("company")
            if not company_id:
                messages.error(request, "⚠️ من فضلك اختر الشركة قبل رفع الملف.")
                return redirect("customer:upload_customer_data")

            company = Customer.objects.get(id=company_id)
            request.session["selected_company_id"] = company.id
            print(f"✅ الشركة المحددة: {company.name_company}")

            if "excel_file" not in request.FILES:
                messages.error(request, "⚠️ من فضلك ارفع ملف Excel.")
                return redirect("customer:upload_customer_data")

            excel_file = request.FILES["excel_file"]
            print(f"📂 الملف المستلم: {excel_file.name}")
            all_sheets = pd.read_excel(excel_file, sheet_name=None, header=None, engine="openpyxl")

            # 🟢 تنظيف السيشن قبل البدء
            for key in ["preview_data", "inbound_aggregations", "outbound_aggregations", "wh_outbound_aggregations", "returns_aggregations"]:
                request.session.pop(key, None)

            preview_data = {}

            # ================== معالجة كل شيت ==================
            for sheet_name, df_sheet in all_sheets.items():
                print(f"\n===== 📑 قراءة الشيت: {sheet_name} =====")
                df_sheet = df_sheet.fillna(method="ffill", axis=1)

                headers = df_sheet.iloc[0].astype(str).tolist()
                sub_headers = df_sheet.iloc[1].astype(str).tolist() if len(df_sheet) > 1 else headers
                df_sheet = df_sheet[2:]  # تجاهل الصفوف الأولى (الهيدر)

                df_sheet.columns = [
                    str(c).strip().replace("\n", "").replace("\r", "").lower()
                    for c in sub_headers
                ]

                rows_excel = df_sheet.fillna("").to_dict(orient="records")
                print(f"📊 عدد الصفوف المقروءة من الشيت {sheet_name}: {len(rows_excel)}")

                unique_rows = []

                # 🟢 Inbound
                if "inbound" in sheet_name.lower():
                    for row in rows_excel:
                        shipment_no = str(row.get("number of shipments") or "").strip()
                        shipment_date = self.clean_date(row.get("dates"))
                        if not shipment_date or not shipment_no:
                            continue
                        row["dates"] = shipment_date.isoformat()

                        if any(r["number of shipments"] == shipment_no and r["dates"] == row["dates"] for r in unique_rows):
                            continue

                        unique_rows.append(self.convert_values(row))

                    if unique_rows:
                        df_preview = pd.DataFrame(unique_rows)
                        for col in ["number of vehicles daily", "number of pallet", "pending shipments", "total quantity", "number of line"]:
                            if col in df_preview.columns:
                                df_preview[col] = pd.to_numeric(df_preview[col], errors="coerce").fillna(0).astype(int)

                        request.session["inbound_aggregations"] = {
                            "number_of_shipments": len(df_preview),
                            "total_vehicles_daily": int(df_preview["number of vehicles daily"].sum()) if "number of vehicles daily" in df_preview else 0,
                            "total_pallets": int(df_preview["number of pallet"].sum()) if "number of pallet" in df_preview else 0,
                            "total_pending_shipments": int(df_preview["pending shipments"].sum()) if "pending shipments" in df_preview else 0,
                            "total_quantity": int(df_preview["total quantity"].sum()) if "total quantity" in df_preview else 0,
                            "total_number_of_line": int(df_preview["number of line"].sum()) if "number of line" in df_preview else 0,
                        }

                    preview_data[sheet_name.lower()] = {
                        "headers": list(df_sheet.columns),
                        "rows": unique_rows,
                    }

                # 🟢 Outbound
                elif "outbound" in sheet_name.lower() and "whoutbound" not in sheet_name.lower():
                    for row in rows_excel:
                        shipment_date = self.clean_date(row.get("dates"))
                        if not shipment_date:
                            continue
                        row["time"] = shipment_date.isoformat()
                        unique_rows.append(self.convert_values(row))

                    if unique_rows:
                        df_preview = pd.DataFrame(unique_rows)
                        for col in ["released order", "piked order", "pending pick order"]:
                            if col in df_preview.columns:
                                df_preview[col] = pd.to_numeric(df_preview[col], errors="coerce").fillna(0).astype(int)

                        request.session["outbound_aggregations"] = {
                            "number_of_shipments": len(df_preview),
                            "total_released_orders": int(df_preview["released order"].sum()) if "released order" in df_preview else 0,
                            "total_piked_orders": int(df_preview["piked order"].sum()) if "piked order" in df_preview else 0,
                            "total_pending_pick_orders": int(df_preview["pending pick order"].sum()) if "pending pick order" in df_preview else 0,
                        }

                    preview_data[sheet_name.lower()] = {
                        "headers": list(df_sheet.columns),
                        "rows": unique_rows,
                    }

                # 🟢 WH Outbound
                elif "whoutbound" in sheet_name.lower():
                    for row in rows_excel:
                        shipment_date = self.clean_date(row.get("dates"))
                        if not shipment_date:
                            continue
                        row["time"] = shipment_date.isoformat()
                        unique_rows.append(self.convert_values(row))

                    preview_data[sheet_name.lower()] = {
                        "headers": list(df_sheet.columns),
                        "rows": unique_rows,
                    }

                # 🟢 Returns
                elif "returns" in sheet_name.lower():
                    import re

                    def canonical(s):
                        if s is None: return ""
                        s = str(s).strip().lower()
                        s = s.replace("\n", " ").replace("\r", " ")
                        s = re.sub(r"\s+", " ", s)
                        s = s.replace("’", "'").replace("`", "'")
                        return s

                    returns_map = {
                        "dates": "time", "date": "time", "time": "time",
                        "total orders items returned": "total_orders_items_returned",
                        "total return items": "total_orders_items_returned",
                        "number of return items orders updated on time": "number_of_return_items_orders_updated_on_time",
                        "returns updated on time": "number_of_return_items_orders_updated_on_time",
                        "number of return items orders updated late": "number_of_return_items_orders_updated_late",
                        "returns updated late": "number_of_return_items_orders_updated_late",
                    }

                    temp = {}
                    for raw in rows_excel:
                        norm = {}
                        for k, v in raw.items():
                            mapped = returns_map.get(canonical(k), canonical(k).replace(" ", "_"))
                            norm[mapped] = v

                        parsed_date = self.clean_date(norm.get("time"))
                        if not parsed_date:
                            continue

                        for col in ["total_orders_items_returned", "number_of_return_items_orders_updated_on_time", "number_of_return_items_orders_updated_late"]:
                            try:
                                norm[col] = int(float(norm.get(col) or 0))
                            except Exception:
                                norm[col] = 0

                        norm["time"] = parsed_date.isoformat()
                        temp[norm["time"]] = norm

                    unique_rows = list(temp.values())

                    if unique_rows:
                        df_preview = pd.DataFrame(unique_rows)
                        for col in ["total_orders_items_returned", "number_of_return_items_orders_updated_on_time", "number_of_return_items_orders_updated_late"]:
                            if col in df_preview.columns:
                                df_preview[col] = pd.to_numeric(df_preview[col], errors="coerce").fillna(0).astype(int)

                        request.session["returns_aggregations"] = {
                            "number_of_returns": len(df_preview),
                            "total_orders_items_returned": int(df_preview["total_orders_items_returned"].sum()),
                            "total_return_items_updated_on_time": int(df_preview["number_of_return_items_orders_updated_on_time"].sum()),
                            "total_return_items_updated_late": int(df_preview["number_of_return_items_orders_updated_late"].sum()),
                        }

                    preview_data[sheet_name.lower()] = {
                        "headers": ["time", "total_orders_items_returned", "number_of_return_items_orders_updated_on_time", "number_of_return_items_orders_updated_late"],
                        "rows": unique_rows,
                    }

                # 🟢 Expiry
                elif "expiry" in sheet_name.lower():
                    temp = {}
                    for row in rows_excel:
                        parsed_date = self.clean_date(row.get("dates"))
                        if not parsed_date:
                            continue
                        norm = {
                            "time": parsed_date.isoformat(),
                            "assigned_day": str(row.get("assigned day") or "").strip(),
                            "total_SKUs_expired": int(float(row.get("total skus expired") or 0)),
                            "total_expired_SKUS_disposed": int(float(row.get("total expired skus disposed") or 0)),
                            "nearly_expired_1_to_3_months": int(float(row.get("nearly expired 1 to 3 months") or 0)),
                            "nearly_expired_3_to_6_months": int(float(row.get("nearly expired 3 to 6 months") or 0)),
                        }
                        temp[norm["time"]] = norm  # إزالة المكرر

                    unique_rows = list(temp.values())

                    if unique_rows:
                        df_preview = pd.DataFrame(unique_rows)
                        request.session["expiry_aggregations"] = {
                            "number_of_days": len(df_preview),
                            "total_SKUs_expired": int(df_preview["total_SKUs_expired"].sum()),
                            "total_expired_SKUS_disposed": int(df_preview["total_expired_SKUS_disposed"].sum()),
                            "total_nearly_expired_1_to_3_months": int(df_preview["nearly_expired_1_to_3_months"].sum()),
                            "total_nearly_expired_3_to_6_months": int(df_preview["nearly_expired_3_to_6_months"].sum()),
                        }

                    preview_data[sheet_name.lower()] = {
                        "headers": ["time", "assigned_day", "total_SKUs_expired", "total_expired_SKUS_disposed",
                                    "nearly_expired_1_to_3_months", "nearly_expired_3_to_6_months"],
                        "rows": unique_rows,
                    }


                # 🟢 Damage
                elif "damage" in sheet_name.lower():
                    temp = {}
                    for row in rows_excel:
                        parsed_date = self.clean_date(row.get("dates"))
                        if not parsed_date:
                            continue
                        norm = {
                            "time": parsed_date.isoformat(),
                            "assigned_day": str(row.get("assigned day") or "").strip(),
                            "Total_QTYs_Damaged_by_WH": int(float(row.get("total qtys damaged by wh") or 0)),
                            "Number_of_Damaged_during_receiving": int(
                                float(row.get("number of damaged during receiving") or 0)),
                            "Total_Araive_Damaged": int(float(row.get("total araive damaged") or 0)),
                        }
                        temp[norm["time"]] = norm

                    unique_rows = list(temp.values())

                    if unique_rows:
                        df_preview = pd.DataFrame(unique_rows)
                        request.session["damage_aggregations"] = {
                            "number_of_days": len(df_preview),
                            "total_qtys_damaged_by_wh": int(df_preview["Total_QTYs_Damaged_by_WH"].sum()),
                            "total_damaged_during_receiving": int(
                                df_preview["Number_of_Damaged_during_receiving"].sum()),
                            "total_araive_damaged": int(df_preview["Total_Araive_Damaged"].sum()),
                        }

                    preview_data[sheet_name.lower()] = {
                        "headers": ["time", "assigned_day", "Total_QTYs_Damaged_by_WH",
                                    "Number_of_Damaged_during_receiving", "Total_Araive_Damaged"],
                        "rows": unique_rows,
                    }


                # 🟢 Inventory
                elif "inventory" in sheet_name.lower():
                    temp = {}
                    for row in rows_excel:
                        parsed_date = self.clean_date(row.get("dates"))
                        if not parsed_date:
                            continue
                        norm = {
                            "time": parsed_date.isoformat(),
                            "assigned_day": str(row.get("assigned day") or "").strip(),
                            "Total_Locations_match": int(float(row.get("total locations match") or 0)),
                            "Total_Locations_not_match": int(float(row.get("total locations not match") or 0)),
                        }
                        temp[norm["time"]] = norm

                    unique_rows = list(temp.values())

                    if unique_rows:
                        df_preview = pd.DataFrame(unique_rows)
                        request.session["inventory_aggregations"] = {
                            "number_of_days": len(df_preview),
                            "Total_Locations_match": int(df_preview["Total_Locations_match"].sum()),
                            "Total_Locations_not_match": int(df_preview["Total_Locations_not_match"].sum()),
                        }

                    preview_data[sheet_name.lower()] = {
                        "headers": ["time", "assigned_day", "Total_Locations_match", "Total_Locations_not_match"],
                        "rows": unique_rows,
                    }

                # 🟢 HSE
                elif "hse" in sheet_name.lower():
                    temp = {}
                    for row in rows_excel:
                        parsed_date = self.clean_date(row.get("dates"))
                        if not parsed_date:
                            continue
                        norm = {
                            "time": parsed_date.isoformat(),
                            "assigned_day": str(row.get("assigned day") or "").strip(),
                            "Total_Incidents_on_the_side": int(float(row.get("total incidents on the side") or 0)),
                        }
                        temp[norm["time"]] = norm

                    unique_rows = list(temp.values())
                    preview_data["hse"] = {
                        "headers": ["time", "assigned_day", "Total_Incidents_on_the_side"],
                        "rows": unique_rows,
                    }

            # 🟢 حفظ preview في السيشن
            request.session["preview_data"] = preview_data
            request.session.modified = True

            messages.success(request, "✅ تم رفع الملف وعرض البيانات بنجاح.")
            return redirect("customer:upload_customer_data")

        except Exception as e:
            import traceback
            print(traceback.format_exc())
            messages.error(request, f"❌ خطأ أثناء قراءة الملف: {e}")
            return redirect("customer:upload_customer_data")


class SaveUploadedDataView(LoginRequiredMixin, View):
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
                return redirect("customer:upload_customer_data")

            company = Customer.objects.get(id=company_id)
            preview_data = request.session.get("preview_data", {})
            if not preview_data:
                messages.error(request, "⚠️ لا توجد بيانات محفوظة للتحميل. ارفع ملف أولاً.")
                return redirect("customer:upload_customer_data")

            saved_counts = {}
            print(f"\n💾 بدء الحفظ للشركة: {company.name_company}")

            for sheet_name, sheet_data in preview_data.items():
                rows = sheet_data.get("rows", [])
                sheet_lower = sheet_name.lower()
                print(f"\n===== 💾 حفظ البيانات من الشيت: {sheet_name} =====")
                print(f"📊 عدد الصفوف المحضّرة: {len(rows)}")

                # Safety: ensure rows are dicts (sometimes stored as JSON strings)
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
                        # keys in preview were normalized: expect 'time' and 'number_of_shipments' etc
                        shipment_date = self.parse_date(row.get("time") or row.get("dates"))
                        shipment_no = self._to_int(row.get("number_of_shipments") or row.get("number of shipments"))
                        if not shipment_date or not shipment_no:
                            continue

                        # احذف أي شحنة بنفس رقم الشحنة + الشركة (حتى لا يتكرر)
                        with transaction.atomic():
                            CustomerInbound.objects.filter(
                                company=company,
                                number_of_shipments=shipment_no
                            ).delete()

                            CustomerInbound.objects.create(
                                company=company,
                                time=shipment_date,
                                assigned_day=shipment_date.strftime("%A"),
                                number_of_shipments=shipment_no,
                                number_of_vehicles_daily=self._to_int(
                                    row.get("number_of_vehicles_daily") or row.get("number of vehicles daily")),
                                number_of_pallets=self._to_int(
                                    row.get("number_of_pallet") or row.get("number of pallet")),
                                bulk=1 if str(row.get("shipment_type") or row.get(
                                    "shipment type") or "").lower() == "bulk" else 0,
                                loose=1 if str(row.get("shipment_type") or row.get(
                                    "shipment type") or "").lower() == "loose" else 0,
                                cold=1 if str(row.get("shipment_temperature") or row.get(
                                    "shipment temperature") or "").lower() == "cold" else 0,
                                frozen=1 if str(row.get("shipment_temperature") or row.get(
                                    "shipment temperature") or "").lower() in ["frozen", "frosen"] else 0,
                                ambient=1 if str(row.get("shipment_temperature") or row.get(
                                    "shipment temperature") or "").lower() == "ambient" else 0,
                                pending_shipments=self._to_int(
                                    row.get("pending_shipments") or row.get("pending shipments")),
                                total_quantity=self._to_int(row.get("total_quantity") or row.get("total quantity")),
                                number_of_line=self._to_int(row.get("number_of_line") or row.get("number of line")),
                            )

                    saved_counts[sheet_lower] = saved_counts.get(sheet_lower, 0) + len(normalized_rows)

                # ===== WH Outbound =====
                elif "wh_outbound" in sheet_lower :
                    # سنستخدم set لمنع إدخال نفس released_order أكثر من مرة خلال نفس جلسة الحفظ
                    processed_keys = set()
                    for row in normalized_rows:
                        # preview صممنا مفاتيحها لتكون like model fields: 'time', 'released_order', 'piked_order', 'pending_pick_orders', 'number_of_PODs_collected_on_time', 'number_of_PODs_collected_Late'
                        shipment_date = self.parse_date(row.get("time") or row.get("dates"))
                        if not shipment_date:
                            continue

                        released_order = self._to_int(row.get("released_order") or row.get("released order"))
                        piked_order = self._to_int(row.get("piked_order") or row.get("piked order"))
                        pending_pick_orders = self._to_int(
                            row.get("pending_pick_orders") or row.get("pending pick orders"))
                        pods_on_time = self._to_int(row.get("number_of_PODs_collected_on_time") or row.get(
                            "number of pod's collected time") or row.get("number of pods collected on time"))
                        pods_late = self._to_int(row.get("number_of_PODs_collected_Late") or row.get(
                            "number of pod's collected late") or row.get("number of pods collected late"))

                        # مفتاح منع التكرار: released_order إذا موجود >0 وإلا (company,time)
                        dedupe_key = ("released", released_order) if released_order else ("time",
                                                                                          shipment_date.isoformat())

                        if dedupe_key in processed_keys:
                            # يتكرر داخل نفس عملية الحفظ -> تجاهل
                            continue
                        processed_keys.add(dedupe_key)

                        # حذف القيم القديمة في DB لنفس released_order (أو لنفس التاريخ إذا released_order غير معرف)
                        with transaction.atomic():
                            if released_order:
                                CustomerWHOutbound.objects.filter(company=company,
                                                                  released_order=released_order).delete()
                            else:
                                CustomerWHOutbound.objects.filter(company=company, time=shipment_date).delete()

                            CustomerWHOutbound.objects.create(
                                company=company,
                                time=shipment_date,
                                assigned_day=shipment_date.strftime("%A"),
                                released_order=released_order,
                                piked_order=piked_order,
                                pending_pick_orders=pending_pick_orders,
                                number_of_PODs_collected_on_time=pods_on_time,
                                number_of_PODs_collected_Late=pods_late,
                            )

                    saved_counts[sheet_lower] = saved_counts.get(sheet_lower, 0) + len(normalized_rows)

                elif "returns" in sheet_lower:
                    CustomerReturns.objects.filter(company=company).delete()
                    for row in preview_data["returns"]["rows"]:
                        CustomerReturns.objects.create(
                            company=company,
                            time=pd.to_datetime(row.get("time")).date() if row.get("time") else None,
                            total_orders_items_returned=int(row.get("total_orders_items_returned") or 0),
                            number_of_return_items_orders_updated_on_time=int(
                                row.get("number_of_return_items_orders_updated_on_time") or 0),
                            number_of_return_items_orders_updated_late=int(
                                row.get("number_of_return_items_orders_updated_late") or 0),
                            assigned_day=pd.to_datetime(row.get("time")).day_name() if row.get("time") else None,
                        )
                    print(f"✅ تم حفظ {len(preview_data['returns']['rows'])} من returns")

                elif "expiry" in sheet_lower:
                    CustomerExpiry.objects.filter(company=company).delete()
                    for row in preview_data["expiry"]["rows"]:
                        CustomerExpiry.objects.create(
                            company=company,
                            time=pd.to_datetime(row.get("time")).date() if row.get("time") else None,
                            assigned_day=pd.to_datetime(row.get("time")).day_name() if row.get("time") else None,
                            total_SKUs_expired=int(row.get("total_SKUs_expired") or 0),
                            total_expired_SKUS_disposed=int(row.get("total_expired_SKUS_disposed") or 0),
                            nearly_expired_1_to_3_months=int(row.get("nearly_expired_1_to_3_months") or 0),
                            nearly_expired_3_to_6_months=int(row.get("nearly_expired_3_to_6_months") or 0),
                        )
                    print(f"✅ تم حفظ {len(preview_data['expiry']['rows'])} من expiry")


                elif "damage" in sheet_lower:
                    CustomerDamage.objects.filter(company=company).delete()
                    for row in preview_data["damage"]["rows"]:
                        CustomerDamage.objects.create(
                            company=company,
                            time=pd.to_datetime(row.get("time")).date() if row.get("time") else None,
                            assigned_day=pd.to_datetime(row.get("time")).day_name() if row.get("time") else None,
                            Total_QTYs_Damaged_by_WH=int(row.get("Total_QTYs_Damaged_by_WH") or 0),
                            Number_of_Damaged_during_receiving=int(row.get("Number_of_Damaged_during_receiving") or 0),
                            Total_Araive_Damaged=int(row.get("Total_Araive_Damaged") or 0),
                        )
                    print(f"✅ تم حفظ {len(preview_data['damage']['rows'])} من damage")


                elif "inventory" in sheet_lower:
                    CustomerInventory.objects.filter(company=company).delete()
                    for row in preview_data["inventory"]["rows"]:
                        CustomerInventory.objects.create(
                            company=company,
                            time=pd.to_datetime(row.get("time")).date() if row.get("time") else None,
                            assigned_day=pd.to_datetime(row.get("time")).day_name() if row.get("time") else None,
                            Total_Locations_match=int(row.get("Total_Locations_match") or 0),
                            Total_Locations_not_match=int(row.get("Total_Locations_not_match") or 0),
                        )
                    print(f"✅ تم حفظ {len(preview_data['inventory']['rows'])} من inventory")

                elif "hse" in sheet_lower:
                    CustomerHSE.objects.filter(company=company).delete()
                    for row in preview_data["hse"]["rows"]:
                        CustomerHSE.objects.create(
                            company=company,
                            time=pd.to_datetime(row.get("time")).date() if row.get("time") else None,
                            assigned_day=pd.to_datetime(row.get("time")).day_name() if row.get("time") else None,
                            Total_Incidents_on_the_side=int(row.get("Total_Incidents_on_the_side") or 0),
                        )
                    print(f"✅ تم حفظ {len(preview_data['hse']['rows'])} من hse")




                # ===== other sheets: implement similarly if needed =====
                else:
                    # for other sheets, just count them (or implement saving logic)
                    saved_counts[sheet_lower] = saved_counts.get(sheet_lower, 0) + len(normalized_rows)

            print("\n✅ ملخص الحفظ:", saved_counts)
            msg = f"✅ تم حفظ البيانات بنجاح للشركة {company.name_company}."
            for sheet, count in saved_counts.items():
                msg += f" 🟢 {sheet}: {count} صف محفوظ."
            messages.success(request, msg)

            # نظف السيشن بعد الحفظ
            for key in ["preview_data", "inbound_aggregations", "wh_outbound_aggregations", "outbound_aggregations"]:
                request.session.pop(key, None)
            request.session.modified = True

            return redirect("customer:customer_dashboard")

        except Exception as e:
            import traceback
            print("❌ خطأ أثناء الحفظ:")
            print(traceback.format_exc())
            messages.error(request, f"❌ خطأ أثناء الحفظ: {e}")
            return redirect("customer:upload_customer_data")


