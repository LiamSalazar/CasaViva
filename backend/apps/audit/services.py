import hashlib
import json
from django.forms.models import model_to_dict
from .models import AuditEvent


def _safe(values):
    if values is None:
        return None
    hidden = {"password", "token", "secret", "code", "session"}
    cleaned = {str(k): ("[REDACTADO]" if any(word in str(k).lower() for word in hidden) else v) for k, v in values.items()}
    return json.loads(json.dumps(cleaned, default=str))


def snapshot(entity):
    try:
        return {k: str(v) if hasattr(v, "isoformat") else v for k, v in model_to_dict(entity).items() if "password" not in k}
    except Exception:
        return None


def audit_event(actor, action, entity=None, *, entity_type=None, old_values=None, new_values=None, request=None, success=True, reason=None):
    ip_hash = None
    user_agent = None
    request_id = None
    if request:
        request_id = getattr(request, "request_id", None)
        ip = request.META.get("REMOTE_ADDR", "")
        ip_hash = hashlib.sha256(ip.encode()).hexdigest() if ip else None
        user_agent = request.headers.get("User-Agent", "")[:300]
    return AuditEvent.objects.create(
        actor_user=actor if getattr(actor, "is_authenticated", False) else None,
        action=action,
        entity_type=entity_type or (entity.__class__.__name__ if entity is not None else "System"),
        entity_id=str(getattr(entity, "pk", "") or ""),
        old_values=_safe(old_values),
        new_values=_safe(new_values if new_values is not None else (snapshot(entity) if entity is not None else None)),
        request_id=request_id,
        ip_hash=ip_hash,
        user_agent=user_agent,
        success=success,
        reason=reason,
    )
