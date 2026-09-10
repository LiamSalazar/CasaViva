# Eventos analíticos

Todos usan `schema_version=1`, `occurred_at`, `visitor_id`, `session_id`, `page_path` opcional y `properties` validado con máximo de 16 KiB. Visitante y sesión existen sólo en `sessionStorage`; el servidor ignora IDs legacy al crear otra sesión. La sesión rota después de 30 minutos o cambios materiales de UTM. La solicitud en vuelo se comparte para evitar duplicados bajo React Strict Mode.

Al asociar una consulta, los eventos previos reciben el lead de forma idempotente y los posteriores lo heredan de `WebSession.lead`. BI usa first-touch: primera sesión conocida ordenada por inicio e identificador.

| Evento | Disparador | Requerido específico |
| --- | --- | --- |
| `page_viewed` | Cambio de página | — |
| `search_performed` | Envío de búsqueda | Sólo campos permitidos; todos opcionales |
| `filter_applied` | Aplicación de filtro | `filter` |
| `listing_viewed`, `development_viewed`, `gallery_opened` | Apertura de contenido | Relaciones opcionales |
| `favorite_added`, `favorite_removed` | Cambio de favorito | — |
| `recommendation_started`, `recommendation_completed`, `recommendation_result_clicked` | Recomendador determinista | — |
| `contact_form_opened`, `contact_form_submitted` | Contacto | — |
| `whatsapp_clicked`, `phone_clicked` | Acción de contacto | — |
| `lead_created` | Alta de cliente | — |
| `lead_status_changed` | Cambio de etapa | `status` |
| `visit_scheduled`, `visit_completed`, `sale_closed` | Operación CRM | — |

```json
{"event_name":"search_performed","schema_version":1,"occurred_at":"2026-08-19T18:00:00Z","visitor_id":"00000000-0000-0000-0000-000000000000","session_id":"00000000-0000-0000-0000-000000000000","page_path":"/propiedades","properties":{"price_max":1300000,"bedrooms_min":3,"property_type_codes":["house"],"amenity_slugs":["areas-verdes"],"result_count":4}}
```
