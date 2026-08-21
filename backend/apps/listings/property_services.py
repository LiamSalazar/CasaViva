from django.db import transaction
from rest_framework.exceptions import ValidationError
from rest_framework.exceptions import PermissionDenied

from apps.audit.services import audit_event
from apps.catalog.models import PropertyOffering
from apps.common.exceptions import Conflict
from apps.common.services import archive_entity, restore_entity
from apps.crm.models import Inquiry, LeadInterest, Sale, Visit
from .models import AvailabilityRecord, Listing, ListingMedia, PriceRecord, SlugRedirect
from .services import change_availability, change_price, publish_listing, unpublish_listing


def _same_price(current, payload):
    return bool(current) and all([
        current.price_type == payload["price_type"],
        current.amount_min == payload.get("amount_min"),
        current.amount_max == payload.get("amount_max"),
        current.currency == payload.get("currency", "MXN"),
    ])


@transaction.atomic
def create_property(validated, offering_serializer, actor, request=None):
    offering = offering_serializer.save(created_by=actor, updated_by=actor)
    listing_data = validated["listing"]
    listing = Listing.objects.create(offering=offering, created_by=actor, updated_by=actor, **listing_data)
    price = dict(validated["price"])
    change_price(offering, actor, request=request, **price)
    change_availability(offering, actor, request=request, **validated["availability"])
    _replace_media(listing, validated.get("media", []))
    audit_event(actor, "CREATE", listing, request=request)
    if validated.get("published"):
        listing = publish_listing(listing, actor, request=request)
    return listing


@transaction.atomic
def update_property(listing_id, validated, offering_serializer, actor, request=None):
    listing = Listing.all_objects.select_for_update().select_related("offering").get(pk=listing_id)
    offering = PropertyOffering.all_objects.select_for_update().get(pk=listing.offering_id)
    if listing.version != validated["listing_version"] or offering.version != validated["offering_version"]:
        raise Conflict()

    # Rebind the already validated data to the locked row.
    offering_serializer.instance = offering
    offering = offering_serializer.save(updated_by=actor, version=offering.version + 1)
    old_slug = listing.slug
    for field, value in validated["listing"].items():
        setattr(listing, field, value)
    listing.updated_by = actor
    listing.version += 1
    listing.save()
    if old_slug != listing.slug:
        SlugRedirect.objects.update_or_create(
            old_path=f"/propiedades/{old_slug}",
            defaults={"new_path": f"/propiedades/{listing.slug}"},
        )

    price = validated.get("price")
    if price is not None:
        current = PriceRecord.objects.select_for_update().filter(offering=offering, effective_to__isnull=True).first()
        if not _same_price(current, price):
            price = dict(price)
            change_price(offering, actor, request=request, **price)

    availability = validated.get("availability")
    if availability is not None:
        current = AvailabilityRecord.objects.select_for_update().filter(offering=offering, effective_to__isnull=True).first()
        if not current or current.status != availability["status"]:
            change_availability(offering, actor, request=request, **availability)

    if "media" in validated:
        _replace_media(listing, validated["media"])
    target_published = validated.get("published", listing.is_published)
    if target_published and not listing.is_published:
        listing = publish_listing(listing, actor, request=request)
    elif not target_published and listing.is_published:
        listing = unpublish_listing(listing, actor, request=request)
    audit_event(actor, "UPDATE", listing, request=request)
    return listing


def _replace_media(listing, media):
    ListingMedia.objects.filter(listing=listing).delete()
    ListingMedia.objects.bulk_create([
        ListingMedia(listing=listing, media=item["media"], role=item["role"], sort_order=item["sort_order"])
        for item in media
    ])


@transaction.atomic
def archive_property(listing, actor, request=None):
    if not actor.has_perm("listings.archive_listing"):
        raise PermissionDenied()
    listing = Listing.all_objects.select_for_update().select_related("offering").get(pk=listing.pk)
    offering = PropertyOffering.all_objects.select_for_update().get(pk=listing.offering_id)
    if listing.is_published:
        listing = unpublish_listing(listing, actor, request=request)
    archive_entity(listing, actor)
    archive_entity(offering, actor)
    return listing


@transaction.atomic
def restore_property(listing, actor):
    if not actor.has_perm("listings.restore_listing"):
        raise PermissionDenied()
    listing = Listing.all_objects.select_for_update().select_related("offering").get(pk=listing.pk)
    offering = PropertyOffering.all_objects.select_for_update().get(pk=listing.offering_id)
    restore_entity(offering, actor)
    restore_entity(listing, actor)
    return listing


@transaction.atomic
def set_property_featured(listing, actor, *, is_featured, listing_version, request=None):
    if not actor.has_perm("catalog.manage_offerings"):
        raise PermissionDenied()
    locked = Listing.all_objects.select_for_update().get(pk=listing.pk)
    if locked.version != listing_version:
        raise Conflict()
    old_value = locked.is_featured
    if old_value == is_featured:
        return locked
    locked.is_featured = is_featured
    locked.updated_by = actor
    locked.version += 1
    locked.save(update_fields=["is_featured", "updated_by", "version", "updated_at"])
    audit_event(actor, "UPDATE", locked, old_values={"is_featured": old_value}, new_values={"is_featured": is_featured}, request=request)
    return locked


@transaction.atomic
def set_property_publication(listing, actor, *, is_published, listing_version, request=None):
    locked = Listing.all_objects.select_for_update().select_related("offering").get(pk=listing.pk)
    if locked.version != listing_version:
        raise Conflict()
    if locked.is_published == is_published:
        return locked
    if is_published:
        return publish_listing(locked, actor, request=request)
    return unpublish_listing(locked, actor, request=request)


def property_dependencies(listing):
    offering = listing.offering
    return {
        "sales": Sale.objects.filter(listing=listing).count() + Sale.objects.filter(listing__isnull=True, offering=offering).count(),
        "visits": Visit.objects.filter(offering=offering).count(),
        "inquiries": Inquiry.objects.filter(listing=listing).count(),
        "interests": LeadInterest.objects.filter(offering=offering).count(),
        "analytics_events": listing.analytics_events.count() + offering.analytics_events.filter(listing__isnull=True).count(),
    }


@transaction.atomic
def hard_delete_property(listing, actor, *, confirmation, reason, request=None):
    if not actor.has_perm("listings.hard_delete_listing"):
        from rest_framework.exceptions import PermissionDenied
        raise PermissionDenied()
    listing = Listing.all_objects.select_for_update().select_related("offering").get(pk=listing.pk)
    offering = PropertyOffering.all_objects.select_for_update().get(pk=listing.offering_id)
    if listing.archived_at is None or offering.archived_at is None:
        raise ValidationError("Primero archiva la propiedad.")
    if confirmation != listing.title:
        raise ValidationError({"confirmation": f'Escribe exactamente "{listing.title}".'})
    dependencies = property_dependencies(listing)
    if any(dependencies[key] for key in ("sales", "visits", "inquiries", "interests")):
        raise ValidationError("Este registro tiene actividad comercial y sólo puede archivarse.")
    audit_event(
        actor, "HARD_DELETE", listing, entity_type="Property", old_values={
            "listing_id": str(listing.id), "offering_id": str(offering.id),
            "title": listing.title, "slug": listing.slug,
        }, request=request, reason=reason,
    )
    # Analytics foreign keys use SET_NULL and retain their snapshots.
    listing.analytics_events.filter(listing_public_key__isnull=True).update(
        listing_public_key=listing.id, listing_title_snapshot=listing.title,
    )
    ListingMedia.objects.filter(listing=listing).delete()
    listing.delete()
    PriceRecord.objects.filter(offering=offering).delete()
    AvailabilityRecord.objects.filter(offering=offering).delete()
    offering.delete()
