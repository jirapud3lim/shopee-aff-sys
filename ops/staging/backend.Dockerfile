FROM ghcr.io/astral-sh/uv:0.11.13 AS uv
FROM python:3.12-slim-bookworm

ENV PYTHONUNBUFFERED=1 PYTHONDONTWRITEBYTECODE=1 UV_PROJECT_ENVIRONMENT=/opt/venv
WORKDIR /app
RUN apt-get update && apt-get install -y --no-install-recommends ffmpeg gosu \
    && rm -rf /var/lib/apt/lists/* \
    && useradd --system --no-create-home --uid 10001 studio \
    && install -d -o studio -g studio /var/lib/studio/renders
COPY --from=uv /uv /usr/local/bin/uv
COPY backend/pyproject.toml backend/uv.lock backend/
COPY spikes/phase0_publish/ spikes/phase0_publish/
RUN uv sync --locked --no-dev --project backend
COPY backend/app/ backend/app/
COPY backend/alembic/ backend/alembic/
COPY backend/alembic.ini backend/
COPY spikes/phase0_video/render_sample.sh spikes/phase0_video/
COPY ops/staging/backend-entrypoint.sh /usr/local/bin/studio-entrypoint
ENV PATH="/opt/venv/bin:$PATH" PYTHONPATH=/app/backend RENDER_ROOT=/var/lib/studio/renders
ENTRYPOINT ["bash", "/usr/local/bin/studio-entrypoint"]
CMD ["python", "-m", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8001"]
