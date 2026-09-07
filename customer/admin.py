from django.contrib import admin

from customer.models import CustomerInbound, CustomerReturns, CustomerExpiry, CustomerDamage, \
    CustomerInventory, CustomerPalletLocationAvailability, CustomerHSE, Customer, EmployeeProfile, CustomerWHOutbound, \
    CustomerTransportationOutbound

# Register your models here.


admin.site.register(Customer)
admin.site.register(EmployeeProfile)
admin.site.register(CustomerInbound)
admin.site.register(CustomerTransportationOutbound)
admin.site.register(CustomerWHOutbound)
admin.site.register(CustomerReturns)
admin.site.register(CustomerExpiry)
admin.site.register(CustomerDamage)
admin.site.register(CustomerInventory)
admin.site.register(CustomerPalletLocationAvailability)
admin.site.register(CustomerHSE)
