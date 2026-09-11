from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [("crm", "0005_privacynoticeversion_one_active_privacy_notice_and_more")]

    operations = [
        migrations.AddField(
            model_name="privacynoticeversion",
            name="production_ready",
            field=models.BooleanField(
                default=False,
                help_text="Revisión explícita contra el modelo legal vigente; las versiones legacy no satisfacen readiness.",
            ),
        ),
        migrations.AddField(
            model_name="termsofuseversion",
            name="production_ready",
            field=models.BooleanField(
                default=False,
                help_text="Revisión explícita contra el modelo legal vigente; las versiones legacy no satisfacen readiness.",
            ),
        ),
    ]
