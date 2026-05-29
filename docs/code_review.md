# Code Review — Kanban Studio MVP

**Date:** 2026-05-29
**Reviewer:** Claude (Opus 4.8)
**Scope:** Full repository — backend (FastAPI/SQLAlchemy), frontend (Next.js/React), infra (Docker), tests.

## Summary

The project is a well-structured, functional MVP. All 10 plan parts are implemented and the test suite (6 frontend unit, 5 backend, 3 E2E) passes. The architecture (static Next.js export served by FastAPI, SQLite persistence, LLM board edits) is sound for its goals.

However, there are a handful of **correctness bugs**, **security issues**, and **performance/quality problems** that should be addressed before this moves beyond a demo. The most urgent are: a broken AI-test endpoint (missing function), debug `print` statements leaking data on every save, a non-atomic destructive save routine, an insecure default JWT secret, and a full-board POST fired on every keystroke during column rename.

Severity legend: 🔴 Critical · 🟠 High · 🟡 Medium · 🔵 Low / polish

---

## 🔴 Critical

### C1. `/api/ai/test` calls an undefined function
`backend/main.py:254-256` imports and calls `run_test_query`, but `backend/ai.py` only defines `run_chat_query`. The endpoint is wrapped in a try/except so it won't crash the server, but it will **always** return `{"status": "error", ...}`. This means PLAN Part 8's success criterion ("LLM client successfully connects") cannot actually be verified through this endpoint.

**Action:** Either implement `run_test_query()` in `ai.py` (a simple "2+2" completion as the plan describes) or remove the endpoint. No test covers this path, which is why it went unnoticed.

### C2. Debug `print` statements leak data and spam logs on every save
`backend/main.py:97-106` prints `user_id`, and **every card's id + user_id for all users in the DB**, on every single `save_user_board` call. This runs on every drag, rename, card add/delete, and AI edit.

**Action:** Delete all five `print("DEBUG: ...")` lines. If logging is wanted, use the `logging` module at `DEBUG` level (off by default).

---

## 🟠 High

### H1. `save_user_board` is destructive and not atomic
`backend/main.py:95-131` deletes all of a user's columns and cards, **commits**, then inserts the new state in a second transaction. The comment ("Commit the deletes first to guarantee SQLite primary keys are freed") indicates a workaround. If the insert loop raises (bad data, disk error, concurrent request), the user's board is left **wiped**. There is no rollback path.

**Action:** Perform delete + insert in a single transaction (one `commit()` at the end). The "free primary keys" problem is better solved by `flush()` mid-transaction or by an upsert/diff strategy instead of delete-all-reinsert. At minimum, wrap in try/except with `db.rollback()`.

### H2. Insecure default JWT secret
`backend/auth.py:9` falls back to a hardcoded secret (`"kanban-studio-mvp-super-secret-key-change-in-prod"`) when `JWT_SECRET` is unset. `docker-compose.yml` does **not** set `JWT_SECRET`, so the default is what actually runs. Anyone with this public repo can forge session cookies for any user.

**Action:** Generate `JWT_SECRET` at deploy time and pass it via `.env`/compose. Consider failing fast (raise on startup) if it's missing in a non-dev environment. Document the variable in an `.env.example`.

### H3. Column rename fires a full-board save on every keystroke
`KanbanColumn.tsx:42-47` binds `onChange` directly to `onRename`, which calls `saveBoard` (`KanbanBoard.tsx:127-138`). Typing a 10-character column name triggers 10 POSTs, each of which runs the full delete-all-reinsert in H1. This is wasteful and amplifies the H1 data-loss window.

**Action:** Save on blur (`onBlur`) or debounce the save (e.g. 500ms). Keep local state for the input value so typing stays responsive.

### H4. CORS allows all origins with credentials
`backend/main.py:157-163` sets `allow_origins=["*"]` together with `allow_credentials=True`. Browsers reject this combination, and more importantly the frontend is served **same-origin** from FastAPI, so the CORS middleware isn't needed at all.

**Action:** Remove the CORS middleware entirely, or restrict `allow_origins` to a known list if cross-origin access is ever required.

---

## 🟡 Medium

### M1. AI board updates can silently destroy data
`backend/main.py:234-242` takes whatever full board the LLM returns and overwrites the user's entire board via `save_user_board`. If the model omits cards/columns (a common LLM failure), they are permanently deleted with no confirmation or backup. `save_user_board` also silently skips `cardIds` that have no matching card entry (`main.py:120-121`), masking malformed responses.

**Action:** Consider a diff/merge approach, validate that the update is a superset-or-intentional-change, or at least snapshot the prior board so a bad AI edit can be undone. Log when `cardIds` reference missing cards rather than silently dropping them.

### M2. Side effects inside React state updaters
`KanbanBoard.tsx` calls `saveBoard(...)` inside the `setBoard((prev) => {...})` updater in `handleDragEnd`, `handleRenameColumn`, `handleAddCard`, `handleDeleteCard`. State updater functions should be pure; under React 18 StrictMode they can run twice, firing duplicate network requests.

**Action:** Compute `nextBoard` first, then call `setBoard(nextBoard)` and `saveBoard(nextBoard)` as separate statements outside the updater.

### M3. Pydantic v2 deprecation warnings
`backend/schemas.py:19,28` use the deprecated class-based `class Config: from_attributes = True`. Tests emit `PydanticDeprecatedSince20` warnings; this breaks in Pydantic v3.

**Action:** Replace with `model_config = ConfigDict(from_attributes=True)`. (Note: these schemas are currently built manually in `get_user_board`, not from ORM objects, so `from_attributes` may not even be needed — verify and remove if unused.)

### M4. `get_user_board` is O(columns × cards)
`backend/main.py:86` re-scans the full card list for each column to build `cardIds`. Fine at MVP scale, quadratic as boards grow.

**Action:** Build a `column_id -> [cards]` dict in one pass, preserving position order.

### M5. Two sources of truth for seed data
`INITIAL_DATA` in `backend/main.py:22-40` duplicates `initialData` in `frontend/src/lib/kanban.ts:18-72`. They can drift. The frontend copy is also imported into `KanbanBoard.tsx:20` but **never used** (the board initializes empty and fetches from the API).

**Action:** Remove the unused `initialData` import in `KanbanBoard.tsx`. Treat the backend as the single source of truth for seed data; keep the frontend type definitions only.

### M6. Fragile LLM JSON parsing instead of structured outputs
`backend/ai.py:42-54` extracts JSON via regex / first-`{`-to-last-`}`. PLAN Part 9 calls for "Structured Outputs," but this is prompt-coaxed JSON. It will fail on nested braces in card details or any prose the model adds.

**Action:** Use the OpenAI client's `response_format={"type": "json_object"}` (or JSON schema mode if the model supports it via OpenRouter) to get guaranteed-parseable output.

---

## 🔵 Low / Polish

- **L1.** `docker-compose.yml:1` — `version: '3.8'` is obsolete and emits a warning on every `docker-compose` invocation. Remove the line.
- **L2.** Inline imports scattered through `main.py` (`verify_password` at :171, `run_chat_query` at :231, `run_test_query` at :254) and `auth.py` (`import bcrypt` inside both functions). Move to module top for clarity and to surface import errors at load time (would have caught C1).
- **L3.** `backend/AGENTS.md` is still a placeholder ("This file should be updated…"). Fill it in or delete it.
- **L4.** No `.env.example`. Add one documenting `OPENROUTER_API_KEY` (required) and `JWT_SECRET` (recommended).
- **L5.** Backend tests run against the real persistent SQLite DB and mutate the seeded board, relying on manual restore (`test_api.py:73-75`). Use a per-test in-memory SQLite via a dependency-override fixture for isolation.
- **L6.** The frontend seeds the chat with an `assistant` greeting (`SidebarChat.tsx:17-22`) and sends it as the first message in the LLM history. Leading with an assistant turn is unusual and may confuse some models — filter it out before sending, or mark it client-only.
- **L7.** Cookie is set with `secure=False` (`main.py:179`). Correct for local HTTP, but must be `True` behind HTTPS in production — make it environment-driven.
- **L8.** Save failures are only `console.error`'d (`KanbanBoard.tsx`, `SidebarChat.tsx`). The UI and DB can silently diverge. Surface a toast/banner and consider rolling back optimistic state on failure.
- **L9.** Catch-all route returns a JSON `{"message": ...}` with a 200 when static assets are missing (`main.py:276`) instead of a 404. Minor, only hit if the frontend build is absent.
- **L10.** `err: any` in frontend catch blocks (`SidebarChat.tsx:72`, `Login.tsx:36`) — prefer `unknown` with narrowing for type safety.

---

## Suggested priority order

1. **C1, C2** — quick, high-impact (broken endpoint + data leak/log spam).
2. **H1, H2** — data-loss and auth-forgery risks.
3. **H3, H4** — performance and CORS correctness.
4. **M1–M6** — robustness and maintainability.
5. **L1–L10** — polish, can be batched.

## What's done well

- Clean separation of concerns (auth / models / schemas / ai / routes).
- The drag-and-drop collision detection (`KanbanBoard.tsx:23-49`) thoughtfully handles empty columns with a layered fallback.
- `moveCard` (`lib/kanban.ts:84-162`) is pure, well-factored, and unit-tested for the tricky reordering cases.
- Multi-stage Dockerfile keeps the runtime image lean; `uv` for fast installs.
- Composite FK on `(column_id, user_id)` with cascade deletes is a nice touch for per-user data integrity.
- Good test coverage across all three layers for an MVP.
