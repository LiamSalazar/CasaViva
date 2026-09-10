# Implementación de privacidad

Los formularios muestran el aviso simplificado antes del envío cuando domicilio y correo están configurados, enlazan el aviso integral y registran un acuse `PRIVACY_NOTICE_ACKNOWLEDGEMENT`. Una solicitud de inmueble exige además autorización independiente `LEAD_TRANSFER`; no existe marketing opt-in visible.

Cada registro apunta a la versión publicada exacta. La analítica es first-party y de sesión: ambos UUID viven en `sessionStorage`; la preferencia mínima `limited` puede persistir localmente para suprimir page views, búsquedas y filtros. No hay fingerprinting ni trackers externos.

Los documentos pasan DRAFT → PUBLISHED → RETIRED. Publicar requiere permiso, MFA reciente, elimina placeholders, calcula SHA-256 normalizado, retira al activo anterior y audita. Un publicado es inmutable y no tiene DELETE por API.
