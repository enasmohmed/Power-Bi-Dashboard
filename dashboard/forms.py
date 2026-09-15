from django import forms

from .models import DashboardWorkbook


class ExcelUploadForm(forms.Form):
    excel_file = forms.FileField(
        label="Select Excel file",
        required=True,
        widget=forms.ClearableFileInput(
            attrs={
                "class": "form-control",
                "accept": ".xlsx,.xlsm",
            }
        ),
    )


class ExcelUploadAdminForm(forms.Form):
    """Plain file input for Django admin (avoid Bootstrap `form-control` hiding the control)."""

    excel_file = forms.FileField(
        label="Excel file (.xlsx)",
        required=True,
        widget=forms.FileInput(attrs={"accept": ".xlsx,.xlsm", "size": 40}),
    )


class DashboardWorkbookAdminForm(forms.ModelForm):
    """Validate Daily Tracker sheet and attach parsed JSON to the instance (saved in Admin.save_model)."""

    class Meta:
        model = DashboardWorkbook
        fields = ("title", "file", "is_active")

    def clean(self):
        from .daily_tracker_parse import parse_daily_tracker_workbook

        cleaned_data = super().clean()
        f = cleaned_data.get("file")
        if f is False:
            self.instance.parsed_snapshot = None
            return cleaned_data
        if not f:
            if not self.instance.pk:
                raise forms.ValidationError({"file": "Upload an Excel workbook (.xlsx or .xlsm)."})
            return cleaned_data
        raw = f.read()
        if hasattr(f, "seek"):
            f.seek(0)
        try:
            self.instance.parsed_snapshot = parse_daily_tracker_workbook(raw)
        except ValueError as exc:
            raise forms.ValidationError({"file": str(exc)}) from exc
        return cleaned_data
