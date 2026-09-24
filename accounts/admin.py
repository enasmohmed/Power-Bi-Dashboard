from django.contrib import admin
from django.contrib.auth.admin import UserAdmin

from .models import CustomUser, InboundShipmentReview, Profile


# Register your models here.
class CustomUserAdmin(admin.ModelAdmin):
    list_display = ('username', 'email', 'is_staff', 'is_admin', 'is_customer', 'is_employee')
    list_filter = ('is_employee', 'is_staff', 'is_active')


@admin.register(InboundShipmentReview)
class InboundShipmentReviewAdmin(admin.ModelAdmin):
    list_display = ("shipment_nbr", "warehouse", "company", "status", "proposed_result", "approved_result", "submitted_at")
    list_filter = ("status", "company")
    search_fields = ("shipment_nbr", "shipment_key", "warehouse", "proposed_reason", "approved_reason")


admin.site.register(Profile)
# admin.site.register(HierarchicalGroup)
admin.site.register(CustomUser, UserAdmin)
