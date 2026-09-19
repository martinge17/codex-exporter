FROM cgr.dev/chainguard/python:latest-dev@sha256:075c08ad4c1d529dfb0ee3aaeab034268c912771256132765bb0751d0dba6572 AS builder

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PATH=/app/venv/bin:$PATH

WORKDIR /app

RUN python -m venv /app/venv
COPY requirements.txt .

RUN python -m pip install --no-cache-dir -r requirements.txt \
    && python -m pip uninstall --yes pip \
    && mkdir /app/data

FROM cgr.dev/chainguard/python:latest@sha256:e8525291a96a1bbd9e6e2006633b78f8105e0cdefd12e678f425ff703d73bfdf AS runtime

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
