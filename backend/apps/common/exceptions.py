from rest_framework.views import exception_handler
from rest_framework.exceptions import APIException


class Conflict(APIException):
    status_code = 409
    default_detail = "Este registro fue modificado mientras lo estabas editando. Actualiza la información antes de guardar tus cambios."
    default_code = "CONFLICT"


def api_exception_handler(exc, context):
    response = exception_handler(exc, context)
    if response is None:
        return response
    fields = response.data if isinstance(response.data, dict) else {}
    detail = fields.pop("detail", None) if isinstance(fields, dict) else None
    message = str(detail or "No fue posible completar la solicitud.")
    response.data = {"error": {"code": getattr(exc, "default_code", "API_ERROR").upper(), "message": message, "fields": fields}}
    request = context.get("request")
    if request and getattr(request, "request_id", None):
        response["X-Request-ID"] = request.request_id
    return response
