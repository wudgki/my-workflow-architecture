# syntax=docker/dockerfile:1.6
#
# bridge-ingress: Telegram MTProto listener + healthcheck (v0.2.0).
# Multi-stage build on alpine. Target: < 100 MB final image.
#
# Build:
#   docker build -t bridge-ingress:dev .
#
# Run (requires TG_API_ID, TG_API_HASH, TG_SESSION_STRING + chat IDs):
#   docker run -d --name bridge-ingress \
#     --env-file .env \
#     -v /tmp/inbox:/data/inbox \
#     -v $PWD/../../pipelines/keywords.yaml:/blueprint/50-Intelligence/pipelines/keywords.yaml:ro \
#     -p 8080:8080 bridge-ingress:dev


# ---------- builder ----------
FROM python:3.12-alpine AS builder

WORKDIR /build

# build-base needed for C extensions (cryptg, PyYAML).
# libffi-dev needed for telethon's crypto acceleration.
RUN apk add --no-cache build-base libffi-dev

COPY requirements.txt .

RUN python -m venv /opt/venv \
    && /opt/venv/bin/pip install --no-cache-dir --upgrade pip \
    && /opt/venv/bin/pip install --no-cache-dir -r requirements.txt


# ---------- runtime ----------
FROM python:3.12-alpine AS runtime

# curl: required for the docker compose healthcheck declared in PR #12.
# tini: PID 1 / signal forwarding so SIGTERM cleanly stops uvicorn.
# libffi: runtime dep for cryptg.
RUN apk add --no-cache curl tini libffi \
    && addgroup -S bridge \
    && adduser -S -G bridge -h /app bridge

WORKDIR /app

COPY --from=builder /opt/venv /opt/venv
COPY --chown=bridge:bridge \
    main.py \
    config.py \
    signature.py \
    phase_router.py \
    inbox_writer.py \
    logger.py \
    tg_listener.py \
    /app/

ENV PATH=/opt/venv/bin:$PATH \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    LISTEN_PORT=8080 \
    LOG_LEVEL=info \
    INBOX_PATH=/data/inbox \
    KEYWORDS_PATH=/blueprint/50-Intelligence/pipelines/keywords.yaml

EXPOSE 8080

USER bridge

ENTRYPOINT ["/sbin/tini", "--"]
CMD ["sh", "-c", "uvicorn main:app --host 0.0.0.0 --port ${LISTEN_PORT} --log-level ${LOG_LEVEL}"]
