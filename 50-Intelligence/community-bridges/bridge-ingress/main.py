"""bridge-ingress application (v0.2.0).

Architecture:
  - FastAPI with /healthz endpoint (for docker compose healthcheck)
  - Telegram MTProto listener (Telethon userbot, primary ingest path)
  - Legacy /webhook/telegram endpoint (kept but requires
    TELEGRAM_WEBHOOK_SECRET to be set; disabled by default in v0.2.0)

The MTProto listener runs as a background asyncio task that starts
when the FastAPI lifespan begins and stops on shutdown (SIGTERM).

Testability:
  create_app() accepts an optional listener_factory callable. When None
  (production), it creates a real TelegramListener. Tests inject a fake
  factory that returns a stub, so pytest never touches Telethon.

ASCII-only.
"""
from __future__ import annotations

import asyncio
import time
import uuid
from contextlib import asynccontextmanager
from typing import Any, AsyncGenerator, Callable, Optional, Protocol

from fastapi import FastAPI, Header, HTTPException, Request, Response, status

from config import Settings, load_settings
from inbox_writer import write_telegram_capture
from logger import get_logger, init_logger
from phase_router import PhaseRouter
from signature import verify_telegram_secret
from tg_listener import TelegramListener, _parse_chat_ids


_BRIDGE_VERSION = "0.2.0"


class ListenerProtocol(Protocol):
    """Minimal interface that main.py requires from a listener."""

    @property
    def connected(self) -> bool: ...

    @property
    def messages_processed(self) -> int: ...

    async def start(self) -> None: ...

    async def run_until_disconnected(self) -> None: ...

    async def stop(self) -> None: ...


def _default_listener_factory(settings: Settings) -> TelegramListener:
    """Production factory: creates a real TelegramListener."""
    return TelegramListener(
        api_id=settings.tg_api_id,
        api_hash=settings.tg_api_hash,
        session_string=settings.tg_session_string,
        meme_chat_ids=_parse_chat_ids(settings.tg_meme_chat_ids),
        contract_chat_ids=_parse_chat_ids(settings.tg_contract_chat_ids),
        inbox_path=settings.inbox_path,
        keywords_path=settings.keywords_path,
    )


def create_app(
    settings: Optional[Settings] = None,
    listener_factory: Optional[Callable[[Settings], Any]] = None,
) -> FastAPI:
    """Build the FastAPI application.

    Args:
        settings: If None, loaded from environment variables.
        listener_factory: Callable(settings) -> listener instance.
            If None, uses _default_listener_factory (real Telethon).
            Tests pass a fake factory to avoid real Telegram connections.
    """
    if settings is None:
        settings = load_settings()

    init_logger(settings.log_level)
    log = get_logger("bridge-ingress")
    router = PhaseRouter(settings.keywords_path)

    if listener_factory is None:
        listener_factory = _default_listener_factory
    listener = listener_factory(settings)

    log.info(
        "bridge_ingress_started",
        extra={
            "version": _BRIDGE_VERSION,
            "mode": "mtproto_listener",
            "file": settings.keywords_path,
        },
    )

    @asynccontextmanager
    async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
        # Startup: connect the Telegram listener.
        await listener.start()
        listener_task = asyncio.create_task(
            listener.run_until_disconnected()
        )
        yield
        # Shutdown: graceful disconnect.
        await listener.stop()
        listener_task.cancel()
        try:
            await listener_task
        except asyncio.CancelledError:
            pass

    app = FastAPI(
        title="hermes bridge-ingress",
        version=_BRIDGE_VERSION,
        docs_url=None,
        redoc_url=None,
        openapi_url=None,
        lifespan=lifespan,
    )

    @app.get("/healthz")
    def healthz() -> dict:
        return {
            "status": "ok",
            "listener_connected": listener.connected,
            "messages_processed": listener.messages_processed,
        }

    # --- Legacy webhook endpoint (kept for backward compat) ---
    # Only active if TELEGRAM_WEBHOOK_SECRET is set.
    if settings.telegram_webhook_secret:

        @app.post("/webhook/telegram")
        async def webhook_telegram(
            request: Request,
            x_telegram_bot_api_secret_token: str | None = Header(
                default=None
            ),
        ) -> Response:
            req_id = uuid.uuid4().hex[:12]
            started = time.monotonic()
            client_ip = (
                request.client.host if request.client else None
            )

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
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="bad_json",
                )

            if not isinstance(payload, dict):
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="bad_json",
                )

            router.reload_if_changed()

            try:
                result = write_telegram_capture(
                    payload=payload,
                    inbox_path=settings.inbox_path,
                    phase_router=router,
                    bridge_version=_BRIDGE_VERSION,
                )
            except ValueError as exc:
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


# Module-level app for uvicorn: `uvicorn main:app`
# Guarded so that pytest (which sets _TESTING=1 or imports create_app
# directly) does not trigger a real Telethon session on import.
import os as _os

if _os.environ.get("_BRIDGE_SKIP_AUTO_CREATE") != "1":
    app = create_app()
else:
    # Placeholder so `from main import app` does not raise AttributeError
    # in test modules that need to reference the name before calling
    # create_app() themselves.
    app = None  # type: ignore[assignment]
