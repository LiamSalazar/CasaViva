# Runbook ARCO

El receptor es `privacy_email` de la configuración; producción falla si está vacío. Registrar fecha, identidad declarada, medio de respuesta, derecho y alcance. Solicitar sólo evidencia razonable y proporcional de identidad. No responder con datos antes de verificarla.

1. Ejecutar `python manage.py privacy_subject_lookup --email ...` o `--phone ...` y guardar el reporte en el expediente restringido.
2. Revisar Lead, Inquiry, Visit, Sale, ConsentRecord y tracking vinculado; confirmar homónimos y dependencias.
3. Para acceso, entregar copia segura y comprensible. Para rectificación, conservar trazabilidad. Para cancelación, determinar primero bloqueos legales/operativos; para oposición o revocación, detener tratamientos dependientes del consentimiento.
4. `privacy_subject_anonymize` es dry-run por defecto. Revisar el reporte y sólo entonces repetir con `--confirm`; ConsentRecord, AuditEvent, Sale y relaciones PROTECT se preservan y se documentan.
5. Registrar decisión, fundamento, alcance, responsable, fecha y respuesta. Aplicar los plazos legales vigentes al momento de la solicitud; no se codifican plazos fijos porque deben validarse con asesoría aplicable.
