FROM python:3.14-slim-bookworm@sha256:a3974109d36f164ca70024bc0d0828ac706e4ccda849f8638d879e91f79e90ec AS builder

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /build
COPY requirements.txt .
RUN python -m venv /opt/venv \
    && /opt/venv/bin/pip install --upgrade pip \
    && /opt/venv/bin/pip install --no-cache-dir -r requirements.txt

FROM python:3.14-slim-bookworm@sha256:a3974109d36f164ca70024bc0d0828ac706e4ccda849f8638d879e91f79e90ec AS runtime

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PATH=/opt/venv/bin:$PATH \
    PORT=9212 \
    HOST=0.0.0.0

RUN groupadd --system --gid 10001 exporter \
    && useradd --system --uid 10001 --gid exporter --home-dir /nonexistent --shell /usr/sbin/nologin exporter \
    && mkdir -p /app /data \
    && chown -R exporter:exporter /app /data

WORKDIR /app
COPY --from=builder /opt/venv /opt/venv
COPY --chown=exporter:exporter app ./app

USER exporter
EXPOSE 9212

CMD ["python", "-m", "app.main"]
