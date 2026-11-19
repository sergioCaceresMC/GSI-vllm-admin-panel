# Repository Guidelines

## Project Structure

- `main.py` assembles FastAPI. In `src/vllm_admin/`, `api.py` defines HTTP routes, `application.py` handles operations, and `adapters.py` integrates with the host.
- `static/` contains dashboard HTML, CSS, and JavaScript modules. Update it alongside any API response changes. Keep new dashboard text in Spanish to match the existing UI.
- `start-vllm.py` reads `/etc/vllm-admin/settings.json` and launches vLLM from its separate environment.
- `src/vllm_admin/__init__.py` backs the packaged CLI, which currently prints a greeting. The dashboard entry point is `main:app`.

## Build and Run

Run these commands from the repository root so the app can find the dashboard:

- `uv sync --locked` installs the panel dependencies from `uv.lock`. The repository pins Python 3.10.
- `uv run uvicorn main:app --host 127.0.0.1 --port 8080` starts the dashboard for local development.
- `uv build` builds the Python package into `dist/`.

## Coding Style

Use four spaces in Python, `snake_case` for functions and fields, `PascalCase` for Pydantic models, and `UPPER_CASE` for module constants. Follow the surrounding HTML and JavaScript indentation and use `camelCase` for JavaScript functions. The repository has no configured formatter or linter.

## Verification

Run `uv run python -m unittest discover -s tests` for API tests. Tests mock host integrations. There is no coverage threshold. Run `uv run python -m py_compile main.py start-vllm.py` for syntax and `uv run python -c 'import main'` for imports. Open the dashboard and use `curl -i http://127.0.0.1:8080/api/metrics` to smoke-test a read-only endpoint. Verify service controls, configuration writes, and GPU metrics on a host configured as described in `README.md`. Use systemd for autostart status and the vLLM `/health` endpoint for model readiness.

## Commits and Pull Requests

Use short, imperative Conventional Commit subjects such as `fix(metrics): handle missing GPU data`. Group related changes in one commit. In pull requests, describe the behavior change and checks performed, link an issue when available, and include a screenshot for visible dashboard changes.

## Deployment Configuration

Keep the unauthenticated dashboard bound to loopback. Preserve the restricted sudo commands and validated configuration helper documented in `README.md`. Keep credentials and host-specific configuration out of commits.
