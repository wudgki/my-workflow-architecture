"""End-to-end FastAPI tests via legacy webhook endpoint.

MTProto listener replaced with FakeListener stub. ASCII-only.
"""
from __future__ import annotations

import asyncio
import importlib
import sys
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

_RELOAD_TARGETS = (
    "main", "config", "phase_router", "inbox_writer",
    "logger", "signature", "tg_listener",
)


class _FakeListener:
    def __init__(self, **kwargs: object) -> None:
        self._connected = False
        self._messages_processed = 0
        self.last_error = ""

    @property
    def connected(self) -> bool:
        return self._connected

    @property
    def messages_processed(self) -> int:
        return self._messages_processed

    async def start(self) -> None:
        self._connected = True

    async def run_until_disconnected(self) -> None:
        try:
            await asyncio.sleep(3600)
        except asyncio.CancelledError:
            pass

    async def stop(self) -> None:
        self._connected = False


@pytest.fixture
def client(app_env) -> TestClient:
    for mod in _RELOAD_TARGETS:
        sys.modules.pop(mod, None)

    main_mod = importlib.import_module("main")
    config_mod = importlib.import_module("config")
    settings = config_mod.load_settings()

    def fake_factory(s: object) -> _FakeListener:
        return _FakeListener()

    test_app = main_mod.create_app(
        settings=settings, listener_factory=fake_factory
    )
    with TestClient(test_app) as c:
        yield c


def test_healthz(client: TestClient) -> None:
    res = client.get("/healthz")
    assert res.status_code == 200
    assert res.json()["status"] == "ok"
    assert res.json()["listener_connected"] is True


def test_webhook_missing_secret_returns_401(client: TestClient) -> None:
    res = client.post("/webhook/telegram", json={"update_id": 1})
    assert res.status_code == 401


def test_webhook_wrong_secret_returns_401(client: TestClient) -> None:
    res = client.post(
        "/webhook/telegram",
        json={"update_id": 1},
        headers={"X-Telegram-Bot-Api-Secret-Token": "wrong"},
    )
    assert res.status_code == 401


def test_webhook_correct_secret_writes_file(
    client: TestClient, fake_secret: str, inbox_dir: Path
) -> None:
    payload = {
        "update_id": 9001,
        "message": {
            "message_id": 17,
            "date": 1_700_000_000,
            "chat": {"id": -100, "type": "supergroup"},
            "from": {"id": 1, "username": "trader"},
            "text": "Polymarket election odds drifting",
        },
    }
    res = client.post(
        "/webhook/telegram",
        json=payload,
        headers={"X-Telegram-Bot-Api-Secret-Token": fake_secret},
    )
    assert res.status_code == 200
    captures_dir = inbox_dir / "Telegram-Captures"
    captures = list(captures_dir.iterdir())
    assert len(captures) == 1
    body = captures[0].read_text(encoding="utf-8")
    assert "phase: phase_4" in body
    assert "chat_id: -100" in body
    assert "message_id: 17" in body


def test_webhook_no_message_returns_200_no_file(
    client: TestClient, fake_secret: str, inbox_dir: Path
) -> None:
    res = client.post(
        "/webhook/telegram",
        json={"update_id": 1},
        headers={"X-Telegram-Bot-Api-Secret-Token": fake_secret},
    )
    assert res.status_code == 200
    captures_dir = inbox_dir / "Telegram-Captures"
    if captures_dir.exists():
        assert list(captures_dir.iterdir()) == []


def test_webhook_bad_json_returns_400(
    client: TestClient, fake_secret: str
) -> None:
    res = client.post(
        "/webhook/telegram",
        content=b"not-json-at-all",
        headers={
            "X-Telegram-Bot-Api-Secret-Token": fake_secret,
            "Content-Type": "application/json",
        },
    )
    assert res.status_code == 400


def test_webhook_array_payload_returns_400(
    client: TestClient, fake_secret: str
) -> None:
    res = client.post(
        "/webhook/telegram",
        json=[1, 2, 3],
        headers={"X-Telegram-Bot-Api-Secret-Token": fake_secret},
    )
    assert res.status_code == 400


def test_webhook_idempotent_redelivery(
    client: TestClient, fake_secret: str, inbox_dir: Path
) -> None:
    payload = {
        "update_id": 42,
        "message": {
            "message_id": 7,
            "date": 1_700_000_100,
            "chat": {"id": 999, "type": "private"},
            "from": {"id": 1, "username": "redeliv"},
            "text": "Hermes infra deployment status",
        },
    }
    headers = {"X-Telegram-Bot-Api-Secret-Token": fake_secret}
    res1 = client.post("/webhook/telegram", json=payload, headers=headers)
    res2 = client.post("/webhook/telegram", json=payload, headers=headers)
    assert res1.status_code == 200
    assert res2.status_code == 200
    captures = list((inbox_dir / "Telegram-Captures").iterdir())
    assert len(captures) == 1
