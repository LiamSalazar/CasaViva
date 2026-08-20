from django.db import transaction
from django.utils import timezone
from rest_framework.exceptions import PermissionDenied, ValidationError
from apps.audit.services import audit_event
from .models import AvailabilityRecord, Listing, PriceRecord, SlugRedirect
from apps.crm.models import Sale


@transaction.atomic
def change_price(offering, actor, *, price_type, amount_min=None, amount_max=None, effective_from=None, source_record=None, observations=None, request=None):
    if not actor.has_perm("catalog.manage_offerings"):
        raise PermissionDenied()
    locked = type(offering).all_objects.select_for_update().get(pk=offering.pk)
    if price_type != PriceRecord.Type.ON_REQUEST and amount_min is None:
        raise ValidationError({"amount_min": "Captura un precio o selecciona Precio a consultar."})
    if amount_min is not None and amount_min < 0:
        raise ValidationError({"amount_min": "El precio no puede ser negativo."})
    now = effective_from or timezone.now()
    current = PriceRecord.objects.select_for_update().filter(offering=locked, effective_to__isnull=True).first()
    if current:
        current.effective_to = now
        current.save(update_fields=["effective_to", "updated_at"])
    record = PriceRecord.objects.create(offering=locked, price_type=price_type, amount_min=amount_min, amount_max=amount_max, effective_from=now, source_record=source_record, observations=observations, created_by=actor)
    audit_event(actor, "PRICE_CHANGE", locked, old_values={"price": str(current.amount_min) if current else None}, new_values={"price": str(amount_min) if amount_min is not None else None, "type": price_type}, request=request)
    return record


@transaction.atomic
def change_availability(offering, actor, *, status, effective_from=None, notes=None, request=None):
    locked = type(offering).all_objects.select_for_update().get(pk=offering.pk)
    now = effective_from or timezone.now()
    current = AvailabilityRecord.objects.select_for_update().filter(offering=locked, effective_to__isnull=True).first()
    if current:
        current.effective_to = now
        current.save(update_fields=["effective_to", "updated_at"])
    record = AvailabilityRecord.objects.create(offering=locked, status=status, effective_from=now, changed_by=actor, notes=notes)
    audit_event(actor, "AVAILABILITY_CHANGE", locked, old_values={"status": current.status if current else None}, new_values={"status": status}, request=request)
    return record


def validate_publishable(listing):
    offering = listing.offering
    location = offering.effective_location()
    errors = {}
    if listing.archived_at or offering.archived_at:
        errors["archived"] = "Una propiedad archivada no puede publicarse."
    if not listing.title.strip():
        errors["title"] = "El título es obligatorio."
    if not offering.property_type_id:
        errors["property_type"] = "El tipo de propiedad es obligatorio."
    if not location["state"] or not location["municipality"]:
        errors["location"] = "Selecciona estado y municipio."
    if not PriceRecord.objects.filter(offering=offering, effective_to__isnull=True).exists():
        errors["price"] = "Registra un precio o selecciona Precio a consultar."
    if errors:
        raise ValidationError(errors)


@transaction.atomic
def publish_listing(listing, actor, request=None):
    if not actor.has_perm("listings.publish_listing"):
        raise PermissionDenied()
    listing = Listing.all_objects.select_for_update().select_related("offering").get(pk=listing.pk)
    validate_publishable(listing)
    listing.is_published = True
    listing.published_at = listing.published_at or timezone.now()
    listing.unpublished_at = None
    listing.updated_by = actor
    listing.version += 1
    listing.save()
    audit_event(actor, "PUBLISH", listing, request=request)
    return listing


@transaction.atomic
def unpublish_listing(listing, actor, request=None):
    if not actor.has_perm("listings.unpublish_listing"):
        raise PermissionDenied()
    listing = Listing.all_objects.select_for_update().get(pk=listing.pk)
    listing.is_published = False
    listing.unpublished_at = timezone.now()
    listing.updated_by = actor
    listing.version += 1
    listing.save()
    audit_event(actor, "UNPUBLISH", listing, request=request)
    return listing


@transaction.atomic
def change_slug(listing, new_slug, actor):
    if listing.slug == new_slug:
        return listing
    SlugRedirect.objects.update_or_create(old_path=f"/propiedades/{listing.slug}", defaults={"new_path": f"/propiedades/{new_slug}"})
    listing.slug = new_slug
    listing.updated_by = actor
    listing.version += 1
    listing.save()
    return listing


@transaction.atomic
def hard_delete_listing(listing, actor, *, confirmation, reason, request=None):
    if not actor.has_perm("listings.hard_delete_listing"):
        raise PermissionDenied()
    listing = Listing.all_objects.select_for_update().get(pk=listing.pk)
    if listing.archived_at is None:
        raise ValidationError("Primero archiva la propiedad.")
    if confirmation != listing.title:
        raise ValidationError({"confirmation": f'Escribe exactamente "{listing.title}".'})
    if Sale.objects.filter(listing=listing).exists() or Sale.objects.filter(offering=listing.offering).exists():
        raise ValidationError("Este registro forma parte del historial de una venta y no puede eliminarse definitivamente. Puedes archivarlo.")
    audit_event(actor, "HARD_DELETE", listing, old_values={"title": listing.title, "slug": listing.slug, "offering_id": str(listing.offering_id)}, request=request, reason=reason)
    listing.delete()
