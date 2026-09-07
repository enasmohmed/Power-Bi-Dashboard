# forms.py
from django import forms

from customer.models import CustomerInbound, Customer, CustomerReturns, CustomerExpiry, \
    CustomerDamage, CustomerPalletLocationAvailability, CustomerHSE, EmployeeProfile, \
    CustomerInventory, CustomerTransportationOutbound, CustomerWHOutbound


class DateInput(forms.DateInput):
    input_type = 'date'


class CustomerForm(forms.ModelForm):
    username = forms.CharField(label='User', required=False, disabled=True)  # حقل لعرض اسم المستخدم

    class Meta:
        model = Customer
        fields = ['name_company']

    def __init__(self, *args, **kwargs):
        user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            field.required = False

        if user:
            self.fields['username'].initial = user.username
            company = None

            if user.groups.filter(name='Employee').exists():
                emp_profile = EmployeeProfile.objects.filter(user=user).first()
                if emp_profile:
                    companies = emp_profile.company.all()
                    if companies.exists():
                        company = companies.first()
            elif user.groups.filter(name='Customer').exists():
                company = Customer.objects.filter(employees__user=user).first()

            if company:
                self.fields['name_company'].initial = company.name_company
                self.fields['name_company'].disabled = True


class EmployeeProfileForm(forms.ModelForm):
    class Meta:
        model = EmployeeProfile
        fields = ['user', 'company', 'role']

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        instance = kwargs.get('instance')
        if instance:
            self.fields['user'].disabled = True  # Disable user field
            self.fields['user'].widget.attrs['readonly'] = True
            self.fields['company'].disabled = True  # Disable company field
            self.fields['company'].widget.attrs['readonly'] = True
            self.fields['role'].widget = forms.HiddenInput()  # Hide role field


class CustomerInboundForm(forms.ModelForm):
    class Meta:
        model = CustomerInbound
        fields = ['time', 'assigned_day', 'number_of_vehicles_daily', 'number_of_pallets', 'bulk', 'loose', 'cold',
                  'frozen', 'ambient', 'pending_shipments', 'number_of_shipments', 'total_quantity', 'number_of_line']
        widgets = {
            'time': DateInput(),
        }


class CustomerTransportationOutboundForm(forms.ModelForm):
    class Meta:
        model = CustomerTransportationOutbound
        fields = ['time', 'assigned_day', 'released_order', 'pending_pick_orders',
                  'piked_order','number_of_PODs_collected_on_time','number_of_PODs_collected_Late']
        widgets = {
            'time': DateInput(),
        }


class CustomerWHOutboundForm(forms.ModelForm):
    class Meta:
        model = CustomerWHOutbound
        fields = ['time', 'assigned_day', 'released_order', 'pending_pick_orders',
                  'piked_order', 'number_of_PODs_collected_on_time','number_of_PODs_collected_Late']
        widgets = {
            'time': DateInput(),
        }


class CustomerReturnsForm(forms.ModelForm):
    class Meta:
        model = CustomerReturns
        fields = ['time', 'assigned_day', 'total_orders_items_returned',
                  'number_of_return_items_orders_updated_on_time', 'number_of_return_items_orders_updated_late']
        widgets = {
            'time': DateInput(),
        }


class CustomerExpiryForm(forms.ModelForm):
    class Meta:
        model = CustomerExpiry
        fields = ['time', 'assigned_day', 'total_SKUs_expired', 'total_expired_SKUS_disposed',
                  'nearly_expired_1_to_3_months', 'nearly_expired_3_to_6_months']
        widgets = {
            'time': DateInput(),
        }


class CustomerDamageForm(forms.ModelForm):
    class Meta:
        model = CustomerDamage
        fields = ['time', 'assigned_day', 'Total_QTYs_Damaged_by_WH', 'Number_of_Damaged_during_receiving',
                  'Total_Araive_Damaged']
        widgets = {
            'time': DateInput(),
        }


class CustomerInventoryForm(forms.ModelForm):
    class Meta:
        model = CustomerInventory
        fields = ['time', 'assigned_day', 'Total_Locations_match', 'Total_Locations_not_match']
        widgets = {
            'time': DateInput(),
        }


class CustomerPalletLocationAvailabilityForm(forms.ModelForm):
    class Meta:
        model = CustomerPalletLocationAvailability
        fields = ['time', 'assigned_day', 'Total_Storage_Pallet', 'Total_Storage_Bin', 'Total_Storage_pallet_empty',
                  'Total_Storage_Bin_empty', 'Total_occupied_pallet_location', 'Total_occupied_Bin_location']
        widgets = {
            'time': DateInput(),
        }


class CustomerHSEForm(forms.ModelForm):
    class Meta:
        model = CustomerHSE
        fields = ['time', 'assigned_day', 'Total_Incidents_on_the_side']
        widgets = {
            'time': DateInput(),
        }



class UploadCustomerDataForm(forms.Form):
    company = forms.ModelChoiceField(
        queryset=Customer.objects.none(),  # الافتراضي فاضي
        label="Choose the company",
        widget=forms.Select(attrs={"class": "form-control"})
    )
    file = forms.FileField(label="Upload Excel file")

    def __init__(self, *args, user=None, **kwargs):
        super().__init__(*args, **kwargs)

        if user and hasattr(user, "employee_profile"):
            companies_qs = user.employee_profile.company.all()
            self.fields["company"].queryset = companies_qs

            # ممكن تحط أول شركة كقيمة افتراضية
            first = companies_qs.first()
            if first:
                self.fields["company"].initial = first
