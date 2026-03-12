"""Tests for the Flask application routes and security."""

from __future__ import annotations

import json
import textwrap
from pathlib import Path

import pytest

from copilot_log_viewer.app import create_app


@pytest.fixture()
def app_with_data(tmp_path: Path):
    """Create an app backed by a temporary session directory."""
    session_dir = tmp_path / "aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee"
    session_dir.mkdir()

    (session_dir / "workspace.yaml").write_text(
        textwrap.dedent("""\
        id: aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee
        summary: Test Session
        repository: org/repo
        branch: main
        created_at: 2026-03-12T10:00:00.000Z
        updated_at: 2026-03-12T10:05:00.000Z
        """)
    )

    events = [
        {"type": "session.start", "data": {"copilotVersion": "1.0.0", "context": {}}, "timestamp": "2026-03-12T10:00:00Z"},
        {"type": "user.message", "data": {"content": "hello"}, "timestamp": "2026-03-12T10:00:01Z"},
        {"type": "session.shutdown", "data": {}, "timestamp": "2026-03-12T10:05:00Z"},
    ]
    with open(session_dir / "events.jsonl", "w") as f:
        for evt in events:
            f.write(json.dumps(evt) + "\n")

    # Create a backup file for the backup endpoint test
    backups = session_dir / "rewind-snapshots" / "backups"
    backups.mkdir(parents=True)
    (backups / "abcdef0123456789-1234567890123").write_text("backup content")

    app = create_app(tmp_path)
    app.config["TESTING"] = True
    return app


def test_index_returns_200(app_with_data) -> None:
    with app_with_data.test_client() as c:
        r = c.get("/")
        assert r.status_code == 200
        assert b"Test Session" in r.data


def test_session_view_returns_200(app_with_data) -> None:
    with app_with_data.test_client() as c:
        r = c.get("/session/aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee")
        assert r.status_code == 200
        assert b"hello" in r.data


def test_session_view_404_for_missing(app_with_data) -> None:
    with app_with_data.test_client() as c:
        r = c.get("/session/11111111-2222-3333-4444-555555555555")
        assert r.status_code == 404


def test_session_view_rejects_path_traversal(app_with_data) -> None:
    """Path traversal attempts are blocked (Flask normalizes ../ to 404)."""
    with app_with_data.test_client() as c:
        r = c.get("/session/../../etc/passwd")
        assert r.status_code in (400, 404)  # blocked either way


def test_session_view_400_for_non_uuid(app_with_data) -> None:
    with app_with_data.test_client() as c:
        r = c.get("/session/not-a-uuid")
        assert r.status_code == 400


def test_api_sessions(app_with_data) -> None:
    with app_with_data.test_client() as c:
        r = c.get("/api/sessions")
        assert r.status_code == 200
        data = r.get_json()
        assert len(data) == 1
        assert data[0]["summary"] == "Test Session"


def test_api_events(app_with_data) -> None:
    with app_with_data.test_client() as c:
        r = c.get("/api/session/aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee/events")
        assert r.status_code == 200
        data = r.get_json()
        assert len(data) == 3


def test_api_backup_returns_content(app_with_data) -> None:
    with app_with_data.test_client() as c:
        r = c.get("/api/session/aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee/backup/abcdef0123456789-1234567890123")
        assert r.status_code == 200
        assert r.data == b"backup content"


def test_api_backup_rejects_path_traversal(app_with_data) -> None:
    """Path traversal in backup hash is blocked."""
    with app_with_data.test_client() as c:
        r = c.get("/api/session/aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee/backup/../../etc/passwd")
        assert r.status_code in (400, 404)  # blocked either way


def test_security_headers(app_with_data) -> None:
    with app_with_data.test_client() as c:
        r = c.get("/")
        assert r.headers["X-Content-Type-Options"] == "nosniff"
        assert r.headers["X-Frame-Options"] == "DENY"
        assert "Content-Security-Policy" in r.headers
        assert "frame-ancestors 'none'" in r.headers["Content-Security-Policy"]
