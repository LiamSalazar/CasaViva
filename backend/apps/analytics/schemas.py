from rest_framework.exceptions import ValidationError

EVENT_SCHEMAS = {
    "page_viewed": set(), "listing_viewed": set(), "development_viewed": set(),
    "gallery_opened": set(), "favorite_added": set(), "favorite_removed": set(),
    "contact_form_opened": set(), "contact_form_submitted": set(),
    "whatsapp_clicked": set(), "phone_clicked": set(), "lead_created": set(),
    "lead_status_changed": {"status"}, "visit_scheduled": set(), "visit_completed": set(),
    "sale_closed": set(), "filter_applied": {"filter"},
    "recommendation_started": set(), "recommendation_completed": set(),
    "recommendation_result_clicked": set(),
    "search_performed": set(),
}
ALLOWED_SEARCH_FIELDS = {
    "municipality_ids", "state_ids", "price_min", "price_max", "bedrooms_min",
    "property_type_codes", "amenity_slugs", "result_count",
}


def validate_event(name, version, properties):
    if name not in EVENT_SCHEMAS:
        raise ValidationError({"event_name": "Evento no reconocido."})
    if version != 1:
        raise ValidationError({"schema_version": "Versión de evento no compatible."})
    if not isinstance(properties, dict):
        raise ValidationError({"properties": "Debe ser un objeto."})
    if len(str(properties).encode()) > 16_384:
        raise ValidationError({"properties": "El evento excede el tamaño permitido."})
    required = EVENT_SCHEMAS[name]
    missing = required - properties.keys()
    if missing:
        raise ValidationError({"properties": f"Faltan campos: {', '.join(sorted(missing))}."})
    if name == "search_performed" and set(properties) - ALLOWED_SEARCH_FIELDS:
        raise ValidationError({"properties": "La búsqueda contiene campos no permitidos."})
