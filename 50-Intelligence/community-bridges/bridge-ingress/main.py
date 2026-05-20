"""bridge-ingress application (v0.2.1).

Architecture:
  - FastAPI starts FIRST, /healthz always accessible.
  - Telegram MTProto listener starts as a background task AFTER FastAPI
    is up. If the listener fails to connect, /healthz reports the error
    but the HTTP server remains healthy.

Testability: create_app() accepts an optional listener_factory. Tests
inject a fake factory so pytest never touches Telethon.

ASCII-only.
"""
from __future__ import annotations

import asyncio
import os
import time
import uuid
from contextlib import asynccontextmanager
from typing import Any, AsyncGenerator, Callable, Optional, Protocol, Tuple

from fastapi import FastAPI, Header, HTTPException, Request, Response, status

from config import Settings, load_settings
from inbox_writer import write_telegram_capture
from logger import get_logger, init_logger
from phase_router import PhaseRouter
from signature import verify_telegram_secret
from tg_listener import TelegramListener, _parse_chat_ids


_BRIDGE_VERSION = "0.2.1"


class ListenerProtocol(Protocol):
    @property
    def connected(self) -> bool: ...
    @property
    def messages_processed(self) -> int: ...
    @property
    def last_error(self) -> str: ...
    async def start(self) -> None: ...
    async def run_until_disconnected(self) -> None: ...
    async def stop(self) -> None: ...


def _build_proxy_tuple(settings: Settings) -> Optional[Tuple]:
    """Build a python-socks compatible proxy tuple from settings.

    Returns None if proxy is not configured.
    Format: (proxy_type, host, port, rdns, username, password)
    """
    if not settings.tg_proxy_type or not settings.tg_proxy_host:
        return None
    import socks
    proxy_type_map = {
        "socks5": socks.SOCKS5,
        "socks4": socks.SOCKS4,
        "http": socks.HTTP,
    }
    ptype = proxy_type_map.get(settings.tg_proxy_type.lower())
    if ptype is None:
        return None
    return (
        ptype,
        settings.tg_proxy_host,
        settings.tg_proxy_port or 1080,
        True,
        settings.tg_proxy_username or None,
        settings.tg_proxy_password or None,
    )


def _default_listener_factory(settings: Settings) -> TelegramListener:
    return TelegramListener(
        api_id=settings.tg_api_id,
        api_hash=settings.tg_api_hash,
        session_string=settings.tg_session_string,
        meme_chat_ids=_parse_chat_ids(settings.tg_meme_chat_ids),
        contract_chat_ids=_parse_chat_ids(settings.tg_contract_chat_ids),
        inbox_path=settings.inbox_path,
        keywords_path=settings.keywords_path,
        dc_id=settings.tg_dc_id,
        server_address=settings.tg_server_address,
        server_port=settings.tg_server_port,
        proxy=_build_proxy_tuple(settings),
    )


def create_app(
    settings: Optional[Settings] = None,
    listener_factory: Optional[Callable[[Settings], Any]] = None,
) -> FastAPI:
    """Build the FastAPI application.

    The listener is started as a background task during lifespan startup.
    If it fails to connect (timeout, DC unreachable, session expired),
    FastAPI remains operational and /healthz reports the failure.
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
        extra={"version": _BRIDGE_VERSION, "file": settings.keywords_path},
    )

    @asynccontextmanager
    async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
        # Start listener as a background task. Do NOT await it here so
        # FastAPI startup completes immediately regardless of Telegram
        # connection outcome.
        async def _listener_lifecycle() -> None:
            await listener.start()
            if listener.connected:
                await listener.run_until_disconnected()

        listener_task = asyncio.create_task(_listener_lifecycle())
        yield
        # Shutdown: stop listener, cancel task.
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
        result: dict = {
            "status": "ok",
            "listener_connected": listener.connected,
            "messages_processed": listener.messages_processed,
        }
        if listener.last_error:
            result["last_error"] = listener.last_error
        return result

    # Legacy webhook endpoint: only active if TELEGRAM_WEBHOOK_SECRET is set.
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
                    extra={"req_id": req_id, "reason": str(exc)},
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
                },
            )
            return Response(status_code=status.HTTP_200_OK)

    return app


# Module-level app for uvicorn. Guarded for tests.
if os.environ.get("_BRIDGE_SKIP_AUTO_CREATE") != "1":
    app = create_app()
else:
    app = None  # type: ignore[assignment]
