from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("dashboard", "0036_pickershiftrecord_business"),
    ]

    operations = [
        migrations.AddField(
            model_name="pickershiftrecord",
            name="is_overtime",
            field=models.BooleanField(
                blank=True,
                help_text="True when confirmation time is after the shift window that creation time falls in.",
                null=True,
                verbose_name="After shift end",
            ),
        ),
    ]
