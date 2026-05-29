# Kanban Studio MVP - Project Plan

Detailed roadmap for building the Project Management MVP with Next.js, FastAPI, SQLite, and OpenRouter AI.

---

## Part 1: Plan
- **Description**: Enrich this document with substeps, tests, and success criteria. Create `frontend/AGENTS.md` to describe the existing codebase.
- **Substeps Checklist**:
  - [x] Update `docs/PLAN.md` with detailed plans.
  - [x] Write `frontend/AGENTS.md` detailing Next.js layout, components, and Tailwind config.
- **Test Plan & Verification**:
  - Verify documents exist and are accurate.
- **Success Criteria**:
  - `docs/PLAN.md` contains 10 detailed parts.
  - `frontend/AGENTS.md` is populated.

## Part 2: Scaffolding
- **Description**: Set up the Docker environment, FastAPI backend, and startup/shutdown scripts.
- **Substeps Checklist**:
  - [x] Create `Dockerfile` (multi-stage: Node build -> Python runtime).
  - [x] Create `docker-compose.yml` linking `.env` and port `8000`.
  - [x] Create `backend/main.py` serving a basic API.
  - [x] Create `scripts/start.ps1`, `scripts/stop.ps1` for Windows.
  - [x] Create `scripts/start.sh`, `scripts/stop.sh` for Mac/Linux.
- **Test Plan & Verification**:
  - Run start scripts and verify Docker container starts successfully.
  - Query `http://localhost:8000/api/health` and verify `{"status": "ok"}` response.
  - Run stop scripts and verify Docker container is cleaned up.
- **Success Criteria**:
  - Single command startup works cross-platform.
  - FastAPI is running inside Docker.

## Part 3: Add in Frontend
- **Description**: Statically build the frontend and serve it from the FastAPI backend at `/`.
- **Substeps Checklist**:
  - [x] Update `frontend/next.config.ts` to output static files (`output: 'export'`).
  - [x] Modify `Dockerfile` to compile Next.js static build in build stage.
  - [x] Configure `backend/main.py` using `StaticFiles` to serve `frontend/out` at `/`.
  - [x] Implement path fallback on FastAPI to redirect unknown routes (excluding `/api/*`) to `index.html`.
- **Test Plan & Verification**:
  - Run start script and navigate to `http://localhost:8000/`.
  - Verify Kanban board page loads properly and style is correct.
- **Success Criteria**:
  - Frontend served natively by FastAPI without a separate node dev server.

## Part 4: Add in a fake user sign in experience
- **Description**: Build a login/logout mechanism using hardcoded credentials ("user" and "password") and JWT cookies.
- **Substeps Checklist**:
  - [x] Create `Login` screen in Next.js matching the design system colors.
  - [x] Add session authentication on the backend using JWT stored in HttpOnly cookie.
  - [x] Implement backend `/api/auth/login` and `/api/auth/logout` endpoints.
  - [x] Integrate login state in frontend, prompting for credentials if no active session.
- **Test Plan & Verification**:
  - Open `http://localhost:8000/` and verify redirect/overlay of login form.
  - Log in with invalid credentials (verify error message).
  - Log in with `user` / `password` (verify redirect to board).
  - Log out and verify login form displays again.
- **Success Criteria**:
  - Unauthenticated users cannot view the Kanban board.
  - Cookie validation secures backend routes.

## Part 5: Database modeling
- **Description**: Define the database tables and schemas in SQLite.
- **Substeps Checklist**:
  - [x] Design normalized tables: `users`, `columns`, `cards`.
  - [x] Save JSON schema definition to `docs/schema.json`.
  - [x] Write `docs/DATABASE.md` documenting schema fields and relationships.
- **Test Plan & Verification**:
  - Validate JSON schema file.
  - Verify SQLite DB generated correctly.
- **Success Criteria**:
  - Schema captures user columns, cards, card positions, and titles.

## Part 6: Backend
- **Description**: Implement database models, repository, and CRUD API routes to sync board state.
- **Substeps Checklist**:
  - [x] Configure SQLite and SQLAlchemy in `backend/database.py` and `backend/models.py`.
  - [x] Auto-create database schema on startup if file does not exist.
  - [x] Implement database seeding for new users with `initialData`.
  - [x] Create API routes to read/write columns and cards for the authenticated user.
  - [x] Write Python backend tests for database operations and API endpoints.
- **Test Plan & Verification**:
  - Run backend unit tests with pytest: `pytest backend/tests`.
  - Verify database file `pm.db` is created in docker volume.
- **Success Criteria**:
  - Full CRUD operations tested and passing.

## Part 7: Frontend + Backend
- **Description**: Connect the Next.js board component to the FastAPI board endpoints.
- **Substeps Checklist**:
  - [x] Implement client-side API client using `fetch`.
  - [x] Update board load handler to fetch columns and cards.
  - [x] Update drag-and-drop end handler to call backend re-order endpoint.
  - [x] Update column rename, card addition, and card deletion to sync with backend.
  - [x] Write end-to-end Playwright tests for frontend/backend integration.
- **Test Plan & Verification**:
  - Playwright test: `npm run test:e2e` inside frontend.
  - Manual check: Refresh board after edits and ensure changes persist.
- **Success Criteria**:
  - Drag-and-drop and edits persist upon reload.

## Part 8: AI connectivity
- **Description**: Set up LLM connection using OpenRouter API and `openai/gpt-oss-120b:free`.
- **Substeps Checklist**:
  - [x] Create `backend/ai.py` with OpenAI client wrapper.
  - [x] Read `OPENROUTER_API_KEY` from environment variables.
  - [x] Add `/api/ai/test` endpoint performing a simple "2+2" query.
- **Test Plan & Verification**:
  - Call `/api/ai/test` and verify response contains expected math answer.
- **Success Criteria**:
  - LLM client successfully connects and authenticates to OpenRouter.

## Part 9: LLM Board Updating
- **Description**: Implement Structured Outputs on the LLM to parse and perform modifications on the database.
- **Substeps Checklist**:
  - [x] Define Structured Output Pydantic schema: `chatResponse` (text), and `boardUpdate` (optional board JSON).
  - [x] Send system prompts containing current board state and conversation history to LLM.
  - [x] Parse JSON output from LLM.
  - [x] Implement database update routine to apply LLM board updates transactionally.
- **Test Plan & Verification**:
  - Unit test: Mock LLM structured response and verify database updates correctly.
- **Success Criteria**:
  - LLM can successfully create, edit, or move cards via structured JSON.

## Part 10: AI Sidebar Widget
- **Description**: Build chat sidebar widget on the frontend supporting conversational edits.
- **Substeps Checklist**:
  - [x] Design sliding panel/sidebar UI matching design system.
  - [x] Render chat history and message input.
  - [x] Implement chat request fetching with loading indicator.
  - [x] Add state event callback to refresh Kanban board if response contains board updates.
  - [x] Add E2E tests verifying conversation.
- **Test Plan & Verification**:
  - Verify chat sidebar opens/closes.
  - Send message: "Create a card called 'Write tests' in Backlog".
  - Verify card is created and visible without page refresh.
- **Success Criteria**:
  - Real-time UI synchronization upon AI modification.