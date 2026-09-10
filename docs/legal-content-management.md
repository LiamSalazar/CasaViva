# Gestión de contenido legal

Administración expone `privacy-notices` y `terms-of-use`: listar historial, crear/editar borrador, previsualizar con su cuerpo y publicar mediante la acción `publish`. Publicar exige permisos `crm.publish_privacy_notice` o `crm.publish_terms_of_use` y MFA de menos de 15 minutos. No hay DELETE. Las versiones históricas y consentimientos permanecen.

`seed_system` crea borradores base con placeholders y nunca los publica. Complete domicilio, correo de privacidad, contacto/quejas y teléfono, cree la versión definitiva y publique. El check de producción impide placeholders o ausencia de documentos activos.
