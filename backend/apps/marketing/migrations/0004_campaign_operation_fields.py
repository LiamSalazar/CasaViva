from django.db import migrations, models


def normalize_channels(apps, schema_editor):
    Campaign = apps.get_model("marketing", "MarketingCampaign")
    for campaign in Campaign.objects.all():
        raw = (campaign.channel or "").lower()
        campaign.channel = "INSTAGRAM" if raw in {"instagram", "ig"} else "FACEBOOK" if raw in {"facebook", "fb", "meta"} else "TIKTOK" if raw == "tiktok" else "GOOGLE" if raw == "google" else "OTHER"
        campaign.utm_source = {"INSTAGRAM": "instagram", "FACEBOOK": "facebook", "TIKTOK": "tiktok", "GOOGLE": "google"}.get(campaign.channel, "other")
        campaign.utm_medium = "paid_search" if campaign.channel == "GOOGLE" else "paid_social"
        campaign.save(update_fields=["channel", "utm_source", "utm_medium"])


class Migration(migrations.Migration):
    dependencies = [("marketing", "0003_marketingspend_is_voided_marketingspend_void_reason_and_more")]
    operations = [
        migrations.AddField(model_name="marketingcampaign", name="planned_budget", field=models.DecimalField(decimal_places=2, default=0, max_digits=14)),
        migrations.AddField(model_name="marketingcampaign", name="utm_source", field=models.CharField(default="other", max_length=120), preserve_default=False),
        migrations.AddField(model_name="marketingcampaign", name="utm_medium", field=models.CharField(default="paid_social", max_length=120), preserve_default=False),
        migrations.AddField(model_name="marketingcampaign", name="default_landing_path", field=models.CharField(default="/", max_length=500)),
        migrations.RunPython(normalize_channels, migrations.RunPython.noop),
        migrations.AlterField(model_name="marketingcampaign", name="channel", field=models.CharField(choices=[("INSTAGRAM", "Instagram"), ("FACEBOOK", "Facebook"), ("TIKTOK", "TikTok"), ("GOOGLE", "Google"), ("OTHER", "Otro")], max_length=20)),
    ]
