# nicegui-diagnostics demo

A live documentation page that dogfoods the diagnostics module.

## Run it

```bash
cd nicegui-diagnostics
pip install -e .
python demo/main.py
```

Then open <http://localhost:8081> (see `demo/main.py` for the source of truth).

Or via Docker Compose:

```bash
docker compose up --build
```

Then open <http://localhost:8085>

## What it shows

- **Left column** — Documentation: what each probe does, quick-start guide, install parameters
- **Right column** — Live demo: this app's own diagnostics, refreshed every 2 seconds
- The `/_nicegui/diagnostics` endpoint is live and queryable
- The stack dump server is running on port 9999 (configured via `stack_dump_port=9999` in `demo/main.py`)

This app *is* the documentation. It uses `nicegui_diagnostics.install()` to
instrument itself, then displays its own diagnostic data.
