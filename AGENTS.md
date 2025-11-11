# Repository Guidelines

## Project Structure & Module Organization

All automation lives at the repo root for quick invocation. `jpt_menu.py` is the interactive launcher that shells out to the task-specific scripts (`jpt.py`, `jira_*_overview.py`, `jira_*_sanity_check.py`, `jpt_forecast.py`). Each script has a matching Markdown brief (`jpt.md`, `jira_todo_notify.md`, etc.) describing inputs and outputs. Presentation templates (`sprint-template.pptx`) and generated decks (`S_A Sprint*.pptx`) stay in the same directory, alongside auxiliary assets such as `smtp_settings.env` and `sprint_forecast_history.xlsx`. Dependency pins live in `requirements.txt`.

## Build, Test, and Development Commands

- `python3 -m venv .venv && source .venv/bin/activate` – create/enter an isolated interpreter (Python 3.7+).
- `pip install -r requirements.txt` – install Jira, SMTP, and PowerPoint libraries.
- `python jpt_menu.py` – open the unified menu for presentations, sanity checks, and notifications.
- `python <script>.py --help` – most scripts expose flags (dry-run, output path, filters); run directly when iterating.

## Coding Style & Naming Conventions

Follow PEP 8 with 4-space indentation and `snake_case` for functions, `PascalCase` for classes, and SCREAMING_SNAKE for config constants (e.g., `JT_JIRA_URL`). Keep modules cohesive: Jira API helpers near the top, rendering/email helpers grouped beneath. Use f-strings for readability, type hints when adding new functions, and log meaningful status messages rather than bare `print`. Markdown docs use sentence-case headings and embed example commands.

## Testing Guidelines

No formal test suite exists; rely on targeted script runs. When adding features, create lightweight smoke scripts (e.g., `python jpt.py --sprint "Sprint 42"` pointing at a staging board) and capture before/after artifacts. Prefer deterministic fixtures by exporting Jira responses to JSON and replaying in helper functions. If you add automated tests, place them in `tests/` and name files `test_<module>.py`, then run with `pytest` and document the command here.

## Commit & Pull Request Guidelines

Commit history favors short, imperative summaries (“change labels and ordering”). Keep messages under 60 characters, optionally adding detail in the body when touching multiple scripts. PRs should include: scope summary, scripts touched, manual test evidence (screenshots of PPT or CLI output), and links to Jira issues or sprint tickets. Mention any secret-handling steps (e.g., `.jira_environment`, `smtp_settings.env`) so reviewers can reproduce safely.

## Security & Configuration Tips

Never commit `.jira_environment`, SMTP credentials, or certificates; use local `.env` files referenced via `REQUESTS_CA_BUNDLE` for Zscaler or similar proxies. When sharing decks, scrub sprint names that reveal client data. If you must check in example configs, redact tokens and suffix the filename with `.example`.

## Agent Sync Notes

`jira_config.py` owns `.jira_environment` parsing—always import `load_jira_env()` (or `get_jira_setting()`) instead of copying parser snippets so new keys propagate everywhere. After pulling fresh changes, run `python - <<'PY' import jira_config,jpt,jpt_forecast,jira_todo_notify,jira_refine_sanity_check,jira_ready_sanity_check,jira_on_hold_overview,jira_blocked_overview; print('import ok') PY` to confirm every script still loads credentials before doing deeper work. Keep this file and `README.md` in sync whenever workflows or dependencies change so the next agent has an accurate single source of truth.
