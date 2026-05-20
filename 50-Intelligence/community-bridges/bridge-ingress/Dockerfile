# syntax=docker/dockerfile:1.6
# bridge-ingress v0.2.0: Telegram MTProto listener + healthcheck.

FROM python:3.12-alpine AS builder
WORKDIR /build
RUN apk add --no-cache build-base libffi-dev
COPY requirements.txt .
RUN python -m venv /opt/venv \
    && /opt/venv/bin/pip install --no-cache-dir --upgrade pip \
    && /opt/venv/bin/pip install --no-cache-dir -r requirements.txt

FROM python:3.12-alpine AS runtime
RUN apk add --no-cache curl tini libffi \
    && addgroup -S bridge && adduser -S -G bridge -h /app bridge
WORKDIR /app
COPY --from=builder /opt/venv /opt/venv
COPY --chown=bridge:bridge \
    main.py config.py signature.py phase_router.py \
    inbox_writer.py logger.py tg_listener.py /app/
ENV PATH=/opt/venv/bin:$PATH \
    PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 \
    LISTEN_PORT=8080 LOG_LEVEL=info \
    INBOX_PATH=/data/inbox \
    KEYWORDS_PATH=/blueprint/50-Intelligence/pipelines/keywords.yaml
EXPOSE 8080
USER bridge
ENTRYPOINT ["/sbin/tini", "--"]
CMD ["sh", "-c", "uvicorn main:app --host 0.0.0.0 --port ${LISTEN_PORT} --log-level ${LOG_LEVEL}"]
