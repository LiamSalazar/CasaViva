import re
from decimal import Decimal
from django.db import transaction
from django.utils import timezone
from rest_framework.exceptions import PermissionDenied, ValidationError
from apps.audit.services import audit_event
from .models import ConsentRecord, Inquiry, Lead, LeadInterest, LeadStageHistory, Sale, Visit


def normalize_phone(value):
    if not value:
        return None
    digits = re.sub(r"\D", "", value)
    if len(digits) == 10:
        return f"+52{digits}"
    return f"+{digits}" if 10 <= len(digits) <= 15 else None


@transaction.atomic
def create_inquiry(*, first_name, last_name=None, email=None, phone=None, message=None,
                   listing=None, session_id=None, visitor_id=None, source="WEB",
                   privacy_notice_version=None, intent=Inquiry.Intent.INFORMATION,
                   subject=None):
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
    web_session = None
    if session_id:
        from apps.analytics.models import AnalyticsEvent, WebSession
        from apps.analytics.attribution import first_touch_session
        web_session = WebSession.objects.select_for_update().filter(pk=session_id).first()
        if web_session is None:
            raise ValidationError({"session_id": "La sesión de navegación no existe."})
        if visitor_id is None or web_session.visitor_id != visitor_id:
            raise ValidationError({"session_id": "La sesión no pertenece al visitante indicado."})
        if web_session.lead_id and web_session.lead_id != lead.id:
            raise ValidationError({"session_id": "La sesión ya está asociada a otro cliente."})
        if AnalyticsEvent.objects.filter(session=web_session, lead__isnull=False).exclude(lead=lead).exists():
            raise ValidationError({"session_id": "La sesión contiene actividad asociada a otro cliente."})
        if web_session.lead_id is None:
            web_session.lead = lead
            web_session.save(update_fields=["lead", "updated_at"])
        AnalyticsEvent.objects.filter(session=web_session, lead__isnull=True).update(lead=lead)
        visitor_has_conflicting_lead = WebSession.objects.filter(
            visitor_id=web_session.visitor_id, lead__isnull=False,
        ).exclude(lead=lead).exists()
        prior_session_ids = []
        if not visitor_has_conflicting_lead:
            candidate_ids = list(
                WebSession.objects.select_for_update().filter(
                    visitor_id=web_session.visitor_id,
                    lead__isnull=True,
                    started_at__lte=web_session.started_at,
                ).values_list("id", flat=True),
            )
            conflicting_ids = set(
                AnalyticsEvent.objects.filter(
                    session_id__in=candidate_ids, lead__isnull=False,
                ).values_list("session_id", flat=True),
            )
            prior_session_ids = [item for item in candidate_ids if item not in conflicting_ids]
        if prior_session_ids:
            WebSession.objects.filter(id__in=prior_session_ids).update(lead=lead)
            AnalyticsEvent.objects.filter(
                session_id__in=prior_session_ids,
                lead__isnull=True,
            ).update(lead=lead)
        first_session = first_touch_session(lead) or web_session
        attribution_source = first_session.utm_source or source
        if lead.first_source in (None, "", source):
            lead.first_source = attribution_source
        lead.last_source = web_session.utm_source or source
        lead.save(update_fields=["first_source", "last_source", "updated_at"])
    inquiry = Inquiry.objects.create(
        lead=lead, listing=listing, channel=Inquiry.Channel.WEB, intent=intent,
        subject=subject, message=message, session_id=web_session.id if web_session else None,
    )
    if privacy_notice_version:
        purpose = {
            Inquiry.Intent.INFORMATION: "PROPERTY_INQUIRY",
            Inquiry.Intent.VISIT_REQUEST: "VISIT_REQUEST",
            Inquiry.Intent.GENERAL_CONTACT: "GENERAL_CONTACT",
        }[intent]
        ConsentRecord.objects.create(
            lead=lead, visitor_id=web_session.visitor_id if web_session else None,
            privacy_notice_version=privacy_notice_version, purpose=purpose,
            granted=True, granted_at=timezone.now(), source="PUBLIC_WEB",
        )
    if listing:
        LeadInterest.objects.create(lead=lead, offering=listing.offering, interest_type=LeadInterest.Type.INQUIRED)
    return inquiry


@transaction.atomic
def create_visit(*, lead, offering, scheduled_at, actor, assigned_to=None, notes=None,
                 status=Visit.Status.SCHEDULED):
    if not actor.has_perm("crm.manage_visits"):
        raise PermissionDenied()
    if status not in Visit.Status.values:
        raise ValidationError({"status": "Selecciona un estado de visita válido."})
    visit = Visit.objects.create(
        lead=lead, offering=offering, scheduled_at=scheduled_at, status=status,
        assigned_to=assigned_to, notes=notes,
        completed_at=timezone.now() if status == Visit.Status.COMPLETED else None,
    )
    if status == Visit.Status.SCHEDULED and lead.status not in (Lead.Status.WON, Lead.Status.LOST, Lead.Status.VISIT_SCHEDULED, Lead.Status.NEGOTIATING):
        _set_lead_stage(lead, Lead.Status.VISIT_SCHEDULED, actor)
    audit_event(actor, "VISIT_SCHEDULED" if status == Visit.Status.SCHEDULED else "CREATE", visit)
    return visit


@transaction.atomic
def change_visit_status(visit, new_status, actor, request=None):
    if not actor.has_perm("crm.manage_visits"):
        raise PermissionDenied()
    if new_status not in Visit.Status.values:
        raise ValidationError({"status": "Selecciona un estado de visita válido."})
    locked = Visit.objects.select_for_update().select_related("lead").get(pk=visit.pk)
    old_status = locked.status
    if old_status == new_status:
        return locked
    transitions = {
        Visit.Status.SCHEDULED: {Visit.Status.COMPLETED, Visit.Status.CANCELLED, Visit.Status.NO_SHOW},
        Visit.Status.CANCELLED: {Visit.Status.SCHEDULED},
        Visit.Status.NO_SHOW: {Visit.Status.SCHEDULED},
        Visit.Status.COMPLETED: set(),
    }
    if new_status not in transitions[old_status]:
        raise ValidationError({"status": "La transición de visita no es válida."})
    locked.status = new_status
    locked.completed_at = timezone.now() if new_status == Visit.Status.COMPLETED else None
    locked.save(update_fields=["status", "completed_at", "updated_at"])
    if new_status == Visit.Status.SCHEDULED and locked.lead.status not in (Lead.Status.WON, Lead.Status.LOST, Lead.Status.VISIT_SCHEDULED, Lead.Status.NEGOTIATING):
        _set_lead_stage(locked.lead, Lead.Status.VISIT_SCHEDULED, actor)
    action = {
        Visit.Status.SCHEDULED: "VISIT_SCHEDULED",
        Visit.Status.COMPLETED: "VISIT_COMPLETED",
        Visit.Status.CANCELLED: "VISIT_CANCELLED",
        Visit.Status.NO_SHOW: "VISIT_NO_SHOW",
    }[new_status]
    audit_event(actor, action, locked, old_values={"status": old_status}, new_values={"status": new_status}, request=request)
    return locked


@transaction.atomic
def change_lead_stage(lead, stage, actor):
    if not actor.has_perm("crm.manage_leads"):
        raise PermissionDenied()
    if stage not in Lead.Status.values:
        raise ValidationError({"status": "Selecciona una etapa válida."})
    return _set_lead_stage(lead, stage, actor)


def _set_lead_stage(lead, stage, actor):
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
    if status not in Sale.Status.values:
        raise ValidationError({"status": "Selecciona un estado de venta válido."})
    sale = Sale.objects.create(lead=lead, offering=offering, listing=listing, sale_price=sale_price, commission_rate=rate, commission_amount=amount, closed_at=closed_at, status=status, created_by=actor)
    if status == Sale.Status.CLOSED:
        _set_lead_stage(lead, Lead.Status.WON, actor)
    audit_event(actor, "CREATE", sale)
    return sale


@transaction.atomic
def change_sale_status(sale, new_status, actor, request=None):
    if not actor.has_perm("crm.manage_sales"):
        raise PermissionDenied()
    if new_status not in Sale.Status.values:
        raise ValidationError({"status": "Selecciona un estado de venta válido."})
    locked = Sale.objects.select_for_update().select_related("lead").get(pk=sale.pk)
    old_status = locked.status
    if old_status == new_status:
        return locked
    locked.status = new_status
    locked.save(update_fields=["status", "updated_at"])
    if new_status == Sale.Status.CLOSED and locked.lead.status != Lead.Status.WON:
        _set_lead_stage(locked.lead, Lead.Status.WON, actor)
    elif new_status == Sale.Status.CANCELLED:
        other_closed = Sale.objects.filter(lead=locked.lead, status=Sale.Status.CLOSED).exclude(pk=locked.pk).exists()
        if not other_closed and locked.lead.status == Lead.Status.WON:
            _set_lead_stage(locked.lead, Lead.Status.NEGOTIATING, actor)
    audit_event(actor, "SALE_STATUS_CHANGED", locked, old_values={"status": old_status}, new_values={"status": new_status}, request=request)
    return locked
