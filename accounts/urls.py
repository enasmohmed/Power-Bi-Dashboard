from django.contrib.auth import views as auth_views
from django.urls import path

from customer.views import CustomerDashboardView
from . import views
from .views import RegisterView, CustomLogoutView, CustomLoginView, EmployeeDashboardView, \
    redirect_to_dashboard, ChooseDashboardView, ApproveUsersView

app_name = 'accounts'

urlpatterns = [
    path('register/', RegisterView.as_view(), name='register'),
    path('approve_users/', ApproveUsersView.as_view(), name='approve_users'),
    path('login/', CustomLoginView.as_view(), name='login'),
    path('logout/', CustomLogoutView.as_view(), name='logout'),

    path('admin_dashboard/', views.DashboardPageView.as_view(), name='admin_dashboard'),
    path('customer_dashboard/', CustomerDashboardView.as_view(), name='customer_dashboard'),
    path('home/', redirect_to_dashboard, name='redirect_to_dashboard'),
    path('choose_dashboard/', ChooseDashboardView.as_view(), name='choose_dashboard'),


    path('employee_dashboard/', EmployeeDashboardView.as_view(), name='employee_dashboard'),

    path('user_profile', views.user_profile, name="user_profile"),
    path('user_cards', views.user_cards, name="user_cards"),

    # تغيير كلمة المرور
    path('accounts/password_change/', auth_views.PasswordChangeView.as_view(), name='password_change'),

    # إعادة تعيين كلمة المرور
    path('accounts/password_reset/', auth_views.PasswordResetView.as_view(), name='password_reset'),
    path('accounts/password_reset/done/', auth_views.PasswordResetDoneView.as_view(), name='password_reset_done'),
    path('accounts/reset/<uidb64>/<token>/', auth_views.PasswordResetConfirmView.as_view(),
         name='password_reset_confirm'),
    path('accounts/reset/done/', auth_views.PasswordResetCompleteView.as_view(), name='password_reset_complete'),


    path('upload-kpi-excel/', views.UploadKpiExcelView.as_view(), name='upload_kpi_excel'),
    path('dashboard/', views.DashboardPageView.as_view(), {'page': 'dashboard'}, name='dashboard'),
    path('overview/', views.DashboardPageView.as_view(), {'page': 'overview'}, name='overview'),
    path('outbound/', views.DashboardPageView.as_view(), {'page': 'outbound'}, name='outbound'),
    path('outbound/review/', views.SubmitInboundReviewView.as_view(), name='outbound_review'),
    path('outbound/review/decide/', views.DecideInboundReviewView.as_view(), name='outbound_review_decide'),
    path('inbound/', views.DashboardPageView.as_view(), {'page': 'inbound'}, name='inbound'),
    path('inbound/review/', views.SubmitInboundReviewView.as_view(), name='inbound_review'),
    path('inbound/review/decide/', views.DecideInboundReviewView.as_view(), name='inbound_review_decide'),
    path('cities/', views.DashboardPageView.as_view(), {'page': 'cities'}, name='cities'),
    path('inventory/', views.DashboardPageView.as_view(), {'page': 'inventory'}, name='inventory'),
    path('sla/', views.DashboardPageView.as_view(), {'page': 'sla'}, name='sla'),
    path('sla/save/', views.SaveSlaTargetsView.as_view(), name='save_sla_targets'),
    path('misses/', views.DashboardPageView.as_view(), {'page': 'misses'}, name='misses'),
]
