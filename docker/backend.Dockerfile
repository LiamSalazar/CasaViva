FROM python:3.12-slim AS runtime

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    DJANGO_SETTINGS_MODULE=config.settings.production
WORKDIR /app
RUN groupadd --system casaviva && useradd --system --gid casaviva casaviva
COPY backend/requirements /app/requirements
RUN pip install --no-cache-dir -r /app/requirements/production.txt
COPY backend /app
RUN mkdir -p /app/media /app/staticfiles && chown -R casaviva:casaviva /app
USER casaviva
EXPOSE 8000
HEALTHCHECK --interval=30s --timeout=5s --start-period=20s --retries=3 CMD python -c "import urllib.request; request = urllib.request.Request('http://127.0.0.1:8000/api/health/live/', headers={'X-Forwarded-Proto': 'https'}); urllib.request.urlopen(request, timeout=3).read()"
CMD ["gunicorn", "config.wsgi:application", "--bind", "0.0.0.0:8000", "--access-logfile", "-", "--error-logfile", "-"]
