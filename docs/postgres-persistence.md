# PostgreSQL 18: inicialización y persistencia

CasaViva fija `PGDATA=/var/lib/postgresql/18/docker` y monta su padre `/var/lib/postgresql`. En Pilot ese padre corresponde al EBS cifrado montado en `/opt/casaviva/postgres`; no depende del directorio por defecto de la imagen.

El primer arranque recibe `POSTGRES_USER=postgres`, `POSTGRES_DB=casaviva` y `POSTGRES_PASSWORD` desde `POSTGRES_SUPERUSER_PASSWORD` de Parameter Store. No se usa `trust`. `init-roles.sh` sólo corre al crear un clúster vacío y exige las cuatro contraseñas técnicas.

Ejecute `./scripts/test-postgres-persistence.sh`. La prueba crea un clúster PostgreSQL 18 y un dato, verifica reinicio, `compose down/up` y eliminación/recreación del contenedor conservando el mismo volumen. Sólo elimina su proyecto y volumen de prueba al terminar.

En AWS, el EBS gp3 de datos tiene `prevent_destroy`, etiqueta stateful y montaje por UUID. User-data formatea únicamente si `blkid` confirma que el dispositivo no tiene filesystem. Para reanexarlo, detenga PostgreSQL, adjunte el volumen a una instancia en la misma AZ, confirme su ID/UUID, móntelo en `/opt/casaviva/postgres` y despliegue; nunca ejecute `mkfs` en un volumen con filesystem.
