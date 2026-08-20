# Permisos

Los grupos iniciales son `Owner` y `Founder Admin`. Los endpoints siempre vuelven a comprobar permisos.

| Acción | Liam | Ana | Alfredo |
| --- | --- | --- | --- |
| Catálogo, desarrolladoras, desarrollos y modelos | Sí | Sí | Sí |
| Propiedades, publicación, archivo y restauración | Sí | Sí | Sí |
| Eliminación definitiva válida | Sí | Sí | Sí |
| Multimedia y contenido | Sí | Sí | Sí |
| Leads, consultas, visitas y ventas | Sí | Sí | Sí |
| Marketing, BI y DSS | Sí | Sí | Sí |
| Auditoría de negocio | Sí | Sí | Sí |
| Crear/desactivar usuarios administrativos | Sí | No | No |
| Roles y permisos | Sí | No | No |
| Crear superusuarios o modificar a Liam | Sí, con salvaguardas | No | No |
| Django Admin técnico | Sólo si está habilitado | No | No |

Todo cambio de acceso incrementa `authz_version`, elimina sesiones anteriores y deja auditoría. Founder Admin no contiene permisos `accounts.manage_*`.
