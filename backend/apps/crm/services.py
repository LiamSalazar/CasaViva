import re
from decimal import Decimal
from django.db import transaction
from django.utils import timezone
from rest_framework.exceptions import PermissionDenied, ValidationError
from apps.audit.services import audit_event
from .models import ConsentRecord, Inquiry, Lead, LeadInterest, LeadStageHistory, Sale


def normalize_phone(value):
    if not value:
        return None
    digits = re.sub(r"\D", "", value)
    if len(digits) == 10:
        return f"+52{digits}"
    return f"+{digits}" if 10 <= len(digits) <= 15 else None


@transaction.atomic
def create_inquiry(*, first_name, last_name=None, email=None, phone=None, message=None, listing=None, session_id=None, source="WEB", privacy_notice_version=None):
    email = email.lower().strip() if email else None
    normalized = normalize_phone(phone)
    lead = Lead.all_objects.filter(email=email, archived_at__isnull=True).first() if email else None
    if lead is None and normalized:
        phone_candidate = Lead.all_objects.filter(phone_normalized=normalized, archived_at__isnull=True).first()
        # A matching phone with a different known email is ambiguous and is never auto-merged.
        if phone_candidate and (not email or not phone_candidate.email or phone_candidate.email == email):
            lead = phone_candidate
    if lead is None:
        lead = Lead.objects.create(first_name=first_name.strip(), last_name=last_name, email=email, phone_raw=phone, phone_normalized=normalized, first_source=source, last_source=source)
        LeadStageHistory.objects.create(lead=lead, stage=Lead.Status.NEW, started_at=timezone.now())
    else:
        lead.last_source = source
        if not lead.phone_raw and phone:
            lead.phone_raw, lead.phone_normalized = phone, normalized
        lead.save()
    inquiry = Inquiry.objects.create(lead=lead, listing=listing, channel=Inquiry.Channel.WEB, message=message, session_id=session_id)
    if privacy_notice_version:
        ConsentRecord.objects.create(
            lead=lead, privacy_notice_version=privacy_notice_version, purpose="PROPERTY_INQUIRY",
            granted=True, granted_at=timezone.now(), source=source,
        )
    if listing:
        LeadInterest.objects.create(lead=lead, offering=listing.offering, interest_type=LeadInterest.Type.INQUIRED)
    return inquiry


@transaction.atomic
def change_lead_stage(lead, stage, actor):
    if not actor.has_perm("crm.manage_leads"):
        raise PermissionDenied()
    if stage not in Lead.Status.values:
        raise ValidationError({"status": "Selecciona una etapa válida."})
    locked = Lead.all_objects.select_for_update().get(pk=lead.pk)
    now = timezone.now()
    current = LeadStageHistory.objects.select_for_update().filter(lead=locked, ended_at__isnull=True).first()
    if current:
        current.ended_at = now
        current.save(update_fields=["ended_at", "updated_at"])
    LeadStageHistory.objects.create(lead=locked, stage=stage, started_at=now, changed_by=actor)
    old = locked.status
    locked.status = stage
    locked.updated_by = actor
    locked.version += 1
    locked.save()
    audit_event(actor, "LEAD_STATUS_CHANGED", locked, old_values={"status": old}, new_values={"status": stage})
    return locked


@transaction.atomic
def create_sale(*, lead, offering, sale_price, closed_at, actor, listing=None, commission_rate=None, status=Sale.Status.CLOSED):
    if not actor.has_perm("crm.manage_sales"):
        raise PermissionDenied()
    rate = Decimal(commission_rate) if commission_rate is not None else offering.default_commission_rate
    amount = (Decimal(sale_price) * rate / Decimal(100)).quantize(Decimal("0.01")) if rate is not None else None
    sale = Sale.objects.create(lead=lead, offering=offering, listing=listing, sale_price=sale_price, commission_rate=rate, commission_amount=amount, closed_at=closed_at, created_by=actor)
    if status == Sale.Status.CLOSED:
        change_lead_stage(lead, Lead.Status.WON, actor)
    audit_event(actor, "CREATE", sale)
    return sale
