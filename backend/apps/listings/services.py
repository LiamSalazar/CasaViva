from decimal import Decimal, InvalidOperation
from django.db import transaction
from django.db.models import Q
from django.utils import timezone
from django.utils.dateparse import parse_datetime
from rest_framework.exceptions import PermissionDenied, ValidationError
from apps.audit.services import audit_event
from .models import AvailabilityRecord, Listing, PriceRecord, SlugRedirect
from apps.crm.models import Inquiry, LeadInterest, Sale, Visit


def _decimal(value, field):
    if value in (None, ""):
        return None
    try:
        return Decimal(str(value))
    except (InvalidOperation, TypeError, ValueError):
        raise ValidationError({field: "Captura un número válido."})


def _effective_datetime(value, field="effective_from"):
    if value in (None, ""):
        return timezone.now()
    if isinstance(value, str):
        value = parse_datetime(value)
    if value is None:
        raise ValidationError({field: "Captura una fecha y hora válidas."})
    if timezone.is_naive(value):
        value = timezone.make_aware(value, timezone.get_current_timezone())
    return value


@transaction.atomic
def change_price(offering, actor, *, price_type, amount_min=None, amount_max=None, currency=PriceRecord.Currency.MXN, effective_from=None, source_record=None, observations=None, promotion_text=None, promotion_valid_from=None, promotion_valid_until=None, promotion_conditions=None, request=None):
    if not actor.has_perm("catalog.manage_offerings"):
        raise PermissionDenied()
    locked = type(offering).all_objects.select_for_update().get(pk=offering.pk)
    if price_type not in PriceRecord.Type.values:
        raise ValidationError({"price_type": "Selecciona un tipo de precio válido."})
    if currency not in PriceRecord.Currency.values:
        raise ValidationError({"currency": "CasaViva registra precios en MXN."})
    amount_min = _decimal(amount_min, "amount_min")
    amount_max = _decimal(amount_max, "amount_max")
    if price_type == PriceRecord.Type.ON_REQUEST and (amount_min is not None or amount_max is not None):
        raise ValidationError({"amount_min": "Precio a consultar no admite importes."})
    if price_type != PriceRecord.Type.ON_REQUEST and amount_min is None:
        raise ValidationError({"amount_min": "Captura un precio o selecciona Precio a consultar."})
    if price_type == PriceRecord.Type.RANGE and amount_max is None:
        raise ValidationError({"amount_max": "Captura el precio máximo del rango."})
    if amount_min is not None and amount_min < 0:
        raise ValidationError({"amount_min": "El precio no puede ser negativo."})
    if amount_max is not None and amount_max < 0:
        raise ValidationError({"amount_max": "El precio no puede ser negativo."})
    if amount_min is not None and amount_max is not None and amount_max < amount_min:
        raise ValidationError({"amount_max": "El precio máximo no puede ser menor que el mínimo."})
    if promotion_valid_from and promotion_valid_until and promotion_valid_until <= promotion_valid_from:
        raise ValidationError({"promotion_valid_until": "La vigencia final debe ser posterior a la inicial."})
    if promotion_text and (promotion_valid_from or promotion_valid_until) and not promotion_conditions:
        raise ValidationError({"promotion_conditions": "Captura las condiciones aplicables de la promoción."})
    now = _effective_datetime(effective_from)
    current = PriceRecord.objects.select_for_update().filter(offering=locked, effective_to__isnull=True).first()
    if current:
        if now <= current.effective_from:
            raise ValidationError({"effective_from": "La nueva fecha debe ser posterior al precio vigente."})
        current.effective_to = now
        current.save(update_fields=["effective_to", "updated_at"])
    record = PriceRecord.objects.create(offering=locked, price_type=price_type, amount_min=amount_min, amount_max=amount_max, currency=currency, effective_from=now, source_record=source_record, observations=observations, promotion_text=promotion_text, promotion_valid_from=promotion_valid_from, promotion_valid_until=promotion_valid_until, promotion_conditions=promotion_conditions, created_by=actor)
    audit_event(actor, "PRICE_CHANGE", locked, old_values={"price": str(current.amount_min) if current else None, "currency": current.currency if current else None}, new_values={"price": str(amount_min) if amount_min is not None else None, "type": price_type, "currency": currency}, request=request)
    return record


@transaction.atomic
def change_availability(offering, actor, *, status, effective_from=None, notes=None, request=None):
    if not actor.has_perm("catalog.manage_offerings"):
        raise PermissionDenied()
    if status not in AvailabilityRecord.Status.values:
        raise ValidationError({"status": "Selecciona una disponibilidad válida."})
    locked = type(offering).all_objects.select_for_update().get(pk=offering.pk)
    now = _effective_datetime(effective_from)
    current = AvailabilityRecord.objects.select_for_update().filter(offering=locked, effective_to__isnull=True).first()
    if current:
        if now <= current.effective_from:
            raise ValidationError({"effective_from": "La nueva fecha debe ser posterior a la disponibilidad vigente."})
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
    if not offering.promotion_authorized:
        errors["promotion_authorized"] = "Confirma que el proveedor autorizó la promoción antes de publicar."
    if not offering.information_verified_at:
        errors["information_verified_at"] = "Registra cuándo se verificó la información comercial."
    if offering.source_type == offering.SourceType.DEVELOPER and not offering.development_model_id:
        errors["provider"] = "Selecciona la desarrolladora/proveedor de la oferta."
    if offering.source_type == offering.SourceType.PRIVATE and offering.development_model_id:
        errors["provider"] = "Una oferta particular no puede atribuirse automáticamente a una desarrolladora."
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
    if Sale.objects.filter(Q(listing=listing) | Q(offering=listing.offering)).exists():
        raise ValidationError("Este registro forma parte del historial de una venta y no puede eliminarse definitivamente. Puedes archivarlo.")
    has_activity = (
        Visit.objects.filter(offering=listing.offering).exists()
        or Inquiry.objects.filter(listing=listing).exists()
        or LeadInterest.objects.filter(offering=listing.offering).exists()
    )
    if has_activity:
        raise ValidationError("Este registro tiene actividad comercial y sólo puede archivarse.")
    audit_event(actor, "HARD_DELETE", listing, old_values={"title": listing.title, "slug": listing.slug, "offering_id": str(listing.offering_id)}, request=request, reason=reason)
    listing.delete()
