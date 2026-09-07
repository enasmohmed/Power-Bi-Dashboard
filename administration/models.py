from django.contrib.auth import get_user_model
from django.db import models
from django.db.models.signals import post_save
from django.dispatch import receiver

# Create your models here.

User = get_user_model()


class Company(models.Model):
    hc_business = models.CharField(max_length=255)
    employees = models.ManyToManyField(User, related_name='admin_data_accessible_companies', blank=True)

    def __str__(self):
        return self.hc_business


class EmployeeProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='admin_employee_profile')
    company = models.ForeignKey(Company, on_delete=models.CASCADE, related_name='admin_employees')
    role = models.CharField(max_length=20, choices=User.ROLE_CHOICES)

    def __str__(self):
        return f"{self.user.username} - {self.company} - {self.role}"


# Signal to create EmployeeProfile for new users
@receiver(post_save, sender=User)
def create_employee_profile(sender, instance, created, **kwargs):
    if created and not hasattr(instance, 'admin_employee_profile'):
        default_company = Company.objects.exclude(admin_employees__isnull=True).first()
        if default_company:
            EmployeeProfile.objects.create(user=instance, company=default_company, role='Employee')


class AdminData(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    company = models.ForeignKey(Company, on_delete=models.CASCADE)
    total_quantities = models.IntegerField(blank=True, null=True)
    total_no_of_employees = models.IntegerField(blank=True, null=True)

    def __str__(self):
        return f'{self.user.username} - {self.company}'


class AdminInbound(models.Model):
    time = models.DateField()
    admin_data = models.ForeignKey(AdminData, on_delete=models.CASCADE, default=1)

    class Weekday(models.TextChoices):
        mon = "Monday", "Monday"
        tue = "Tuesday", "Tuesday"
        wed = "Wednesday", "Wednesday"
        thu = "Thursday", "Thursday"
        fri = "Friday", "Friday"
        sund = "Sunday", "Sunday"

    assigned_day = models.CharField(max_length=10, choices=Weekday.choices)
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

    def __str__(self):
        return str(self.id)


class AdminOutbound(models.Model):
    time = models.DateField()
    admin_data = models.ForeignKey(AdminData, on_delete=models.CASCADE, default=1)

    class Weekday(models.TextChoices):
        mon = "Monday", "Monday"
        tue = "Tuesday", "Tuesday"
        wed = "Wednesday", "Wednesday"
        thu = "Thursday", "Thursday"
        fri = "Friday", "Friday"
        sund = "Sunday", "Sunday"

    assigned_day = models.CharField(max_length=10, choices=Weekday.choices)
    tender = models.IntegerField(blank=True, null=True)
    private = models.IntegerField(blank=True, null=True)
    lines = models.IntegerField(blank=True, null=True)
    total_quantities = models.IntegerField(blank=True, null=True)
    bulk = models.IntegerField(blank=True, null=True)
    loose = models.IntegerField(blank=True, null=True)
    pending_orders = models.IntegerField(blank=True, null=True)

    def __str__(self):
        return str(self.id)


class AdminReturns(models.Model):
    time = models.DateField()
    admin_data = models.ForeignKey(AdminData, on_delete=models.CASCADE, default=1)

    class Weekday(models.TextChoices):
        mon = "Monday", "Monday"
        tue = "Tuesday", "Tuesday"
        wed = "Wednesday", "Wednesday"
        thu = "Thursday", "Thursday"
        fri = "Friday", "Friday"
        sund = "Sunday", "Sunday"

    assigned_day = models.CharField(max_length=10, choices=Weekday.choices)
    number_of_return = models.IntegerField(blank=True, null=True)
    number_of_lines = models.IntegerField(blank=True, null=True)
    total_quantities = models.IntegerField(blank=True, null=True)

    def __str__(self):
        return str(self.id)


class AdminCapacity(models.Model):
    time = models.DateField()
    admin_data = models.ForeignKey(AdminData, on_delete=models.CASCADE, default=1)

    class Weekday(models.TextChoices):
        mon = "Monday", "Monday"
        tue = "Tuesday", "Tuesday"
        wed = "Wednesday", "Wednesday"
        thu = "Thursday", "Thursday"
        fri = "Friday", "Friday"
        sund = "Sunday", "Sunday"

    assigned_day = models.CharField(max_length=10, choices=Weekday.choices)
    WH_storage = models.IntegerField(blank=True, null=True)
    occupied_location = models.IntegerField(blank=True, null=True)
    available_location = models.IntegerField(blank=True, null=True)


    def __str__(self):
        return str(self.id)


class AdminInventory(models.Model):
    time = models.DateField()
    admin_data = models.ForeignKey(AdminData, on_delete=models.CASCADE, default=1)

    class Weekday(models.TextChoices):
        mon = "Monday", "Monday"
        tue = "Tuesday", "Tuesday"
        wed = "Wednesday", "Wednesday"
        thu = "Thursday", "Thursday"
        fri = "Friday", "Friday"
        sund = "Sunday", "Sunday"

    assigned_day = models.CharField(max_length=10, choices=Weekday.choices)
    last_movement = models.IntegerField(blank=True, null=True)

    def __str__(self):
        return str(self.id)
