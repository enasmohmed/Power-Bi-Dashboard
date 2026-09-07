from django.db import models

from accounts.models import CustomUser
from project import settings


# Create your models here.


class Customer(models.Model):
    name_company = models.CharField(max_length=255, blank=True, null=True)

    def __str__(self):
        return self.name_company


class EmployeeProfile(models.Model):
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='employee_profile')
    company = models.ManyToManyField(Customer, related_name='employees')
    role = models.CharField(max_length=20, choices=CustomUser.ROLE_CHOICES)

    def __str__(self):
        # لا تستخدم company.name_company مباشرة لأن company هو M2M
        names = ", ".join([c.name_company for c in self.company.all()])
        return f"{self.user.username} - {names}"



class CustomerInbound(models.Model):
    company = models.ForeignKey(Customer, on_delete=models.CASCADE, related_name='inbounds')
    time = models.DateField(blank=True, null=True)


    class Weekday(models.TextChoices):
        mon = "Monday", "Monday"
        tue = "Tuesday", "Tuesday"
        wed = "Wednesday", "Wednesday"
        thu = "Thursday", "Thursday"
        fri = "Friday", "Friday"
        sund = "Sunday", "Sunday"

    assigned_day = models.CharField(max_length=10, choices=Weekday.choices , blank=True, null=True)
    number_of_vehicles_daily = models.IntegerField(blank=True, null=True)
    number_of_pallets = models.IntegerField(blank=True, null=True)
    bulk = models.IntegerField(blank=True, null=True)
    loose = models.IntegerField(blank=True, null=True)
    cold = models.IntegerField(blank=True, null=True)
    frozen = models.IntegerField(blank=True, null=True)
    ambient = models.IntegerField(blank=True, null=True)
    pending_shipments = models.IntegerField(blank=True, null=True)
    number_of_shipments = models.IntegerField(blank=True, null=True)
    total_quantity = models.IntegerField(blank=True, null=True)
    number_of_line = models.IntegerField(blank=True, null=True)

    # أضف created_at و updated_at
    created_at = models.DateTimeField(auto_now_add=True, null=True, blank=True)
    updated_at = models.DateTimeField(auto_now=True, null=True, blank=True)

    def __str__(self):
        return str(self.id)


class CustomerTransportationOutbound(models.Model):
    company = models.ForeignKey(Customer, on_delete=models.CASCADE, related_name='outbounds')

    time = models.DateField(blank=True, null=True)


    class Weekday(models.TextChoices):
        mon = "Monday", "Monday"
        tue = "Tuesday", "Tuesday"
        wed = "Wednesday", "Wednesday"
        thu = "Thursday", "Thursday"
        fri = "Friday", "Friday"
        sund = "Sunday", "Sunday"

    assigned_day = models.CharField(max_length=20, choices=Weekday.choices, blank=True, null=True)

    released_order = models.IntegerField(blank=True, null=True)
    pending_pick_orders = models.IntegerField(blank=True, null=True)
    piked_order = models.IntegerField(blank=True, null=True)
    number_of_PODs_collected_on_time = models.IntegerField(blank=True, null=True)
    number_of_PODs_collected_Late = models.IntegerField(blank=True, null=True)

    # أضف created_at و updated_at
    created_at = models.DateTimeField(auto_now_add=True, null=True, blank=True)
    updated_at = models.DateTimeField(auto_now=True, null=True, blank=True)


    def __str__(self):
            return str(self.id)


class CustomerWHOutbound(models.Model):
    company = models.ForeignKey(Customer, on_delete=models.CASCADE, related_name='wh_outbounds')

    time = models.DateField(blank=True, null=True)


    class Weekday(models.TextChoices):
        mon = "Monday", "Monday"
        tue = "Tuesday", "Tuesday"
        wed = "Wednesday", "Wednesday"
        thu = "Thursday", "Thursday"
        fri = "Friday", "Friday"
        sund = "Sunday", "Sunday"

    assigned_day = models.CharField(max_length=20, choices=Weekday.choices, blank=True, null=True)

    released_order = models.IntegerField(blank=True, null=True)
    pending_pick_orders = models.IntegerField(blank=True, null=True)
    piked_order = models.IntegerField(blank=True, null=True)
    number_of_PODs_collected_on_time = models.IntegerField(blank=True, null=True)
    number_of_PODs_collected_Late = models.IntegerField(blank=True, null=True)

    # أضف created_at و updated_at
    created_at = models.DateTimeField(auto_now_add=True, null=True, blank=True)
    updated_at = models.DateTimeField(auto_now=True, null=True, blank=True)

    # number_of_order_not_yet_picked = models.IntegerField(blank=True, null=True)
    # number_of_orders_picked_but_not_yet_ready_for_disptch_in_progress = models.IntegerField(blank=True, null=True)
    # number_of_orders_waiting_for_qc = models.IntegerField(blank=True, null=True)
    # number_of_orders_that_are_ready_for_dispatch = models.IntegerField(blank=True, null=True)
    # justification_for_the_delay_order_by_order = models.IntegerField(blank=True, null=True)
    # total_skus_picked = models.IntegerField(blank=True, null=True)
    # total_number_of_SKU_discripancy_in_Order = models.IntegerField(blank=True, null=True)



    def __str__(self):
        return str(self.id)


class CustomerReturns(models.Model):
    company = models.ForeignKey(Customer, on_delete=models.CASCADE, related_name='returns')

    time = models.DateField(blank=True, null=True)


    class Weekday(models.TextChoices):
        mon = "Monday", "Monday"
        tue = "Tuesday", "Tuesday"
        wed = "Wednesday", "Wednesday"
        thu = "Thursday", "Thursday"
        fri = "Friday", "Friday"
        sund = "Sunday", "Sunday"

    assigned_day = models.CharField(max_length=20, choices=Weekday.choices, blank=True, null=True)

    total_orders_items_returned = models.IntegerField(blank=True, null=True)
    number_of_return_items_orders_updated_on_time = models.IntegerField(blank=True, null=True)
    number_of_return_items_orders_updated_late = models.IntegerField(blank=True, null=True)

    # أضف created_at و updated_at
    created_at = models.DateTimeField(auto_now_add=True, null=True, blank=True)
    updated_at = models.DateTimeField(auto_now=True, null=True, blank=True)

    def __str__(self):
        return str(self.id)


class CustomerExpiry(models.Model):
    company = models.ForeignKey(Customer, on_delete=models.CASCADE, related_name='expiries')

    time = models.DateField(blank=True, null=True)


    class Weekday(models.TextChoices):
        mon = "Monday", "Monday"
        tue = "Tuesday", "Tuesday"
        wed = "Wednesday", "Wednesday"
        thu = "Thursday", "Thursday"
        fri = "Friday", "Friday"
        sund = "Sunday", "Sunday"

    assigned_day = models.CharField(max_length=20, choices=Weekday.choices, blank=True, null=True)
    total_SKUs_expired = models.IntegerField(blank=True, null=True)
    total_expired_SKUS_disposed = models.IntegerField(blank=True, null=True)
    nearly_expired_1_to_3_months = models.IntegerField(blank=True, null=True)
    nearly_expired_3_to_6_months = models.IntegerField(blank=True, null=True)

    # أضف created_at و updated_at
    created_at = models.DateTimeField(auto_now_add=True, null=True, blank=True)
    updated_at = models.DateTimeField(auto_now=True, null=True, blank=True)

    def save(self, *args, **kwargs):
        self.total_SKUs_expired = (
                (self.nearly_expired_1_to_3_months or 0) +
                (self.nearly_expired_3_to_6_months or 0) +
                (self.total_expired_SKUS_disposed or 0)
        )
        super().save(*args, **kwargs)

    def __str__(self):
        return str(self.id)


class CustomerDamage(models.Model):
    company = models.ForeignKey(Customer, on_delete=models.CASCADE, related_name='damages')

    time = models.DateField(blank=True, null=True)


    class Weekday(models.TextChoices):
        mon = "Monday", "Monday"
        tue = "Tuesday", "Tuesday"
        wed = "Wednesday", "Wednesday"
        thu = "Thursday", "Thursday"
        fri = "Friday", "Friday"
        sund = "Sunday", "Sunday"

    assigned_day = models.CharField(max_length=20, choices=Weekday.choices, blank=True, null=True)
    Total_QTYs_Damaged_by_WH = models.IntegerField(blank=True, null=True)
    Number_of_Damaged_during_receiving = models.IntegerField(blank=True, null=True)
    Total_Araive_Damaged = models.IntegerField(blank=True, null=True)

    # أضف created_at و updated_at
    created_at = models.DateTimeField(auto_now_add=True, null=True, blank=True)
    updated_at = models.DateTimeField(auto_now=True, null=True, blank=True)

    def __str__(self):
        return str(self.id)


class CustomerInventory(models.Model):
    company = models.ForeignKey(Customer, on_delete=models.CASCADE, related_name='inventories')

    time = models.DateField(blank=True, null=True)


    class Weekday(models.TextChoices):
        mon = "Monday", "Monday"
        tue = "Tuesday", "Tuesday"
        wed = "Wednesday", "Wednesday"
        thu = "Thursday", "Thursday"
        fri = "Friday", "Friday"
        sund = "Sunday", "Sunday"

    assigned_day = models.CharField(max_length=20, choices=Weekday.choices, blank=True, null=True)
    Total_Locations_match = models.IntegerField(blank=True, null=True)
    Total_Locations_not_match = models.IntegerField(blank=True, null=True)

    # أضف created_at و updated_at
    created_at = models.DateTimeField(auto_now_add=True, null=True, blank=True)
    updated_at = models.DateTimeField(auto_now=True, null=True, blank=True)

    def __str__(self):
        return str(self.id)


class CustomerPalletLocationAvailability(models.Model):
    customer = models.ForeignKey(Customer, on_delete=models.CASCADE, related_name="pallet_location_availability")

    time = models.DateField(blank=True, null=True)

    class Weekday(models.TextChoices):
        mon = "Monday", "Monday"
        tue = "Tuesday", "Tuesday"
        wed = "Wednesday", "Wednesday"
        thu = "Thursday", "Thursday"
        fri = "Friday", "Friday"
        sund = "Sunday", "Sunday"

    assigned_day = models.CharField(max_length=20, choices=Weekday.choices, blank=True, null=True)
    Total_Storage_Pallet = models.IntegerField(blank=True, null=True)
    Total_Storage_pallet_empty = models.IntegerField(blank=True, null=True)
    Total_occupied_pallet_location = models.IntegerField(blank=True, null=True)

    Total_Storage_Bin = models.IntegerField(blank=True, null=True)
    Total_Storage_Bin_empty = models.IntegerField(blank=True, null=True)
    Total_occupied_Bin_location = models.IntegerField(blank=True, null=True)

    created_at = models.DateTimeField(auto_now_add=True, null=True, blank=True)
    updated_at = models.DateTimeField(auto_now=True, null=True, blank=True)

    def __str__(self):
        return str(self.id)


class CustomerHSE(models.Model):
    company = models.ForeignKey(Customer, on_delete=models.CASCADE, related_name='hses')

    time = models.DateField(blank=True, null=True)


    class Weekday(models.TextChoices):
        mon = "Monday", "Monday"
        tue = "Tuesday", "Tuesday"
        wed = "Wednesday", "Wednesday"
        thu = "Thursday", "Thursday"
        fri = "Friday", "Friday"
        sund = "Sunday", "Sunday"

    assigned_day = models.CharField(max_length=20, choices=Weekday.choices, blank=True, null=True)
    Total_Incidents_on_the_side = models.IntegerField(blank=True, null=True)

    # أضف created_at و updated_at
    created_at = models.DateTimeField(auto_now_add=True, null=True, blank=True)
    updated_at = models.DateTimeField(auto_now=True, null=True, blank=True)

    def __str__(self):
        return str(self.id)



class UploadedExcelData(models.Model):
    date = models.DateField()
    shipment_number = models.CharField(max_length=100)
    data = models.JSONField()   # يخزن الصف كله كـ JSON
    uploaded_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ("date", "shipment_number")  # يمنع التكرار
