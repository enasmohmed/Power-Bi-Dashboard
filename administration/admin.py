from django.contrib import admin

from administration.models import AdminData, AdminInbound, AdminOutbound, AdminReturns, AdminCapacity, AdminInventory, \
    EmployeeProfile, Company

# Register your models here.

admin.site.register(Company)
admin.site.register(AdminData)
admin.site.register(EmployeeProfile)
admin.site.register(AdminInbound)
admin.site.register(AdminOutbound)
admin.site.register(AdminReturns)
admin.site.register(AdminCapacity)
admin.site.register(AdminInventory)
