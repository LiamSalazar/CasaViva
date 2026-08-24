# CasaViva

CasaViva es una plataforma inmobiliaria modular con frontend editorial Next.js 16 y backend Django 6.1/DRF sobre PostgreSQL 18. La experiencia pública conserva el diseño original; los datos, la autenticación administrativa, el CRM, la auditoría, el tracking y BI provienen del backend.

## Ejecutar CasaViva localmente

Requisitos: Docker con Compose, Python 3.12+, Node.js 20+ y npm 10+.

```bash
cp .env.example .env
# Cambia TODOS los valores CHANGE_ME antes del primer arranque.
docker compose up -d postgres

python3 -m venv backend/.venv
source backend/.venv/bin/activate
# Windows (PowerShell): backend\.venv\Scripts\Activate.ps1
pip install -r backend/requirements/development.txt
```

Migra y aplica el hardening usando temporalmente `casaviva_migrator` y la misma contraseña local que configuraste en `.env`:

```bash
export DATABASE_URL='postgresql://casaviva_migrator:TU_PASSWORD_MIGRATOR@127.0.0.1:5432/casaviva'
python backend/manage.py migrate
python backend/manage.py harden_database_roles
unset DATABASE_URL

python backend/manage.py seed_system
python backend/manage.py seed_reference_catalog
python backend/manage.py bootstrap_founders
python backend/manage.py runserver 127.0.0.1:8000
```

`unset DATABASE_URL` hace que Django vuelva a usar el `DATABASE_URL` de `.env`, que debe apuntar a `casaviva_app`. `bootstrap_founders` solicita las cuentas administrativas; no hay correos, contraseñas ni secretos TOTP versionados.

### Acceso de administradores

Las cuentas Liam, Ana y Alfredo se crean al ejecutar `python backend/manage.py bootstrap_founders`; sus correos y contraseñas los define quien instala CasaViva. En el primer acceso, cada cuenta debe escanear el QR TOTP, confirmar un código y conservar sus códigos de recuperación.

Para consultar sólo nombre, correo, rol, estado y estado MFA:

```bash
python backend/manage.py list_admin_users
```

Para restablecer una contraseña sin exponerla en el historial de la terminal:

```bash
python backend/manage.py reset_admin_password correo@example.com
```

En otra terminal:

```bash
npm install
npm run dev
```

Abre el sitio en `http://localhost:3000` y la administración en `http://localhost:3000/administracion/acceso`. Para detener PostgreSQL usa `docker compose down`.

PostgreSQL persiste sus datos en un volumen Docker, no en un archivo dentro del repositorio. Puedes comprobarlo con:

```bash
docker compose ps
docker inspect "$(docker compose ps -q postgres)" \
  --format '{{range .Mounts}}{{println .Name "->" .Destination}}{{end}}'
```

`docker compose down` conserva el volumen. **`docker compose down -v` elimina la base local**; no lo uses si deseas conservar sus datos.

## Verificar el proyecto

```bash
./scripts/verify.sh
```

El script crea una PostgreSQL 18 de pruebas separada, ejecuta backend, frontend y E2E reales, y limpia sólo su infraestructura temporal. Nunca modifica la base normal de desarrollo.

## Arquitectura

```mermaid
flowchart TB
  U[Visitante] --> N[Next.js público]
  A[Equipo CasaViva] --> M[Administración CasaViva]
  N -->|/api/v1/public| D[Django 6.1 + DRF]
  M -->|sesión HttpOnly + CSRF + MFA| D
  D --> P[(PostgreSQL 18)]
  D --> F[(Almacenamiento de archivos)]
  P --> C[Catálogo e inventario]
  P --> R[CRM y ventas]
  P --> T[Tracking y auditoría]
  C --> B[BI operativo]
  R --> B
  T --> B
```

El diagrama detallado está en [docs/architecture.md](docs/architecture.md). El ER con atributos y relaciones está en [docs/erd.md](docs/erd.md), y el diccionario de datos en [docs/database-model.md](docs/database-model.md).

## Pruebas rápidas

```bash
cd backend
.venv/bin/pytest --cov=apps --cov-branch
cd ..
backend/.venv/bin/python backend/manage.py check --settings=config.settings.test
npm run lint
npm run typecheck
npm run build
```

Esta suite usa SQLite en memoria para retroalimentación rápida. No sustituye las pruebas de restricciones, concurrencia ni roles de PostgreSQL.

## Detalle de la verificación completa

```bash
./scripts/verify.sh
```

El script crea exclusivamente `casaviva_test` en el Compose de pruebas, comprueba el nombre antes de cualquier limpieza, migra una base PostgreSQL 18 vacía, ejecuta ambos seeds dos veces, endurece y prueba los roles, corre la suite completa sobre SQLite y PostgreSQL, valida OpenAPI y los checks de despliegue, compila Next.js y ejecuta Playwright contra Next + Django + PostgreSQL reales. Un `trap` elimina únicamente contenedores y volumen de pruebas al terminar; nunca ejecuta `down -v` sobre el Compose de desarrollo.

Las credenciales de esta infraestructura son constantes de prueba aisladas. Playwright recibe usuarios `@example.test` y un secreto TOTP temporal mediante variables del propio script; no existe bypass MFA y nada se habilita en producción.

`reset_demo_data` sólo funciona con `DEBUG=True`. Los seeds son idempotentes: crean faltantes y no reemplazan correcciones humanas.

## API y documentación

- Pública: `/api/v1/public/`
- Administrativa: `/api/v1/admin/`
- Autenticación: `/api/v1/auth/`
- OpenAPI en desarrollo: `/api/schema/` y `/api/schema/docs/`

Documentos: [arquitectura](docs/architecture.md), [modelo y diccionario](docs/database-model.md), [ER](docs/erd.md), [permisos](docs/permissions.md), [seguridad](docs/security.md), [eventos](docs/analytics-events.md), [BI](docs/bi.md), [DW futuro](docs/data-warehouse-roadmap.md), [preparación IA](docs/ai-data-readiness.md), [backups](docs/backup-recovery.md) y [despliegue](docs/deployment.md).

## Preparación para producción

La aplicación no obliga a elegir proveedor. Antes de desplegar: define `config.settings.production`, conecta PostgreSQL externo con SSL, configura `STORAGE_BACKEND=s3` y un bucket S3-compatible, sirve Next y `/api/` bajo HTTPS en el mismo sitio, ejecuta `migrate` con el migrator y después `harden_database_roles`, ejecuta `seed_system` y crea founders una sola vez. Sirve requests con `casaviva_app`, comprueba `/api/health/live/` y `/api/health/ready/`, configura backups externos y completa la [lista de producción](docs/production-checklist.md).

Next incorpora los hosts autorizados para imágenes durante el build. Con storage/CDN remoto compila el frontend así (el hostname no es secreto):

```bash
docker build -f docker/frontend.Dockerfile \
  --build-arg MEDIA_REMOTE_HOSTNAME=media.casaviva.mx \
  -t casaviva-frontend .
```

Los objetos públicos deben ser accesibles mediante el bucket/CDN configurado porque las URLs no llevan firma (`AWS_QUERYSTRING_AUTH=False`). Comienza con `SECURE_HSTS_SECONDS=0`; aumenta gradualmente sólo después de verificar HTTPS y todos los subdominios.
