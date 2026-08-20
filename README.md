# CasaViva

CasaViva es una plataforma inmobiliaria modular con frontend editorial Next.js 16 y backend Django 6.1/DRF sobre PostgreSQL 18. La experiencia pública conserva el diseño original; los datos, la autenticación administrativa, el CRM, la auditoría, el tracking y BI provienen del backend.

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

## Puesta en marcha

Requisitos: Node.js 20+, npm 10+, Python 3.12+ y Docker Compose.

```bash
cp .env.example .env
# Sustituye todos los valores CHANGE_ME.
docker compose up -d postgres

python3 -m venv backend/.venv
backend/.venv/bin/pip install -r backend/requirements/development.txt

# Para migrar usa temporalmente casaviva_migrator.
export DATABASE_URL='postgresql://casaviva_migrator:TU_PASSWORD@127.0.0.1:5432/casaviva'
backend/.venv/bin/python backend/manage.py migrate
backend/.venv/bin/python backend/manage.py seed_system
backend/.venv/bin/python backend/manage.py seed_reference_catalog
backend/.venv/bin/python backend/manage.py bootstrap_founders

# Para servir, cambia DATABASE_URL a casaviva_app.
backend/.venv/bin/python backend/manage.py runserver
```

En otra terminal:

```bash
npm install
npm run dev
```

Abre `http://localhost:3000`. La administración está en `http://localhost:3000/administracion/acceso`. No hay credenciales versionadas: `bootstrap_founders` solicita los datos de Liam, Ana y Alfredo o lee las variables documentadas en `.env.example`.

## Quality gates

```bash
cd backend
.venv/bin/pytest --cov=apps --cov-fail-under=70
cd ..
backend/.venv/bin/python backend/manage.py check --settings=config.settings.test
npm run lint
npx tsc --noEmit
npm run build
```

`reset_demo_data` sólo funciona con `DEBUG=True`. Los seeds son idempotentes: crean faltantes y no reemplazan correcciones humanas.

## API y documentación

- Pública: `/api/v1/public/`
- Administrativa: `/api/v1/admin/`
- Autenticación: `/api/v1/auth/`
- OpenAPI en desarrollo: `/api/schema/` y `/api/schema/docs/`

Documentos: [arquitectura](docs/architecture.md), [modelo y diccionario](docs/database-model.md), [ER](docs/erd.md), [permisos](docs/permissions.md), [seguridad](docs/security.md), [eventos](docs/analytics-events.md), [BI](docs/bi.md), [DW futuro](docs/data-warehouse-roadmap.md), [preparación IA](docs/ai-data-readiness.md), [backups](docs/backup-recovery.md) y [despliegue](docs/deployment.md).
