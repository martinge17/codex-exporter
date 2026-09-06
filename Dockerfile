FROM cgr.dev/chainguard/python:latest-dev@sha256:afdbadf8d697739ab8e10a4d355d0850daa439cba3e6f0e39a73f7f2d3d839b7 AS builder

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PATH=/app/venv/bin:$PATH

WORKDIR /app

RUN python -m venv /app/venv
COPY requirements.txt .

RUN pip install --no-cache-dir -r requirements.txt \
    && mkdir /app/data

FROM cgr.dev/chainguard/python:latest@sha256:eca30c0ac647bf28beaec7442388609d14fd100984fa63397e6015eaffe22aa1 AS runtime

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
