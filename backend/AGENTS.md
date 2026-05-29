# Backend — Kanban Studio API

FastAPI application that serves the JSON API and the compiled Next.js frontend
from a single process. SQLite is the datastore (via SQLAlchemy); OpenRouter
powers the AI board assistant.

## Layout

| File | Responsibility |
|------|----------------|
| `main.py` | FastAPI app, route handlers, board read/write helpers, startup seeding, SPA static fallback |
| `database.py` | SQLAlchemy engine/session; SQLite at `/app/data/pm.db` (falls back to CWD outside Docker) |
| `models.py` | ORM models: `UserModel`, `ColumnModel`, `CardModel` (composite `(column_id, user_id)` FK, cascade deletes) |
| `schemas.py` | Pydantic request/response models (`BoardDataSchema`, `ChatRequest`, `ChatResponse`, …) |
| `auth.py` | JWT session cookies (`session_token`), bcrypt password hashing, `get_current_user` dependency |
| `ai.py` | OpenRouter client; `run_chat_query` (board edits) and `run_test_query` (connectivity check) |
| `test_api.py` | pytest API tests using a per-test in-memory DB via dependency override |

## Key behaviours

- **Auth:** `POST /api/auth/login` sets an HttpOnly JWT cookie; protected routes
  depend on `get_current_user`. The cookie is `Secure` only when `APP_ENV=production`.
- **Board persistence:** the board is stored per user. `POST /api/kanban` replaces
  the whole board atomically in `save_user_board` (delete + flush + re-insert in one
  transaction; rolls back on failure).
- **AI edits:** `POST /api/chat` sends the current board + conversation to the LLM,
  which returns `{ chatResponse, boardUpdate }`. A non-null, non-empty `boardUpdate`
  is validated and persisted; empty/invalid updates are discarded with a note.
- **Seeding:** on startup the default `user`/`password` account and a starter board
  are created if absent. `GET /api/kanban` also re-seeds an empty board.
- **Static serving:** unknown non-`/api` paths fall back to `static/index.html`
  (the Next.js export copied in by the Dockerfile).

## Environment variables

See `../.env.example`. `OPENROUTER_API_KEY` (required for AI), `JWT_SECRET`
(required when `APP_ENV=production`), `APP_ENV` (`development` | `production`).

## Tests

```bash
pytest backend/test_api.py        # from repo root, with PYTHONPATH=. (set in Docker)
```
