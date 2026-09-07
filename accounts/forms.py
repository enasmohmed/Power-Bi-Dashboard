from django import forms
from django.contrib.auth.forms import UserCreationForm

from accounts.models import CustomUser


class CustomUserCreationForm(UserCreationForm):
    role = forms.ChoiceField(choices=CustomUser.ROLE_CHOICES)

    class Meta:
        model = CustomUser
        fields = ('username', 'email', 'password1', 'password2', 'role')

    def save(self, commit=True):
        user = super().save(commit=False)
        user.is_approved = False  # الحساب غير مفعل افتراضياً
        user.is_active = False  # الحساب غير نشط افتراضياً
        if user.role in ['employee', 'admin', 'customer']:
            user.is_staff = True
            user.is_active = True
        if commit:
            user.save()
        return user


class ProfileForm(forms.ModelForm):
    class Meta:
        model = CustomUser
        fields = ['username', 'email', 'role']


class UploadFileForm(forms.Form):
    file = forms.FileField(label="Upload CSV/Excel")