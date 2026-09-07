from django.contrib import admin
from django.contrib.auth.admin import UserAdmin

from .models import CustomUser, Profile


# Register your models here.
class CustomUserAdmin(admin.ModelAdmin):
    list_display = ('username', 'email', 'is_staff', 'is_admin', 'is_customer', 'is_employee')
    list_filter = ('is_employee', 'is_staff', 'is_active')


admin.site.register(Profile)
# admin.site.register(HierarchicalGroup)
admin.site.register(CustomUser, UserAdmin)
