# copilot-log-viewer

A local web UI for browsing and understanding **GitHub Copilot agent** session logs.

Copilot's agent mode produces rich session logs (JSONL events, workspace metadata,
rewind snapshots). This tool turns those raw files into a readable, interactive
timeline so you can review what happened — the user prompts, assistant reasoning,
tool calls, sub-agent activity, errors, and file snapshots — all in one place.

![Python 3.10+](https://img.shields.io/badge/python-3.10%2B-blue)
![License: MIT](https://img.shields.io/badge/license-MIT-green)

---

## Features

- **Session index** — lists every session found in a directory, with summary, repo,
  branch, and timestamps.
- **Interactive timeline** — color-coded conversation view with:
  - User messages (with file attachments)
  - Assistant responses (rendered Markdown, expandable reasoning)
  - Tool calls & results (expandable arguments / output)
  - Sub-agent launches & completions
  - Errors and system notifications
- **Statistics sidebar** — message counts, token usage, tool breakdown with visual
  bars, and rewind snapshot history.
- **Filters** — quickly toggle between event types (User / Assistant / Tools /
  Sub-Agents / Errors).
- **JSON API** — programmatic access at `/api/sessions` and
  `/api/session/<id>/events`.
- **Security** — UUID & backup-hash validation, path-traversal protection,
  Content-Security-Policy headers, localhost-only by default.

## Quick start

### Install from source

```bash
git clone https://github.com/l-teles/copilot-log-viewer.git
cd copilot-log-viewer
pip install .
```

### Install from PyPI (once published)

```bash
pip install copilot-log-viewer
```

### Run

```bash
# Point it at a directory containing Copilot session folders
copilot-log-viewer /path/to/session-logs

# Or use the module directly
python -m copilot_log_viewer /path/to/session-logs
```

Then open **http://127.0.0.1:5000** in your browser.

### Options

```
usage: copilot-log-viewer [-h] [-p PORT] [--host HOST] [--debug] [-V] [log_dir]

positional arguments:
  log_dir               Directory containing Copilot session log folders (default: .)

options:
  -p, --port PORT       Port to listen on (default: 5000)
  --host HOST           Host to bind to (default: 127.0.0.1)
  --debug               Run in Flask debug mode (local development only)
  -V, --version         Show version and exit
```

### Environment variable

You can also set the log directory via the `COPILOT_LOG_DIR` environment variable:

```bash
export COPILOT_LOG_DIR=/path/to/session-logs
copilot-log-viewer
```

## Expected directory layout

The tool expects a directory containing one or more session folders. Each session
folder is a UUID-named directory produced by GitHub Copilot's agent mode:

```
session-logs/
├── 4e71aaa0-f131-41fd-aeee-8bcaa5efb315/
│   ├── workspace.yaml          # Session metadata
│   ├── events.jsonl            # Conversation event stream
│   ├── checkpoints/
│   │   └── index.md
│   └── rewind-snapshots/
│       ├── index.json          # Snapshot manifest
│       └── backups/            # File content snapshots
│           ├── ff627b50b0554488-1773312027139
│           └── ...
├── 8b3c9d7d-60f7-4e4c-a442-eb2ee7ee68e2/
│   ├── workspace.yaml
│   ├── events.jsonl
│   └── ...
└── ...
```

## Development

```bash
# Install with dev dependencies
pip install -e ".[dev]"

# Lint
ruff check src/ tests/

# Test
pytest
```

## Security

- **Localhost only** — binds to `127.0.0.1` by default; never expose to the public
  internet without authentication.
- **Input validation** — session IDs must be valid UUIDs; backup hashes are validated
  against a strict pattern.
- **Path-traversal protection** — resolved file paths are verified to stay within the
  configured log directory.
- **Security headers** — `X-Content-Type-Options`, `X-Frame-Options`,
  `Referrer-Policy`, and `Content-Security-Policy` are set on every response.
- **No debug in production** — debug mode is off by default and must be explicitly
  enabled via `--debug`.

## License

[MIT](LICENSE)
