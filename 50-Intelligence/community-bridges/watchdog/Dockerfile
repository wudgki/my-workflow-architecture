# syntax=docker/dockerfile:1.6
# bridge-ingress watchdog: alpine + curl + jq + bash + tini.
# Final image target: < 20 MB.

FROM alpine:3.20

RUN apk add --no-cache bash curl jq tini ca-certificates \
    && addgroup -S watchdog \
    && adduser -S -G watchdog -h /app watchdog

WORKDIR /app

COPY --chown=watchdog:watchdog watchdog.sh alert.sh /app/

RUN chmod +x /app/watchdog.sh /app/alert.sh

USER watchdog

ENV BRIDGE_HEALTHZ_URL=http://bridge-ingress:8080/healthz \
    CHECK_INTERVAL_SECONDS=60 \
    FAILURE_THRESHOLD=3 \
    LOG_LEVEL=info

ENTRYPOINT ["/sbin/tini", "--"]
CMD ["/app/watchdog.sh"]
