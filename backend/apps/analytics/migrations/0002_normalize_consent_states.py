from django.db import migrations


def normalize_consent_states(apps, schema_editor):
    WebSession = apps.get_model("analytics", "WebSession")
    WebSession.objects.filter(consent_state__in=["ESSENTIAL", "GRANTED", "granted"]).update(
        consent_state="SESSION_ANALYTICS"
    )
    WebSession.objects.filter(consent_state__in=["DENIED", "denied"]).update(consent_state="LIMITED")


class Migration(migrations.Migration):
    dependencies = [("analytics", "0001_initial")]
    operations = [migrations.RunPython(normalize_consent_states, migrations.RunPython.noop)]
