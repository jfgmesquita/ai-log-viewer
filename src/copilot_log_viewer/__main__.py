"""Entry point: ``python -m copilot_log_viewer [LOG_DIR]``."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from . import __version__
from .app import create_app
from .parser import discover_sessions


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(
        prog="copilot-log-viewer",
        description="Browse GitHub Copilot agent session logs in a local web UI.",
    )
    parser.add_argument(
        "log_dir",
        nargs="?",
        default=".",
        help="Directory containing Copilot session log folders (default: current dir)",
    )
    parser.add_argument(
        "-p", "--port",
        type=int,
        default=5000,
        help="Port to listen on (default: 5000)",
    )
    parser.add_argument(
        "--host",
        default="127.0.0.1",
        help="Host to bind to (default: 127.0.0.1)",
    )
    parser.add_argument(
        "--debug",
        action="store_true",
        default=False,
        help="Run in Flask debug mode (do NOT use in production)",
    )
    parser.add_argument(
        "-V", "--version",
        action="version",
        version=f"%(prog)s {__version__}",
    )
    args = parser.parse_args(argv)

    log_path = Path(args.log_dir).resolve()
    if not log_path.is_dir():
        print(f"Error: {log_path} is not a directory", file=sys.stderr)
        sys.exit(1)

    sessions = discover_sessions(log_path)

    print(f"Copilot Session Log Viewer v{__version__}")
    print(f"Scanning: {log_path}")
    print(f"Found {len(sessions)} session(s)")
    for s in sessions:
        print(f"  - {s['summary']} ({s['id'][:8]}...)")
    print()
    print(f"Open http://{args.host}:{args.port} in your browser")
    print()

    app = create_app(log_path)
    app.run(host=args.host, port=args.port, debug=args.debug)


if __name__ == "__main__":
    main()
