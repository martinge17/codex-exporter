FROM cgr.dev/chainguard/python:latest-dev@sha256:7108dea9b9f31c30c20d43d17ecc61d4eb33789e9a8a10cd361e2ed37d8bd931 AS builder

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PATH=/app/venv/bin:$PATH

WORKDIR /app

RUN python -m venv /app/venv
COPY requirements.txt .

RUN python -m pip install --no-cache-dir -r requirements.txt \
    && python -m pip uninstall --yes pip \
    && mkdir /app/data

FROM cgr.dev/chainguard/python:latest@sha256:93c92d4ee2d0a4e540ec4de4e708267b45c2551a3c836fdf3e174a05017a76de AS runtime

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
