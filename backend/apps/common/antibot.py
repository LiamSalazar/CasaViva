import json
from urllib.parse import urlencode
from urllib.request import Request, urlopen
from django.conf import settings
from rest_framework.exceptions import ValidationError


def verify_antibot(token, remote_ip=None):
    if not settings.ANTIBOT_ENABLED:
        return
    if settings.ANTIBOT_PROVIDER != "turnstile" or not settings.TURNSTILE_SECRET_KEY:
        raise ValidationError({"antibot_token": "La protección antibot no está configurada."})
    if not token:
        raise ValidationError({"antibot_token": "Completa la verificación antibot."})
    if settings.TURNSTILE_TEST_TOKEN:
        if token == settings.TURNSTILE_TEST_TOKEN:
            return
        raise ValidationError({"antibot_token": "No fue posible validar la verificación antibot."})
    payload = {"secret": settings.TURNSTILE_SECRET_KEY, "response": token}
    if remote_ip:
        payload["remoteip"] = remote_ip
    request = Request("https://challenges.cloudflare.com/turnstile/v0/siteverify", data=urlencode(payload).encode(), method="POST")
    try:
        with urlopen(request, timeout=5) as response:  # noqa: S310 - fixed provider endpoint
            valid = bool(json.load(response).get("success"))
    except Exception:
        valid = False
    if not valid:
        raise ValidationError({"antibot_token": "No fue posible validar la verificación antibot."})
