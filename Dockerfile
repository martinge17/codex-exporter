FROM python:3.14-slim-bookworm@sha256:86f975aca15cf04a40b399eebede9aea7c82eae084d1f1a0a6ef6bcaae871a30 AS builder

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /build
COPY requirements.txt .
RUN python -m venv /opt/venv \
    && /opt/venv/bin/pip install --upgrade pip \
    && /opt/venv/bin/pip install --no-cache-dir --no-compile -r requirements.txt \
    && /opt/venv/bin/pip uninstall -y pip setuptools \
    && find /opt/venv -type d -name '__pycache__' -prune -exec rm -rf '{}' +

FROM python:3.14-slim-bookworm@sha256:86f975aca15cf04a40b399eebede9aea7c82eae084d1f1a0a6ef6bcaae871a30 AS runtime

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
