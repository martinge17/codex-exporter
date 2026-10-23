FROM cgr.dev/chainguard/python:latest-dev@sha256:396cfa5024c3abce8c911e56cd512d9a4fd51c3b2fd30db9f186e8065354970e AS builder

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PATH=/app/venv/bin:$PATH

WORKDIR /app

RUN python -m venv /app/venv
COPY requirements.txt .

RUN python -m pip install --no-cache-dir -r requirements.txt \
    && python -m pip uninstall --yes pip \
    && mkdir /app/data

FROM cgr.dev/chainguard/python:latest@sha256:f6b8842ea63af0021bc79d164c3023b5ea975031c80b6e6f7ade41640084d053 AS runtime

WORKDIR /app
COPY --from=builder /app/venv /app/venv
COPY app ./app
COPY --from=builder /app/data /data

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PATH=/app/venv/bin:$PATH \
    PORT=9212 \
    HOST=0.0.0.0

USER 65532
EXPOSE 9212

ENTRYPOINT ["python", "-m", "app.main"]
