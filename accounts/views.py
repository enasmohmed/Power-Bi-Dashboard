import calendar

from django.contrib import messages
from django.contrib.auth import login, get_user_model, logout
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.auth.models import Group
from django.contrib.auth.views import LoginView as AuthLoginView, LogoutView
from django.db.models import Sum
from django.http import HttpResponse
from django.shortcuts import redirect, render
from django.urls import reverse_lazy, reverse
from django.utils.decorators import method_decorator
from django.views import View
from django.views.generic import CreateView, TemplateView

from administration.forms import AdminDataForm
from administration.models import AdminData
from customer.forms import CustomerForm
from customer.models import CustomerInbound, CustomerReturns, CustomerExpiry, CustomerDamage, \
    CustomerInventory, CustomerPalletLocationAvailability, CustomerHSE, CustomerTransportationOutbound, \
    CustomerWHOutbound
from .forms import CustomUserCreationForm, ProfileForm
from .models import CustomUser

from .dummy_data import OVERVIEW, OUTBOUND, INBOUND, CITIES, INVENTORY, SLA, MISSES, DASHBOARD
from . import kpi_excel
from . import sla_settings

User = get_user_model()


# Create your views here.


class CustomLoginView(AuthLoginView):
    template_name = 'accounts/new/login.html'

    def form_valid(self, form):
        user = form.get_user()
        print(f"User: {user.username}, Approved: {user.is_approved}")

        # Print detailed role information
        if hasattr(user, 'role'):
            print(f"Role attribute exists. Role: {user.role}")
        else:
            print("Role attribute does not exist.")

        # Print group memberships
        print(f"Groups: {[group.name for group in user.groups.all()]}")

        if not user.is_superuser and not user.is_approved:
            messages.error(self.request, "Your account is pending approval.")
            logout(self.request)
            return redirect('accounts:login')

        login(self.request, user)

        if user.is_superuser or user.groups.filter(name='Admin').exists():
            print("Redirecting to admin dashboard")
            return redirect(reverse('accounts:overview'))
        elif user.role == 'customer' and user.groups.filter(name='Customer').exists():
            print("Redirecting to customer dashboard")
            return redirect('accounts:customer_dashboard')
        # elif user.role == 'employee' and user.groups.filter(name='Employee').exists():
        #     print("Redirecting to employee dashboard")
        #     return redirect('accounts:choose_dashboard')
        elif user.role == 'employee' and user.groups.filter(name='Employee').exists():
            self.request.session['dashboard_choice'] = 'admin_dashboard'
            self.request.session['dashboard_type'] = 'Admin Dashboard'
            return redirect('accounts:overview')
        else:
            print("Redirecting to home page")
            return redirect('/')


class CustomRegisterView(CreateView):
    model = CustomUser
    form_class = CustomUserCreationForm
    template_name = 'accounts/new/sign-up.html'
    success_url = reverse_lazy('login')  # Redirect to login page

    def form_valid(self, form):
        user = form.save()
        messages.success(self.request,
                         "Your account has been created successfully. Your account is now pending approval.")
        return redirect(self.success_url)


class RegisterView(View):
    form_class = CustomUserCreationForm
    template_name = 'accounts/new/sign-up.html'

    def get(self, request):
        form = self.form_class()
        return render(request, self.template_name, {'form': form})

    def post(self, request):
        form = self.form_class(request.POST)
        if form.is_valid():
            user = form.save()
            return HttpResponse("Your account is awaiting approval.")
        return render(request, self.template_name, {'form': form})


class CustomLogoutView(LogoutView):
    next_page = '/accounts/login/'


@method_decorator(login_required, name='dispatch')
@method_decorator(user_passes_test(lambda u: u.is_superuser), name='dispatch')
class ApproveUsersView(TemplateView):
    template_name = 'accounts/approve_users.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        users = CustomUser.objects.filter(is_approved=False)
        user_data = []
        for user in users:
            user_data.append({
                'id': user.id,
                'username': user.username,
                'email': user.email,
                'role': user.get_role_display(),
                'user_role': 'Superuser' if user.is_superuser else 'Staff' if user.is_staff else 'User',
                'groups': ', '.join([group.name for group in user.groups.all()])
            })
        context['users'] = user_data
        context['page'] = 'users'
        context['breadcrumb'] = {
            "title": "Approve Users",
            "parent": "Super User",
            "child": "Admin"
        }

        # Determine user type and add it to the context
        if self.request.user.is_superuser:
            context['user_type'] = "Super Admin"
        elif self.request.user.groups.filter(name='Admin').exists():
            context['user_type'] = "Admin"
        elif self.request.user.groups.filter(name='Employee').exists():
            context['user_type'] = "Employee"
        else:
            context['user_type'] = "Unknown"

        return context

    def post(self, request, *args, **kwargs):
        user_id = request.POST.get('user_id')
        user = CustomUser.objects.get(id=user_id)
        user.is_approved = True

        if user.is_superuser:
            user.is_staff = True
            user.save()
            messages.success(request, f'User has been approved {user.username} He is a super user.')
        else:
            user.is_staff = True
            user.save()

            if user.role == 'admin':
                group, created = Group.objects.get_or_create(name='Admin')
            elif user.role == 'customer':
                group, created = Group.objects.get_or_create(name='Customer')
            elif user.role == 'employee':
                group, created = Group.objects.get_or_create(name='Employee')

            user.groups.add(group)
            user.save()
            messages.success(request,
                             f'User has been approved {user.username} It has been added to the group {group.name}.')

        return redirect('accounts:approve_users')


def profile_view(request):
    user = request.user
    form = ProfileForm(instance=user)
    if request.method == 'POST':
        form = ProfileForm(request.POST, instance=user)
        if form.is_valid():
            form.save()
            return redirect('profile')
    return render(request, 'profile.html', {'form': form})


# ---------------------------------user


@login_required(login_url="/login")
def user_profile(request):
    context = {
        "page": "users",
        "breadcrumb": {
            "title": "User Profile",
            "parent": "Users",
            "child": "User Profile"
        }
    }

    user = request.user
    form = ProfileForm(instance=user)

    # تحديد نوع المستخدم بناءً على الصلاحيات وعضوية المجموعة
    if user.is_superuser:
        user_type = "Super Admin"
    elif user.groups.filter(name='Admin').exists():
        user_type = "Admin"
    elif user.groups.filter(name='Employee').exists():
        user_type = "Employee"
    else:
        user_type = "Customer"

    # الحصول على أسماء المجموعات التي ينتمي إليها المستخدم
    user_groups = user.groups.values_list('name', flat=True)

    if request.method == 'POST':
        form = ProfileForm(request.POST, instance=user)
        if form.is_valid():
            form.save()
            return redirect('profile')

    context['form'] = form
    context['user_type'] = user_type
    context['user_groups'] = user_groups

    return render(request, "user/user-profile/user-profile.html", context)


@login_required(login_url="/login")
def redirect_to_dashboard(request):
    user = request.user
    dashboard_choice = request.session.get('dashboard_choice')

    if request.method == 'POST':
        dashboard_choice = request.POST.get('dashboard_choice')
        request.session['dashboard_choice'] = dashboard_choice

    if user.is_superuser or user.role == 'admin':
        request.session['dashboard_type'] = 'Admin Dashboard'
        return redirect('accounts:overview')
    elif user.role == 'employee':
        if dashboard_choice == 'admin_dashboard':
            request.session['dashboard_type'] = 'Admin Dashboard'
            return redirect('accounts:overview')
        elif dashboard_choice == 'customer_dashboard':
            request.session['dashboard_type'] = 'Customer Dashboard'
            return redirect('accounts:customer_dashboard')
    elif user.role == 'customer':
        request.session['dashboard_type'] = 'Customer Dashboard'
        return redirect('accounts:customer_dashboard')

    request.session['dashboard_type'] = 'Unknown Dashboard'
    return redirect('accounts:choose_dashboard')


@user_passes_test(lambda u: u.is_superuser)
def user_cards(request):
    # التحقق إذا كان المستخدم الحالي هو سوبر يوزر
    if not request.user.is_superuser:
        return redirect('/')

    # جلب جميع المستخدمين
    users = CustomUser.objects.all()

    # تحديد نوع المستخدم بناءً على الصلاحيات وعضوية المجموعة
    if request.user.is_superuser:
        user_type = "Super Admin"
    elif request.user.groups.filter(name='Admin').exists():
        user_type = "Admin"
    elif request.user.groups.filter(name='Employee').exists():
        user_type = "Employee"
    else:
        user_type = "Customer"

    # تحديد مجموعة المستخدم
    user_group = "Unknown"  # افتراض قيمة افتراضية

    if request.user.is_superuser:
        user_group = "Super Admin"
    elif request.user.groups.filter(name='Admin').exists():
        user_group = "Admin"
    elif request.user.groups.filter(name='Employee').exists():
        user_group = "Employee"
    elif request.user.groups.filter(name='Customer').exists():
        user_group = "Customer"

    context = {
        "page": "users",
        "breadcrumb": {
            "title": "User Cards",
            "parent": "Users",
            "child": "User Cards"
        },
        "users": users,
        "user_type": user_type,  # إضافة user_type إلى السياق
        "user_group": user_group,  # إضافة user_group إلى السياق
    }

    return render(request, "user/user-cards/user-cards.html", context)


def is_employee(user):
    return user.is_authenticated and user.role == 'employee'


@method_decorator([login_required, user_passes_test(is_employee)], name='dispatch')
class EmployeeDashboardView(LoginRequiredMixin, TemplateView):
    template_name = 'index.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['breadcrumb'] = {
            "title": "Employee Dashboard",
            "parent": "Dashboard",
            "child": "Employee"
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

        # الحصول على جميع بيانات Inbound
        context['inbound_data'] = inbound_data
        context['total_shipments_in_asn'] = inbound_data.aggregate(Sum('total_shipments_in_asn'))[
                                                'total_shipments_in_asn__sum'] or 0
        context['total_arrived'] = inbound_data.aggregate(Sum('arrived'))['arrived__sum'] or 0
        context['total_no_show'] = inbound_data.aggregate(Sum('no_show'))['no_show__sum'] or 0

        context['total_waiting_for_inspection'] = inbound_data.aggregate(Sum('waiting_for_inspection'))[
                                                      'waiting_for_inspection__sum'] or 0
        context['total_dash_of_GR_reports_shared'] = \
            inbound_data.aggregate(Sum('total_dash_of_GR_reports_shared'))['total_dash_of_GR_reports_shared__sum'] or 0
        context['total_dash_of_GR_reports_with_discripancy'] = \
            inbound_data.aggregate(Sum('dash_of_GR_reports_with_discripancy'))[
                'dash_of_GR_reports_with_discripancy__sum'] or 0

        context['total_received_completely'] = inbound_data.aggregate(Sum('received_completely'))[
                                                   'received_completely__sum'] or 0
        context['total_received_partially'] = inbound_data.aggregate(Sum('received_partially'))[
                                                  'received_partially__sum'] or 0
        context['total_rejected_completely'] = inbound_data.aggregate(Sum('rejected_completely'))[
                                                   'rejected_completely__sum'] or 0

        # Transportation Outbound
        context['transportation_outbound_data'] = transportation_outbound_data
        context['total_released_order'] = transportation_outbound_data.aggregate(Sum('released_order'))['released_order__sum'] or 0
        context['total_pending_pick_orders'] = transportation_outbound_data.aggregate(Sum('pending_pick_orders'))['pending_pick_orders__sum'] or 0
        context['total_piked_order'] = transportation_outbound_data.aggregate(Sum('piked_order'))['piked_order__sum'] or 0

        context['total_number_of_PODs_collected_on_time'] = \
            transportation_outbound_data.aggregate(Sum('number_of_PODs_collected_on_time'))[
                'number_of_PODs_collected_on_time__sum'] or 0
        context['total_number_of_PODs_collected_Late'] = transportation_outbound_data.aggregate(Sum('number_of_PODs_collected_Late'))[
                                                             'number_of_PODs_collected_Late__sum'] or 0
        context['total_total_skus_picked'] = transportation_outbound_data.aggregate(Sum('total_skus_picked'))[
                                                 'total_skus_picked__sum'] or 0

        # WH Outbound
        context['wh_outbound_data'] = wh_outbound_data
        context['total_released_order'] = wh_outbound_data.aggregate(Sum('released_order'))['released_order__sum'] or 0
        context['total_pending_pick_orders'] = wh_outbound_data.aggregate(Sum('pending_pick_orders'))['pending_pick_orders__sum'] or 0
        context['total_piked_order'] = wh_outbound_data.aggregate(Sum('piked_order'))['piked_order__sum'] or 0

        context['total_number_of_PODs_collected_on_time'] = \
            wh_outbound_data.aggregate(Sum('number_of_PODs_collected_on_time'))[
                'number_of_PODs_collected_on_time__sum'] or 0
        context['total_number_of_PODs_collected_Late'] = wh_outbound_data.aggregate(Sum('number_of_PODs_collected_Late'))[
                                                             'number_of_PODs_collected_Late__sum'] or 0
        context['total_total_skus_picked'] = wh_outbound_data.aggregate(Sum('total_skus_picked'))[
                                                 'total_skus_picked__sum'] or 0

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
        context['total_SKUs_expired'] = expiry_data.aggregate(Sum('total_SKUs_expired'))['total_SKUs_expired__sum'] or 0
        context['total_expired_SKUS_disposed'] = expiry_data.aggregate(Sum('total_expired_SKUS_disposed'))[
                                                     'total_expired_SKUS_disposed__sum'] or 0
        context['total_nearly_expired_1_to_3_months'] = expiry_data.aggregate(Sum('nearly_expired_1_to_3_months'))[
                                                            'nearly_expired_1_to_3_months__sum'] or 0
        context['total_nearly_expired_3_to_6_months'] = expiry_data.aggregate(Sum('nearly_expired_3_to_6_months'))[
                                                            'nearly_expired_3_to_6_months__sum'] or 0

        # Damage
        context['damage_data'] = damage_data
        context['Total_QTYs_Damaged_by_WH'] = damage_data.aggregate(Sum('Total_QTYs_Damaged_by_WH'))[
                                                  'Total_QTYs_Damaged_by_WH__sum'] or 0
        context['Total_Number_of_Damaged_during_receiving'] = \
            damage_data.aggregate(Sum('Number_of_Damaged_during_receiving'))[
                'Number_of_Damaged_during_receiving__sum'] or 0
        context['Total_Damaged_QTYs_Disposed'] = damage_data.aggregate(Sum('Total_Damaged_QTYs_Disposed'))[
                                                     'Total_Damaged_QTYs_Disposed__sum'] or 0

        # الحصول على جميع بيانات TravelDistance
        context['travel_distance_data'] = travel_distance_data
        context['Total_no_of_Pallet_deliverd'] = travel_distance_data.aggregate(Sum('Total_no_of_Pallet_deliverd'))[
                                                     'Total_no_of_Pallet_deliverd__sum'] or 0
        context['Total_no_of_Customers_deliverd'] = \
            travel_distance_data.aggregate(Sum('Total_no_of_Customers_deliverd'))[
                'Total_no_of_Customers_deliverd__sum'] or 0

        # Inventory
        context['inventory_data'] = inventory_data
        context['Total_Locations_Audited'] = inventory_data.aggregate(Sum('Total_Locations_Audited'))[
                                                 'Total_Locations_Audited__sum'] or 0
        context['Total_Locations_with_Incorrect_SKU_and_Qty'] = \
            inventory_data.aggregate(Sum('Total_Locations_with_Incorrect_SKU_and_Qty'))[
                'Total_Locations_with_Incorrect_SKU_and_Qty__sum'] or 0
        context['Total_SKUs_Reconciliation'] = inventory_data.aggregate(Sum('Total_SKUs_Reconciliation'))[
                                                   'Total_SKUs_Reconciliation__sum'] or 0

        # PalletLocationAvailability
        context['pallet_location_availability_data'] = pallet_location_availability_data
        context['Total_Storage_Pallet'] = pallet_location_availability_data.aggregate(Sum('Total_Storage_Pallet'))[
                                              'Total_Storage_Pallet__sum'] or 0
        context['Total_Storage_Bin'] = pallet_location_availability_data.aggregate(Sum('Total_Storage_Bin'))[
                                           'Total_Storage_Bin__sum'] or 0
        context['Total_Storage_pallet_empty'] = \
            pallet_location_availability_data.aggregate(Sum('Total_Storage_pallet_empty'))[
                'Total_Storage_pallet_empty__sum'] or 0
        context['Total_Storage_Bin_empty'] = \
            pallet_location_availability_data.aggregate(Sum('Total_Storage_Bin_empty'))[
                'Total_Storage_Bin_empty__sum'] or 0
        context['Total_Storage_Bin_empty'] = \
            pallet_location_availability_data.aggregate(Sum('Total_Storage_Bin_empty'))[
                'Total_Storage_Bin_empty__sum'] or 0
        context['Total_occupied_pallet_location'] = \
            pallet_location_availability_data.aggregate(Sum('Total_occupied_pallet_location'))[
                'Total_occupied_pallet_location__sum'] or 0
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

        context['current_user'] = self.request.user
        user_type = "Employee" if self.request.user.role == "employee" else "Customer"
        context['user_type'] = user_type

        context.update({
            'years': years,
            'months': months,
            'days': days,
        })
        return context


@method_decorator(login_required, name='dispatch')
class ChooseDashboardView(View):
    template_name = 'general/dashboard/default/components/choose_dashboard.html'

    def get_context_data(self, **kwargs):
        context = {
            "breadcrumb": {
                "title": "Employee Dashboard",
                "parent": "Edit Data",
                "child": "Default"
            }
        }

        # Determine user type and add it to the context
        if self.request.user.is_superuser:
            context['user_type'] = "Super Admin"
        elif self.request.user.groups.filter(name='Admin').exists():
            context['user_type'] = "Admin"
        elif self.request.user.groups.filter(name='Employee').exists():
            context['user_type'] = "Employee"
        else:
            context['user_type'] = "Unknown"

        context.update({
            'admin_data_form': AdminDataForm(initial={'user': self.request.user}),
            'customer_form': CustomerForm(initial={'user': self.request.user}),
            'current_user': self.request.user.username,
            'is_employee': self.request.user.groups.filter(name='Employee').exists(),
            'dashboard_choice': self.request.session.get('dashboard_choice')
        })

        return context

    def get(self, request, *args, **kwargs):
        request.session['dashboard_choice'] = 'admin_dashboard'
        request.session['dashboard_type'] = 'Admin Dashboard'
        return redirect('accounts:overview')

    # def get(self, request, *args, **kwargs):
    #     context = self.get_context_data(**kwargs)
    #     return render(request, self.template_name, context)

    def post(self, request, *args, **kwargs):
        choice = request.POST.get('choice')
        if choice == 'admin_dashboard':
            if request.user.is_superuser or request.user.groups.filter(name='Admin').exists():
                request.session['dashboard_choice'] = 'admin_dashboard'
                request.session['dashboard_type'] = 'Admin Dashboard'
                return redirect('accounts:overview')

            elif request.user.groups.filter(name='Employee').exists():
                request.session['dashboard_choice'] = 'admin_dashboard'
                request.session['dashboard_type'] = 'Admin Dashboard'
                return redirect('accounts:overview')

        elif choice == 'customer_dashboard':
            request.session['dashboard_choice'] = 'customer_dashboard'
            request.session['dashboard_type'] = 'Customer Dashboard'
            return redirect('accounts:customer_dashboard')

        context = self.get_context_data(**kwargs)
        return render(request, self.template_name, context)




class DashboardPageView(LoginRequiredMixin, TemplateView):
    template_name = 'general/dashboard/pages/placeholder.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        page = self.request.resolver_match.url_name
        if page == 'admin_dashboard':
            page = 'overview'

        titles = {
            'dashboard': 'Dashboard',
            'overview': 'Overview',
            'outbound': 'Outbound',
            'inbound': 'Inbound',
            'cities': 'Cities',
            'inventory': 'Inventory',
            'sla': 'SLA',
            'misses': 'Misses',
        }

        live_pages, source = kpi_excel.load_dashboard(
            company=self.request.GET.get('company', 'all'),
            warehouse=self.request.GET.get('wh', 'all'),
            page=page,
        )
        if source == 'excel' and live_pages:
            page_data = live_pages
        else:
            page_data = {
                'overview': OVERVIEW,
                'outbound': OUTBOUND,
                'inbound': INBOUND,
                'cities': CITIES,
                'inventory': INVENTORY,
                'sla': SLA,
                'misses': MISSES,
                'dashboard': DASHBOARD,
            }
            if source == 'error':
                source = 'sample'

        context['page'] = page
        context['page_title'] = titles.get(page, page)
        context['has_data'] = False
        context['user_type'] = 'Employee'
        context['selected_company'] = self.request.GET.get('company', 'all')
        context['selected_warehouse'] = self.request.GET.get('wh', 'all')
        context['year_range'] = '2025 - 2026'
        context['kpi_footer'] = (
            'Tamer Logistics — 3PL KPI Dashboard — IFFCO (Mar 2025) & Aramco (Aug 2026) — KSA Operations'
        )
        context['data_source'] = source
        context['excel_name'] = kpi_excel.EXCEL_NAME
        context['breadcrumb'] = {
            'title': titles.get(page, page),
            'parent': 'Dashboard',
            'child': titles.get(page, page),
        }

        selected = context['selected_company']
        selected_wh = context['selected_warehouse']
        qs = []
        if selected and selected != 'all':
            qs.append(f'company={selected}')
        if selected_wh and selected_wh != 'all':
            qs.append(f'wh={selected_wh}')
        context['company_query'] = f'?{"&".join(qs)}' if qs else ''
        context['filter_companies'] = [
            {'key': 'iffco', 'name': 'IFFCO'},
            {'key': 'aramco', 'name': 'Aramco'},
        ]
        context['filter_warehouses'] = []

        data = page_data.get(page)
        if isinstance(page_data, dict) and page_data.get('filter_companies'):
            context['filter_companies'] = page_data['filter_companies']
        if isinstance(page_data, dict) and page_data.get('filter_warehouses'):
            context['filter_warehouses'] = page_data['filter_warehouses']
        if not context['filter_warehouses']:
            dummy_wh = []
            for block in OUTBOUND['companies']:
                if selected != 'all' and block['key'] != selected:
                    continue
                dummy_wh.extend(row['name'] for row in block.get('rows', []) if block.get('layout') == 'warehouse')
            context['filter_warehouses'] = sorted(set(dummy_wh))
        if data:
            companies = data['companies']
            if selected != 'all':
                companies = [c for c in companies if c['key'] == selected]

            context['has_data'] = bool(companies) or page in {'sla', 'inventory'}
            context['year_range'] = data.get('year_range', context['year_range'])
            context['companies'] = companies
            if page == 'dashboard':
                combined_src = [c for c in companies if c.get('key') in ('iffco', 'aramco')] or companies
                context['hc'] = kpi_excel.combine_dashboard(combined_src)
                context['has_data'] = bool(combined_src)
            context['disclaimer'] = data.get('disclaimer', '')
            context['footer_note'] = data.get('footer', '')
            context['agreement'] = data.get('agreement', [])
            context['agreement_title'] = data.get('agreement_title', '')
            context['table_title'] = data.get('table_title', '')
            if page == 'sla':
                cfg = data.get('sla_cfg') or sla_settings.get(selected)
                context['agreement'] = sla_settings.agreement_cards(cfg)
                context['agreement_title'] = data.get('agreement_title') or SLA['agreement_title']
                context['table_title'] = data.get('table_title') or SLA['table_title']
                context['sla_cfg'] = cfg
                context['sla_presets'] = sla_settings.HOUR_PRESETS
                context['sla_editable'] = bool(selected and selected != 'all')
                context['has_data'] = True
                for company in companies:
                    company_cfg = sla_settings.get(company.get('key'))
                    labels = {
                        'Outbound Local Despatch': sla_settings.fmt_hours(company_cfg['local_h']),
                        'Outbound Remote Despatch': sla_settings.fmt_hours(company_cfg['remote_h']),
                        'Outbound CRD': sla_settings.fmt_hours(company_cfg['crd_h']),
                        'Branch Transfers': sla_settings.fmt_hours(company_cfg['transfer_h']),
                        'Inbound Receiving': sla_settings.fmt_hours(company_cfg['inbound_h']),
                        'Inbound GRN': sla_settings.fmt_hours(company_cfg['grn_h']),
                    }
                    for row in company.get('rows', []):
                        if row.get('category') in labels:
                            row['target'] = labels[row['category']]
                context['companies'] = companies
            if data.get('footer'):
                context['kpi_footer'] = data['footer']

        return context


class UploadKpiExcelView(LoginRequiredMixin, View):
    def post(self, request, *args, **kwargs):
        uploaded = request.FILES.get('excel_file')
        if not uploaded:
            messages.error(request, 'Please choose Data_Power_Bi.xlsx first.')
            return redirect(request.META.get('HTTP_REFERER') or reverse('accounts:overview'))

        name = uploaded.name.lower()
        if not name.endswith('.xlsx'):
            messages.error(request, 'Upload an .xlsx file named Data_Power_Bi.xlsx.')
            return redirect(request.META.get('HTTP_REFERER') or reverse('accounts:overview'))

        dest = kpi_excel.storage_path()
        with dest.open('wb') as handle:
            for chunk in uploaded.chunks():
                handle.write(chunk)

        kpi_excel.clear_cache()
        if not kpi_excel.workbook_has_kpi_sheets(dest):
            messages.error(request, 'File saved, but KPI sheets were not found. Check OrderHeader / IBShipments / OBLPN / IBLPN.')
        else:
            messages.success(request, 'Data_Power_Bi.xlsx uploaded. Dashboard now reads live Excel data.')
        return redirect(request.META.get('HTTP_REFERER') or reverse('accounts:overview'))


class SaveSlaTargetsView(LoginRequiredMixin, View):
    def post(self, request, *args, **kwargs):
        company = (request.POST.get('company') or 'all').strip()
        if company in ('all', ''):
            messages.error(request, 'Choose a company first to edit SLA targets.')
            return redirect(reverse('accounts:sla'))
        sla_settings.save(company, request.POST)
        kpi_excel.clear_cache()
        messages.success(request, 'SLA targets saved. Achievement vs Target now uses the new hours.')
        return redirect(f"{reverse('accounts:sla')}?company={company}")
