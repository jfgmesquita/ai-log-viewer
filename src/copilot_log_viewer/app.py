"""Flask application for the Copilot Session Log Viewer."""

from __future__ import annotations

import json
import re
from pathlib import Path

import markdown
from flask import Flask, render_template, jsonify, abort, request, Response
from markupsafe import Markup

from .parser import (
    discover_sessions,
    parse_events,
    parse_snapshots,
    parse_workspace,
    build_conversation,
    compute_stats,
    ts_display,
    ts_relative,
    duration_between,
)

# ---------------------------------------------------------------------------
# Validation helpers
# ---------------------------------------------------------------------------

# Session IDs are UUIDs — enforce that to prevent path traversal.
_UUID_RE = re.compile(
    r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$",
    re.IGNORECASE,
)

# Backup hash filenames: hex-timestamp
_BACKUP_HASH_RE = re.compile(r"^[0-9a-f]{16}-\d{13}$")


def _validate_session_id(session_id: str) -> None:
    if not _UUID_RE.match(session_id):
        abort(400, description="Invalid session ID format")


def _validate_backup_hash(backup_hash: str) -> None:
    if not _BACKUP_HASH_RE.match(backup_hash):
        abort(400, description="Invalid backup hash format")


# ---------------------------------------------------------------------------
# Markdown rendering
# ---------------------------------------------------------------------------

def md_to_html(text: str) -> str:
    if not text:
        return ""
    return markdown.markdown(
        text,
        extensions=["fenced_code", "tables", "codehilite", "nl2br"],
        extension_configs={"codehilite": {"css_class": "codehilite", "guess_lang": False}},
    )


# ---------------------------------------------------------------------------
# App factory
# ---------------------------------------------------------------------------

def create_app(log_dir: str | Path | None = None) -> Flask:
    """Create and configure the Flask application.

    Parameters
    ----------
    log_dir:
        Root directory containing Copilot session folders.
        Falls back to the ``COPILOT_LOG_DIR`` env var, then ``"."``.
    """
    import os

    if log_dir is None:
        log_dir = os.environ.get("COPILOT_LOG_DIR", ".")
    log_path = Path(log_dir).resolve()

    app = Flask(
        __name__,
        template_folder=str(Path(__file__).parent / "templates"),
    )

    # -- Security configuration ----------------------------------------------
    # Disable debug/testing by default (CLI may override for local use).
    app.config["DEBUG"] = False
    app.config["TESTING"] = False
    # Secret key only needed if we ever add sessions; generate one anyway.
    app.config["SECRET_KEY"] = os.urandom(32)
    # Limit maximum request size (no uploads, but defence-in-depth).
    app.config["MAX_CONTENT_LENGTH"] = 1 * 1024 * 1024  # 1 MB

    # -- Security headers (after every response) -----------------------------
    @app.after_request
    def _security_headers(response: Response) -> Response:
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["Referrer-Policy"] = "no-referrer"
        response.headers["Content-Security-Policy"] = (
            "default-src 'self'; "
            "style-src 'self' 'unsafe-inline'; "
            "script-src 'self' 'unsafe-inline'; "
            "img-src 'self' data:; "
            "font-src 'self'; "
            "frame-ancestors 'none'"
        )
        return response

    # -- Routes --------------------------------------------------------------

    @app.route("/")
    def index():
        sessions = discover_sessions(log_path)
        return render_template("index.html", sessions=sessions, log_dir=str(log_path))

    @app.route("/session/<session_id>")
    def session_view(session_id: str):
        _validate_session_id(session_id)
        session_dir = log_path / session_id
        if not session_dir.is_dir():
            abort(404)

        ws = parse_workspace(session_dir)
        events = parse_events(session_dir)
        conversation = build_conversation(events)
        stats = compute_stats(events)
        snapshots = parse_snapshots(session_dir)

        return render_template(
            "session.html",
            ws=ws,
            session_id=session_id,
            conversation=conversation,
            stats=stats,
            snapshots=snapshots,
            ts_display=ts_display,
            ts_relative=ts_relative,
            duration_between=duration_between,
            md_to_html=md_to_html,
            json=json,
            isinstance=isinstance,
            str=str,
            len=len,
            list=list,
            dict=dict,
            Markup=Markup,
        )

    # -- JSON API ------------------------------------------------------------

    @app.route("/api/sessions")
    def api_sessions():
        return jsonify(discover_sessions(log_path))

    @app.route("/api/session/<session_id>/events")
    def api_events(session_id: str):
        _validate_session_id(session_id)
        session_dir = log_path / session_id
        if not session_dir.is_dir():
            abort(404)
        return jsonify(parse_events(session_dir))

    @app.route("/api/session/<session_id>/backup/<backup_hash>")
    def api_backup(session_id: str, backup_hash: str):
        _validate_session_id(session_id)
        _validate_backup_hash(backup_hash)
        backup_file = log_path / session_id / "rewind-snapshots" / "backups" / backup_hash
        # Resolve and verify the path stays within the log directory.
        resolved = backup_file.resolve()
        if not str(resolved).startswith(str(log_path)):
            abort(403)
        if not resolved.is_file():
            abort(404)
        content = resolved.read_text(errors="replace")
        return content, 200, {"Content-Type": "text/plain; charset=utf-8"}

    return app
