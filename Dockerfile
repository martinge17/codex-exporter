FROM cgr.dev/chainguard/python:latest-dev@sha256:df9eb3812f118b33f8fd0bafb7efa0112d6a0810b40b2707337a4c432845f7b4 AS builder

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PATH=/app/venv/bin:$PATH

WORKDIR /app

RUN python -m venv /app/venv
COPY requirements.txt .

RUN pip install --no-cache-dir -r requirements.txt \
    && mkdir /app/data

FROM cgr.dev/chainguard/python:latest@sha256:780029a86e72bf3a58b1795cb77ab73b8f48dfea8c94ab154345396dc3d3237a AS runtime

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
