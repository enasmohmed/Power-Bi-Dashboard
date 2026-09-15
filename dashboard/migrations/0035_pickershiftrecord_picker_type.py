from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("dashboard", "0034_picker_sap_line_fields"),
    ]

    operations = [
        migrations.AddField(
            model_name="pickershiftrecord",
            name="picker_type",
            field=models.CharField(
                blank=True,
                default="",
                help_text='SAP column Type (e.g. "Operator").',
                max_length=64,
                verbose_name="Type",
            ),
        ),
    ]
