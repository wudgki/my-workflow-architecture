"""bridge-ingress FastAPI application.

Endpoints (v1, Telegram-only):
  GET  /healthz             -- liveness probe (200 OK -> {"status":"ok"})
  POST /webhook/telegram    -- Telegram bot webhook receiver

Discord and Feishu webhooks are intentionally NOT exposed. Adding them
is the scope of a future PR after the Telegram path has been validated
against a real bot.

ASCII-only.
"""
from __future__ import annotations

import time
import uuid

from fastapi import FastAPI, Header, HTTPException, Request, Response, status

from config import Settings, load_settings
from inbox_writer import write_telegram_capture
from logger import get_logger, init_logger
from phase_router import PhaseRouter
from signature import verify_telegram_secret


_BRIDGE_VERSION = "0.1.0"


def _build_app() -> FastAPI:
    settings: Settings = load_settings()
    init_logger(settings.log_level)
    log = get_logger("bridge-ingress")
    router = PhaseRouter(settings.keywords_path)

    log.info(
        "bridge_ingress_started",
        extra={
            "version": _BRIDGE_VERSION,
            "file": settings.keywords_path,
        },
    )

    app = FastAPI(
        title="hermes bridge-ingress",
        version=_BRIDGE_VERSION,
        docs_url=None,
        redoc_url=None,
        openapi_url=None,
    )

    @app.get("/healthz")
    def healthz() -> dict[str, str]:
        return {"status": "ok"}

    @app.post("/webhook/telegram")
    async def webhook_telegram(
        request: Request,
        x_telegram_bot_api_secret_token: str | None = Header(default=None),
    ) -> Response:
        req_id = uuid.uuid4().hex[:12]
        started = time.monotonic()
        client_ip = request.client.host if request.client else None

        if not verify_telegram_secret(
            x_telegram_bot_api_secret_token,
            settings.telegram_webhook_secret,
        ):
            log.warning(
                "telegram_webhook_unauthorized",
                extra={"req_id": req_id, "remote_ip": client_ip},
            )
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="unauthorized",
            )

        try:
            payload = await request.json()
        except Exception:
            log.warning(
                "telegram_webhook_bad_json",
                extra={"req_id": req_id, "remote_ip": client_ip},
            )
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="bad_json",
            )

        if not isinstance(payload, dict):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="bad_json",
            )

        # Inline mtime-based hot reload: cheap (one stat()) and immediate.
        # Avoids the complexity of a background poller for a v1 service.
        reloaded = router.reload_if_changed()
        if reloaded:
            log.info(
                "keywords_reloaded",
                extra={"req_id": req_id, "file": settings.keywords_path},
            )

        try:
            result = write_telegram_capture(
                payload=payload,
                inbox_path=settings.inbox_path,
                phase_router=router,
                bridge_version=_BRIDGE_VERSION,
            )
        except ValueError as exc:
            # Valid HTTPS request but payload is not a Telegram message
            # (could be edited_message, callback_query, channel_post, or
            # malformed). Return 200 so Telegram does not retry; log the
            # reason for inspection.
            log.warning(
                "telegram_webhook_payload_skipped",
                extra={
                    "req_id": req_id,
                    "reason": str(exc),
                    "remote_ip": client_ip,
                },
            )
            return Response(status_code=status.HTTP_200_OK)

        latency_ms = int((time.monotonic() - started) * 1000)
        log.info(
            "telegram_capture_written",
            extra={
                "req_id": req_id,
                "source": "telegram",
                "phase": result["phase"],
                "file": result["file"],
                "chat_id": result["chat_id"],
                "message_id": result["message_id"],
                "latency_ms": latency_ms,
                "remote_ip": client_ip,
            },
        )
        return Response(status_code=status.HTTP_200_OK)

    return app


app = _build_app()
