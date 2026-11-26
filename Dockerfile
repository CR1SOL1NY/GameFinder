FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    ENVIRONMENT=production \
    COOKIE_SECURE=true \
    COOKIE_SAMESITE=lax \
    CORS_ORIGINS=""

WORKDIR /srv/gamefinder

COPY requirements-interfaz.lock.txt ./
RUN python -m pip install --no-cache-dir -r requirements-interfaz.lock.txt \
    && useradd --create-home --uid 10001 --user-group gamefinder

COPY --chown=gamefinder:gamefinder app/ ./app/
COPY --chown=gamefinder:gamefinder integracion_frontend/ ./integracion_frontend/
COPY --chown=gamefinder:gamefinder main.py main_interfaz.py ./

USER gamefinder
EXPOSE 8000

CMD ["sh", "-c", "exec python -m uvicorn main_interfaz:app --host 0.0.0.0 --port \"${PORT:-8000}\""]
