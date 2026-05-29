# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

**Kanban Studio** — a single-user project management app with a drag-and-drop Kanban board, JWT authentication, SQLite persistence, and an AI sidebar chat that can modify the board via natural language. Built as a Next.js static export served by a FastAPI backend, containerized with Docker.

## Running the App

```powershell
# Start (Windows)
.\scripts\start.ps1        # runs: docker-compose up --build -d

# Stop
.\scripts\stop.ps1         # runs: docker-compose down
```

```sh
# Start (Mac/Linux)
./scripts/start.sh
./scripts/stop.sh
```

App runs at **http://localhost:8000**. Default credentials: `user` / `password`.

Requires a `.env` file at the project root:
```
OPENROUTER_API_KEY=<your key>
```

## Development Workflow

The app is designed to run inside Docker. For local iteration:

```bash
# Backend (from backend/)
pip install -r requirements.txt
uvicorn main:app --reload --port 8000

# Frontend (from frontend/)
npm install
npm run dev          # Next.js dev server on :3000 (not integrated with backend)
npm run build        # Static export to frontend/out/ (copied to backend/static/ by Docker)
```

## Testing

```bash
# Frontend unit tests (Vitest)
cd frontend && npm run test:unit

# Run a single unit test file
cd frontend && npx vitest src/components/KanbanBoard.test.tsx

# E2E tests (Playwright) — requires app running at http://127.0.0.1:8000
cd frontend && npm run test:e2e

# Backend tests (pytest)
cd backend && pytest test_api.py
```

## Architecture

### Request Flow

```
Browser → FastAPI (port 8000)
         ├── /api/*          → Python route handlers
         └── /{path}         → Serves Next.js static files from backend/static/
```

The frontend is a **Next.js static export** (`output: 'export'`). Docker builds it and copies `frontend/out/` into `backend/static/`. FastAPI serves these files as a catch-all SPA fallback.

### Backend (`backend/`)

| File | Purpose |
|------|---------|
| `main.py` | FastAPI app, all route definitions, DB seeding on startup |
| `models.py` | SQLAlchemy ORM: `UserModel`, `ColumnModel`, `CardModel` |
| `database.py` | SQLite at `/app/data/pm.db`; `SessionLocal`, `Base` |
| `auth.py` | JWT via `session_token` cookie (24h expiry), bcrypt hashing |
| `schemas.py` | Pydantic: `BoardDataSchema`, `ChatRequest/Response` |
| `ai.py` | OpenRouter integration (`openai/gpt-oss-120b:free`); parses structured JSON from LLM |

The board is stored **denormalized per user** — a single `POST /api/kanban` replaces the entire board state. Column and card positions are stored as integers.

### Frontend (`frontend/src/`)

| Location | Purpose |
|----------|---------|
| `app/page.tsx` | Root: auth check → `Login` or `KanbanBoard` |
| `components/KanbanBoard.tsx` | Main state container; drag-drop orchestration; sidebar toggle |
| `components/KanbanColumn.tsx` | Column with rename and card list |
| `components/KanbanCard.tsx` | Draggable card |
| `components/SidebarChat.tsx` | Floating AI chat; sends current board state + user message; applies `boardUpdate` if returned |
| `components/Login.tsx` | Login form |
| `lib/kanban.ts` | `BoardData` type, `moveCard()`, `createId()` |

**dnd-kit** handles drag-and-drop. The `SidebarChat` sends the full board snapshot with each message and receives back a `chatResponse` string plus an optional `boardUpdate` object — the frontend merges this to update board state.

### AI Chat Protocol

`POST /api/chat` receives `{ message, boardData }`. The backend sends the current board to the LLM with a system prompt instructing it to return:

```json
{ "chatResponse": "...", "boardUpdate": { /* optional full board state */ } }
```

`ai.py` strips markdown code fences before parsing. If `boardUpdate` is present, the frontend replaces its board state and persists to the backend.

## Design System

CSS variables defined in `frontend/src/app/globals.css`:
- `--accent`: `#ecad0a` (yellow)
- `--primary`: `#209dd7` (blue)
- `--secondary`: `#753991` (purple)
- `--navy`: `#032147`
- `--surface` / `--surface-strong`: `#f7f8fb` / `#ffffff`
