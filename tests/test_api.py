import base64
from unittest.mock import AsyncMock

import bcrypt
from fastapi.testclient import TestClient
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import padding

from release2gitcode.core.models import SyncRequest, SyncResult
from release2gitcode.core.security import _get_api_key_hash_bytes
from release2gitcode.core.logger import SecurityLogger
from release2gitcode.server.app import create_app


def _encrypt(public_key_pem: str, secret: str) -> str:
    public_key = serialization.load_pem_public_key(public_key_pem.encode("utf-8"))
    encrypted = public_key.encrypt(
        secret.encode("utf-8"),
        padding.OAEP(
            mgf=padding.MGF1(algorithm=hashes.SHA256()),
            algorithm=hashes.SHA256(),
            label=None,
        ),
    )
    return base64.b64encode(encrypted).decode("utf-8")


def test_public_key_requires_api_key() -> None:
    client = TestClient(create_app())
    response = client.get("/api/v1/public-key", headers={"X-Forwarded-Proto": "https"})
    assert response.status_code == 401


def test_sync_request_accepts_optional_serverchan_field() -> None:
    payload = SyncRequest(
        github_release_url="https://github.com/octo/demo/releases/tag/v1.0.0",
        gitcode_repo_url="https://gitcode.com/octo/demo",
        encrypted_gitcode_token="abc",
        encrypted_GH_TOKEN="ghi",
        encrypted_serverchan3_sendkey="def",
    )
    assert payload.encrypted_serverchan3_sendkey == "def"
    assert payload.encrypted_GH_TOKEN == "ghi"


def test_public_key_returns_rsa_material_when_api_key_valid() -> None:
    from release2gitcode.core.config import settings

    api_key = "r2gc-" + "A" * 59
    original_hash = settings.api_key_hash
    settings.api_key_hash = bcrypt.hashpw(api_key.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")
    _get_api_key_hash_bytes.cache_clear()

    try:
        client = TestClient(create_app())
        public_key_response = client.get(
            "/api/v1/public-key",
            headers={"X-API-Key": api_key, "X-Forwarded-Proto": "https"},
        )
        assert public_key_response.status_code == 200
        public_key = public_key_response.json()["public_key"]
        assert "BEGIN PUBLIC KEY" in public_key
        assert _encrypt(public_key, "gitcode-token")
    finally:
        settings.api_key_hash = original_hash
        _get_api_key_hash_bytes.cache_clear()


def test_sync_returns_accepted_immediately_and_runs_in_background(monkeypatch) -> None:
    from release2gitcode.core.config import settings
    from release2gitcode.server import app as server_app

    api_key = "r2gc-" + "A" * 59
    original_hash = settings.api_key_hash
    settings.api_key_hash = bcrypt.hashpw(api_key.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")
    _get_api_key_hash_bytes.cache_clear()

    try:
        client = TestClient(create_app())
        public_key_response = client.get(
            "/api/v1/public-key",
            headers={"X-API-Key": api_key, "X-Forwarded-Proto": "https"},
        )
        public_key = public_key_response.json()["public_key"]

        sync_mock = AsyncMock(
            return_value=SyncResult(
                task_id="task-123",
                triggered_at="2026-03-21 19:10:00 UTC",
                github_release_url="https://github.com/octo/demo/releases/tag/v1.0.0",
                gitcode_repo_url="https://gitcode.com/octo/demo",
                processed_assets=1,
                skipped_assets=0,
                failed_assets=[],
                total_assets=1,
                duration_seconds=0.1,
            )
        )
        monkeypatch.setattr(server_app.ReleaseSyncService, "sync_github_release", sync_mock)

        response = client.post(
            "/api/v1/sync",
            headers={"X-API-Key": api_key, "X-Forwarded-Proto": "https"},
            json={
                "github_release_url": "https://github.com/octo/demo/releases/tag/v1.0.0",
                "gitcode_repo_url": "https://gitcode.com/octo/demo",
                "encrypted_gitcode_token": _encrypt(public_key, "gitcode-token"),
                "encrypted_GH_TOKEN": _encrypt(public_key, "github-token"),
            },
        )

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "accepted"
        assert data["message"] == "Synchronization task accepted and running in background."
        assert data["processed_assets"] == 0
        assert data["skipped_assets"] == 0
        assert data["failed_assets"] == []
        assert data["task_id"]
        sync_mock.assert_awaited_once()
    finally:
        settings.api_key_hash = original_hash
        _get_api_key_hash_bytes.cache_clear()


def test_sync_progress_log_contains_completion_and_eta(monkeypatch) -> None:
    logger = SecurityLogger(name="security-test")
    captured: dict[str, object] = {}

    def fake_log(**kwargs) -> None:
        captured.update(kwargs)

    monkeypatch.setattr(logger, "_log", fake_log)

    logger.log_sync_progress(
        "task-123",
        asset_name="demo.zip",
        asset_status="completed",
        asset_index=3,
        total_assets=5,
        completed_assets=3,
        remaining_assets=2,
        processed_assets=2,
        skipped_assets=1,
        failed_assets=0,
        elapsed_seconds=12.5,
        estimated_remaining_seconds=8.3,
    )

    assert captured["event_type"] == "sync_progress"
    assert captured["request_id"] == "task-123"
    assert "[3/5] demo.zip" in str(captured["message"])
    assert "completed=3/5" in str(captured["message"])
    assert "remaining=2" in str(captured["message"])
    assert "elapsed=00:00:12" in str(captured["message"])
    assert "eta=00:00:08" in str(captured["message"])
    assert captured["extra"] == {
        "asset_name": "demo.zip",
        "asset_status": "completed",
        "asset_index": 3,
        "total_assets": 5,
        "completed_assets": 3,
        "remaining_assets": 2,
        "processed_assets": 2,
        "skipped_assets": 1,
        "failed_assets": 0,
        "elapsed_seconds": 12.5,
        "elapsed_human": "00:00:12",
        "estimated_remaining_seconds": 8.3,
        "estimated_remaining_human": "00:00:08",
    }
