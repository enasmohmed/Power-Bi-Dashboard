from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("dashboard", "0035_pickershiftrecord_picker_type"),
    ]

    operations = [
        migrations.AddField(
            model_name="pickershiftrecord",
            name="business",
            field=models.CharField(
                blank=True,
                db_index=True,
                default="",
                help_text="Company name from the Excel Business column.",
                max_length=128,
                verbose_name="Business",
            ),
        ),
        migrations.AlterField(
            model_name="pickerperformanceprogram",
            name="excel_sheet_name",
            field=models.CharField(
                default="Data",
                help_text="Sheet to read on Admin import (use Data for Picking .xlsx). If missing, import tries Data then the first sheet.",
                max_length=64,
                verbose_name="Excel sheet name",
            ),
        ),
    ]
