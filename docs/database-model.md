# Modelo y diccionario de datos

Convenciones: entidades de negocio usan UUID; timestamps son `timestamptz` en PostgreSQL; dinero y m² son `numeric`; `NULL` significa desconocido; `BusinessModel` añade auditoría de creación/cambio, `version` y archivo lógico.

## Cuentas y trazabilidad

| Tabla | Campo | Tipo | Nulo | Relación / propósito |
| --- | --- | --- | --- | --- |
| `accounts_user` | `id` | UUID | No | PK no secuencial. |
| | `email` | varchar | No | Identificador único de acceso, normalizado lowercase. |
| | `first_name`, `last_name` | varchar | No | Nombre visible; apellido puede estar vacío. |
| | `is_active`, `is_staff`, `is_superuser` | boolean | No | Estado y privilegio técnico. |
| | `authz_version` | integer | No | Invalida sesiones al cambiar acceso. |
| | `last_password_change_at` | timestamptz | No | Control de seguridad. |
| `accounts_recoverycode` | `user_id` | UUID | No | FK CASCADE a usuario. |
| | `code_hash`, `used_at` | varchar(256), timestamptz | Sí sólo uso | Hash adaptativo de Django y consumo único. |
| `audit_auditevent` | `actor_user_id` | UUID | Sí | SET NULL; actor puede ser sistema. |
| | `action`, `entity_type`, `entity_id` | varchar | No | Acción y objeto histórico. |
| | `old_values`, `new_values` | JSONB | Sí | Snapshots sanitizados. |
| | `request_id`, `ip_hash`, `success`, `reason` | varios | Sí según campo | Correlación, resultado y motivo; evento inmutable. |

## Geografía y fuentes

| Tabla | Campos principales | Tipo / nulos | Relación / propósito |
| --- | --- | --- | --- |
| `geo_state` | `name`, `code`, `is_active` | varchar, no nulos | Catálogo de estados. |
| `geo_municipality` | `state_id`, `name`, `is_active`, `is_featured` | UUID/varchar/boolean | PROTECT; único por estado; catálogo geográfico estructural. |
| `geo_locality` | `municipality_id`, `name` | UUID/varchar | Nivel opcional dependiente. |
| `geo_neighborhood` | `municipality_id`, `locality_id`, `name`, `postal_code` | localidad nullable | Colonia/barrio; único por municipio. |
| `common_sourcerecord` | `source_type`, `source_name`, `source_url`, `observed_at`, `notes`, `created_by_id` | URL/notas/actor nullable | Procedencia editable de información y precios. |

## Catálogo inmobiliario

| Tabla | Campos principales | Tipo / nulos | Relación / propósito |
| --- | --- | --- | --- |
| `catalog_developer` | `name`, `legal_name?`, `slug`, `website?`, `logo_media_id?`, `is_active` | UUID/varchar | Desarrolladora genérica; slug único. |
| `catalog_development` | `developer_id`, `name`, `slug`, FKs geo, dirección/coordenadas/descripciones opcionales, `is_active`, `is_published`, `is_featured` | UUID/text/decimal | PROTECT a desarrolladora y geo; ubicación jerárquica. |
| `catalog_housingmodel` | `developer_id`, `name`, `internal_code?`, `slug`, `base_description?`, `is_active` | UUID/varchar/text | Identidad comercial; el nombre no es único. |
| `catalog_developmentmodel` | `development_id`, `housing_model_id`, `display_name_override?`, `is_active` | UUID/varchar | Puente M:N; pareja activa única y desarrolladora compatible. |
| `catalog_propertytype` | `code`, `name`, `is_active`, `sort_order` | UUID/varchar/integer | Catálogo editable. |
| `catalog_propertyoffering` | `source_type`, `condition?`, `development_model_id?`, `variant_name?`, `property_type_id` | UUID/varchar | Oferta central. Origen y condición (`NEW`/`USED`) son independientes; DEVELOPER exige relación y PRIVATE la prohíbe. |
| | FKs geo, dirección, CP, lat/lon | nullable | Ubicación propia; puede heredarse del desarrollo. |
| | recámaras, baños, estacionamiento, niveles | numeric nullable | Desconocido permanece NULL. |
| | áreas min/max y `*_basis` | numeric/varchar nullable | EXACT, UP_TO, FROM, RANGE, UNKNOWN. |
| | referencia/notas/comisión | nullable | Sólo administración; comisión numeric, no pública. |
| `catalog_amenity` | `name`, `slug`, `category`, `is_active`, `sort_order` | no nulos | Catálogo de amenidades. |
| `catalog_developmentamenity`, `catalog_offeringamenity` | dos FKs | no nulos | Puentes únicos a Amenity; `PropertyOffering.amenities` es M:N explícita mediante el segundo puente. |
| `catalog_featuredefinition` | `code`, `label`, `category`, `data_type`, `unit?`, flags, orden | varios | Definición dinámica acotada. |
| `catalog_featurechoice` | `definition_id`, `value`, `label`, `sort_order` | no nulos | Opción para CHOICE. |
| `catalog_offeringfeaturevalue` | `offering_id`, `definition_id`, un valor tipado | sólo uno no nulo | Valor dinámico; pareja única. |

Todas las entidades editables anteriores incluyen `version` para optimistic locking y campos de archivo cuando heredan `BusinessModel`.

## Publicación, precio y media

| Tabla | Campos principales | Tipo / nulos | Relación / propósito |
| --- | --- | --- | --- |
| `listings_pricerecord` | `offering_id`, `price_type`, `amount_min?`, `amount_max?`, `currency`, `effective_from`, `effective_to?`, `source_record_id?`, `observations?` | numeric/timestamptz | Historial; índice único parcial para un vigente. ON_REQUEST no guarda monto y `currency` sólo admite MXN en esta fase. |
| `listings_availabilityrecord` | `offering_id`, `status`, fechas, `changed_by_id?`, `notes?` | varios | AVAILABLE, TEMPORARILY_UNAVAILABLE, RESERVED, SOLD; un vigente. |
| `listings_listing` | `offering_id`, `title`, `slug`, descripciones, flags, fechas, SEO opcional | UUID/varchar/text | OneToOne a offering; publicación independiente y slug único. |
| `listings_slugredirect` | `old_path`, `new_path`, `created_at` | varchar | Preserva URLs mediante 301. |
| `media_library_mediaasset` | `storage_key`, tipo, nombre, MIME, bytes, dimensiones, SHA-256, alt, actor | metadata | No contiene el binario. |
| `catalog_developmentmedia`, `catalog_offeringmedia`, `listings_listingmedia` | entidad, `media_id`, `role`, `sort_order` | FKs/varchar | HERO, GALLERY, FLOORPLAN, DOCUMENT. |

## CRM, privacidad y ventas

| Tabla | Campos principales | Tipo / nulos | Relación / propósito |
| --- | --- | --- | --- |
| `crm_lead` | nombre, email?, teléfono raw/normalizado?, `status`, owner?, fuentes? | varios | Cliente potencial archivables; versión optimista. |
| `crm_leadstagehistory` | `lead_id`, `stage`, `started_at`, `ended_at?`, `changed_by_id?` | FK/tiempo | Un tramo vigente; base del embudo y tiempos. |
| `crm_inquiry` | `lead_id`, `listing_id?`, `channel`, `message?`, `session_id?`, `status`, `assigned_to_id?` | varios | Consulta; listing SET NULL conserva CRM. |
| `crm_leadinterest` | lead, offering, tipo, fecha | FKs | VIEWED, FAVORITED, INQUIRED, VISITED. |
| `crm_visit` | lead, offering, agenda, estado, cierre?, responsable?, notas? | varios | Actividad comercial. |
| `crm_sale` | lead, offering, listing?, precio, comisión?, cierre, estado, actor | numeric/FKs | PROTECT sobre historia de venta. |
| `crm_privacynoticeversion` | versión, publicación, hash, activo | varios | Versión del aviso aceptado. |
| `crm_consentrecord` | lead?, visitor?, aviso, propósito, granted, fecha, fuente | varios | Evidencia de consentimiento. |

## Tracking, marketing y contenido

| Tabla | Campos principales | Tipo / nulos | Relación / propósito |
| --- | --- | --- | --- |
| `analytics_anonymousvisitor` | UUID, primera/última vista | no nulos | Identidad first-party sin cuenta. |
| `analytics_websession` | visitante, lead?, tiempos, UTM opcionales, referrer?, landing, device?, consentimiento | varios | Sesión atribuible. |
| `analytics_analyticsevent` | tiempos, nombre, versión, visitante/sesión, relaciones nullable, path?, `properties`, snapshots | JSONB/FKs | Evento controlado; listing SET NULL conserva snapshots. |
| `marketing_marketingcampaign` | nombre, UTM campaign, canal, fechas, activo, notas? | varios | Campaña administrable. |
| `marketing_marketingspend` | campaña, fecha, amount, currency | numeric | Gasto manual no negativo. |
| `content_homecontent` | key, textos, media editorial? | texto/FK | Contenido editable del home. |
| `content_guide` | slug, título, extracto, contenido, categoría, media?, flags, publicación? | texto/FK | Guías públicas administrables. |
| `content_locationcontent` | `municipality_id`, `slug`, descripción, media?, destacado, latitud?, longitud? | UUID/text/decimal | Contenido editorial 1:1 de una ubicación; no contamina el catálogo geográfico. |

## Restricciones e índices relevantes

- Únicos parciales: precio, disponibilidad y etapa de lead vigentes; pareja DevelopmentModel activa.
- Checks: source type, condición controlada por choices, coordenadas, rangos min/max (incluidas recámaras, estacionamientos y niveles), montos/medidas/comisión no negativos, comisión hasta 100, moneda MXN, formas de precio, periodos temporales y estado de venta controlado.
- B-tree: slugs, estados activos/publicados, geo, relaciones de offering, fecha/nombre de eventos, sesiones y relaciones analíticas.
- `PROTECT` conserva ventas y relaciones de negocio; `SET_NULL` conserva hechos analíticos/consultas; `CASCADE` sólo elimina puentes o valores dependientes sin identidad histórica propia.
