from django import forms

from administration.models import AdminInventory, AdminCapacity, AdminReturns, AdminOutbound, AdminInbound, AdminData, \
    Company, EmployeeProfile


class DateInput(forms.DateInput):
    input_type = 'date'


class CompanyForm(forms.ModelForm):
    class Meta:
        model = Company
        fields = ['hc_business', 'employees']

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        instance = kwargs.get('instance')
        if instance:
            self.fields['hc_business'].disabled = True  # تعطيل حقل اسم الشركة
            self.fields['hc_business'].widget.attrs['readonly'] = True
            self.fields['employees'].widget = forms.HiddenInput()  # إخفاء حقل الموظفين


class EmployeeProfileForm(forms.ModelForm):
    class Meta:
        model = EmployeeProfile
        fields = ['user', 'company', 'role']

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        instance = kwargs.get('instance')
        if instance:
            self.fields['user'].disabled = True  # تعطيل حقل المستخدم
            self.fields['user'].widget.attrs['readonly'] = True
            self.fields['company'].disabled = True  # تعطيل حقل الشركة
            self.fields['company'].widget.attrs['readonly'] = True
            self.fields['role'].widget = forms.HiddenInput()  # إخفاء حقل الدور


class AdminDataForm(forms.ModelForm):
    class Meta:
        model = AdminData
        fields = ['total_quantities', 'total_no_of_employees']

    def __init__(self, *args, **kwargs):
        user = kwargs.pop('user', None)  # استخراج user من kwargs إذا كان متوفرًا
        super().__init__(*args, **kwargs)
        if user:
            self.fields['user'] = forms.CharField(initial=user.username, disabled=True)
            try:
                employee_profile = EmployeeProfile.objects.get(user=user)
                self.fields['company'] = forms.CharField(initial=employee_profile.company.hc_business, disabled=True)
            except EmployeeProfile.DoesNotExist:
               pass


class AdminInboundForm(forms.ModelForm):
    class Meta:
        model = AdminInbound
        fields = ['time', 'assigned_day', 'number_of_vehicles_daily', 'number_of_pallets', 'bulk', 'loose', 'cold',
                  'frozen', 'ambient', 'pending_shipments', 'number_of_shipments', 'total_quantity', 'number_of_line']
        widgets = {
            'time': DateInput(),
        }


class AdminOutboundForm(forms.ModelForm):
    class Meta:
        model = AdminOutbound
        fields = ['time', 'assigned_day', 'tender', 'private', 'lines', 'total_quantities', 'bulk', 'loose',
                  'pending_orders']
        widgets = {
            'time': DateInput(),
        }


class AdminReturnsForm(forms.ModelForm):
    class Meta:
        model = AdminReturns
        fields = ['time', 'assigned_day', 'number_of_return', 'number_of_lines', 'total_quantities']
        widgets = {
            'time': DateInput(),
        }


class AdminCapacityForm(forms.ModelForm):
    class Meta:
        model = AdminCapacity
        fields = ['time', 'assigned_day', 'WH_storage', 'occupied_location', 'available_location']
        widgets = {
            'time': DateInput(),
        }


class AdminInventoryForm(forms.ModelForm):
    class Meta:
        model = AdminInventory
        fields = ['time', 'assigned_day', 'last_movement']
        widgets = {
            'time': DateInput(),
        }
