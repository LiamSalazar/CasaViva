from django.db import migrations


def unpublish_unverified(apps, schema_editor):
    Listing = apps.get_model("listings", "Listing")
    Listing.objects.filter(is_published=True, offering__promotion_authorized=False).update(is_published=False, published_at=None)


class Migration(migrations.Migration):
    dependencies = [("catalog", "0004_propertyoffering_information_verified_at_and_more"), ("listings", "0004_pricerecord_promotion_conditions_and_more")]
    operations = [migrations.RunPython(unpublish_unverified, migrations.RunPython.noop)]
