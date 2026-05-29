import os
import uuid
import logging
from typing import Optional
from contextlib import asynccontextmanager
from fastapi import FastAPI, Depends, Response, HTTPException, status
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from backend.database import Base, engine, get_db
from backend.models import UserModel, ColumnModel, CardModel
from backend.schemas import (
    LoginRequest,
    UserResponse,
    BoardDataSchema,
    ColumnSchema,
    CardSchema,
    ChatRequest,
    ChatResponse
)
from backend.auth import (
    create_access_token,
    get_current_user,
    hash_password,
    verify_password,
)
from backend.ai import run_chat_query, run_test_query

logger = logging.getLogger(__name__)

# Cookies are only flagged Secure (HTTPS-only) in production so local HTTP works.
APP_ENV = os.getenv("APP_ENV", "development").lower()
COOKIE_SECURE = APP_ENV == "production"

# Initial seed data structure
INITIAL_DATA = {
    "columns": [
        { "id": "col-backlog", "title": "Backlog", "cardIds": ["card-1", "card-2"] },
        { "id": "col-discovery", "title": "Discovery", "cardIds": ["card-3"] },
        { "id": "col-progress", "title": "In Progress", "cardIds": ["card-4", "card-5"] },
        { "id": "col-review", "title": "Review", "cardIds": ["card-6"] },
        { "id": "col-done", "title": "Done", "cardIds": ["card-7", "card-8"] }
    ],
    "cards": {
        "card-1": { "id": "card-1", "title": "Align roadmap themes", "details": "Draft quarterly themes with impact statements and metrics." },
        "card-2": { "id": "card-2", "title": "Gather customer signals", "details": "Review support tags, sales notes, and churn feedback." },
        "card-3": { "id": "card-3", "title": "Prototype analytics view", "details": "Sketch initial dashboard layout and key drill-downs." },
        "card-4": { "id": "card-4", "title": "Refine status language", "details": "Standardize column labels and tone across the board." },
        "card-5": { "id": "card-5", "title": "Design card layout", "details": "Add hierarchy and spacing for scanning dense lists." },
        "card-6": { "id": "card-6", "title": "QA micro-interactions", "details": "Verify hover, focus, and loading states." },
        "card-7": { "id": "card-7", "title": "Ship marketing page", "details": "Final copy approved and asset pack delivered." },
        "card-8": { "id": "card-8", "title": "Close onboarding sprint", "details": "Document release notes and share internally." }
    }
}

def seed_user_board(db: Session, user_id: int):
    # Seed columns
    for idx, col in enumerate(INITIAL_DATA["columns"]):
        db_col = ColumnModel(
            id=col["id"],
            user_id=user_id,
            title=col["title"],
            position=idx
        )
        db.add(db_col)
        
        # Seed cards belonging to this column
        for c_idx, card_id in enumerate(col["cardIds"]):
            card_info = INITIAL_DATA["cards"][card_id]
            db_card = CardModel(
                id=card_id,
                column_id=col["id"],
                user_id=user_id,
                title=card_info["title"],
                details=card_info["details"],
                position=c_idx
            )
            db.add(db_card)
    db.commit()

def get_user_board(db: Session, user_id: int) -> BoardDataSchema:
    # Get columns ordered by position
    db_cols = db.query(ColumnModel).filter(ColumnModel.user_id == user_id).order_by(ColumnModel.position).all()
    
    # Get cards ordered by position
    db_cards = db.query(CardModel).filter(CardModel.user_id == user_id).order_by(CardModel.position).all()

    # Single pass: build the cards dict and group card ids by column (preserving order)
    cards_dict = {}
    card_ids_by_column: dict[str, list[str]] = {col.id: [] for col in db_cols}
    for card in db_cards:
        cards_dict[card.id] = CardSchema(
            id=card.id,
            title=card.title,
            details=card.details
        )
        card_ids_by_column.setdefault(card.column_id, []).append(card.id)

    columns_list = [
        ColumnSchema(id=col.id, title=col.title, cardIds=card_ids_by_column.get(col.id, []))
        for col in db_cols
    ]

    return BoardDataSchema(columns=columns_list, cards=cards_dict)

def save_user_board(db: Session, user_id: int, board_data: BoardDataSchema):
    """Replace the user's board atomically.

    The delete + re-insert happen in a single transaction: flush() frees the
    SQLite primary keys mid-transaction (so reused column/card ids don't collide)
    while deferring the commit, and any failure rolls back so the board is never
    left in a wiped or partial state.
    """
    try:
        # Clear existing board state (not yet committed)
        db.query(CardModel).filter(CardModel.user_id == user_id).delete()
        db.query(ColumnModel).filter(ColumnModel.user_id == user_id).delete()
        db.flush()  # apply the deletes so reused ids are free, without committing

        # Insert new columns and cards
        for idx, col in enumerate(board_data.columns):
            db_col = ColumnModel(
                id=col.id,
                user_id=user_id,
                title=col.title,
                position=idx
            )
            db.add(db_col)

            # Save cards of this column
            for c_idx, card_id in enumerate(col.cardIds):
                card_info = board_data.cards.get(card_id)
                if card_info:
                    db_card = CardModel(
                        id=card_id,
                        column_id=col.id,
                        user_id=user_id,
                        title=card_info.title,
                        details=card_info.details,
                        position=c_idx
                    )
                    db.add(db_card)
                else:
                    # cardId referenced by a column but absent from the cards map —
                    # skip it but surface the inconsistency rather than failing silently.
                    logger.warning(
                        "Dropping card id %r in column %r: no matching card data (user_id=%s)",
                        card_id, col.id, user_id,
                    )
        db.commit()
    except Exception:
        db.rollback()
        raise

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Create tables
    Base.metadata.create_all(bind=engine)
    
    # Seed default user if not exists
    db = next(get_db())
    try:
        default_user = db.query(UserModel).filter(UserModel.username == "user").first()
        if not default_user:
            hashed = hash_password("password")
            new_user = UserModel(username="user", password_hash=hashed)
            db.add(new_user)
            db.commit()
            db.refresh(new_user)
            seed_user_board(db, new_user.id)
    finally:
        db.close()
        
    yield

app = FastAPI(title="Kanban Studio API", lifespan=lifespan)

# The frontend is served same-origin from this app, so no CORS middleware is needed.

# Auth routes
@app.post("/api/auth/login")
async def login(credentials: LoginRequest, response: Response, db: Session = Depends(get_db)):
    db_user = db.query(UserModel).filter(UserModel.username == credentials.username).first()

    if db_user and verify_password(credentials.password, db_user.password_hash):
        token = create_access_token(data={"sub": credentials.username})
        response.set_cookie(
            key="session_token",
            value=token,
            httponly=True,
            samesite="lax",
            secure=COOKIE_SECURE,
            max_age=86400
        )
        return {"status": "success", "username": credentials.username}

    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Incorrect username or password"
    )

@app.post("/api/auth/logout")
async def logout(response: Response):
    response.delete_cookie("session_token")
    return {"status": "success", "message": "Logged out successfully"}

@app.get("/api/auth/me", response_model=UserResponse)
async def get_me(username: str = Depends(get_current_user)):
    return {"username": username}

# Kanban CRUD routes
@app.get("/api/kanban", response_model=BoardDataSchema)
async def get_kanban(username: str = Depends(get_current_user), db: Session = Depends(get_db)):
    user = db.query(UserModel).filter(UserModel.username == username).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
        
    # Get columns count
    db_cols_count = db.query(ColumnModel).filter(ColumnModel.user_id == user.id).count()
    if db_cols_count == 0:
        seed_user_board(db, user.id)
        
    return get_user_board(db, user.id)

@app.post("/api/kanban")
async def update_kanban(board_data: BoardDataSchema, username: str = Depends(get_current_user), db: Session = Depends(get_db)):
    user = db.query(UserModel).filter(UserModel.username == username).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
        
    save_user_board(db, user.id, board_data)
    return {"status": "success", "message": "Kanban board updated successfully"}

# --- AI action application ---------------------------------------------------
# The LLM returns a short list of actions rather than the whole board. We apply
# them server-side to the authoritative board, which is far fewer output tokens
# (so much faster) and can't silently drop unrelated cards/columns.

def _new_id(prefix: str) -> str:
    return f"{prefix}-{uuid.uuid4().hex[:8]}"


def _resolve_column(board: dict, ref) -> Optional[dict]:
    """Find a column by id, then by case-insensitive title."""
    if ref is None:
        return None
    ref_str = str(ref).strip()
    for col in board["columns"]:
        if col["id"] == ref_str:
            return col
    for col in board["columns"]:
        if col["title"].strip().lower() == ref_str.lower():
            return col
    return None


def _resolve_card_id(board: dict, ref) -> Optional[str]:
    """Find a card id by id, then by case-insensitive title."""
    if ref is None:
        return None
    ref_str = str(ref).strip()
    if ref_str in board["cards"]:
        return ref_str
    for card_id, card in board["cards"].items():
        if card["title"].strip().lower() == ref_str.lower():
            return card_id
    return None


def _remove_card_from_columns(board: dict, card_id: str):
    for col in board["columns"]:
        if card_id in col["cardIds"]:
            col["cardIds"].remove(card_id)


def _insert_card(column: dict, card_id: str, position):
    if isinstance(position, int) and 0 <= position <= len(column["cardIds"]):
        column["cardIds"].insert(position, card_id)
    else:
        column["cardIds"].append(card_id)


def apply_actions(board: dict, actions: list) -> list[str]:
    """Apply a list of AI actions to `board` in place. Returns warnings for any
    action that could not be applied (unknown type, unresolved target, etc.)."""
    warnings: list[str] = []

    for action in actions:
        if not isinstance(action, dict):
            warnings.append(f"ignored non-object action: {action!r}")
            continue
        atype = action.get("type")

        if atype == "add_card":
            col = _resolve_column(board, action.get("column"))
            if not col:
                warnings.append(f"add_card: column {action.get('column')!r} not found")
                continue
            card_id = _new_id("card")
            board["cards"][card_id] = {
                "id": card_id,
                "title": action.get("title") or "Untitled",
                "details": action.get("details") or "No details yet.",
            }
            _insert_card(col, card_id, action.get("position"))

        elif atype == "edit_card":
            card_id = _resolve_card_id(board, action.get("card"))
            if not card_id:
                warnings.append(f"edit_card: card {action.get('card')!r} not found")
                continue
            if action.get("title") is not None:
                board["cards"][card_id]["title"] = action["title"]
            if action.get("details") is not None:
                board["cards"][card_id]["details"] = action["details"]

        elif atype == "delete_card":
            card_id = _resolve_card_id(board, action.get("card"))
            if not card_id:
                warnings.append(f"delete_card: card {action.get('card')!r} not found")
                continue
            board["cards"].pop(card_id, None)
            _remove_card_from_columns(board, card_id)

        elif atype == "move_card":
            card_id = _resolve_card_id(board, action.get("card"))
            target = _resolve_column(board, action.get("toColumn") or action.get("column"))
            if not card_id or not target:
                warnings.append(f"move_card: card {action.get('card')!r} or target column not found")
                continue
            _remove_card_from_columns(board, card_id)
            _insert_card(target, card_id, action.get("position"))

        elif atype == "rename_column":
            col = _resolve_column(board, action.get("column"))
            if not col:
                warnings.append(f"rename_column: column {action.get('column')!r} not found")
                continue
            if action.get("title") is not None:
                col["title"] = action["title"]

        elif atype == "add_column":
            new_id = _new_id("col")
            board["columns"].append({
                "id": new_id,
                "title": action.get("title") or "New Column",
                "cardIds": [],
            })

        elif atype == "delete_column":
            col = _resolve_column(board, action.get("column"))
            if not col:
                warnings.append(f"delete_column: column {action.get('column')!r} not found")
                continue
            for card_id in list(col["cardIds"]):
                board["cards"].pop(card_id, None)
            board["columns"] = [c for c in board["columns"] if c["id"] != col["id"]]

        else:
            warnings.append(f"unknown action type: {atype!r}")

    return warnings


# AI Chat route
@app.post("/api/chat", response_model=ChatResponse)
async def chat(chat_request: ChatRequest, username: str = Depends(get_current_user), db: Session = Depends(get_db)):
    user = db.query(UserModel).filter(UserModel.username == username).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    messages_list = [{"role": msg.role, "content": msg.content} for msg in chat_request.messages]

    # Use the database board as the authoritative base for both the prompt and
    # the action application, so the model and the server agree on state.
    base_board = get_user_board(db, user.id).model_dump()

    result = run_chat_query(messages_list, base_board)
    chat_response = result.get("chatResponse") or "Done."
    actions = result.get("actions") or []

    board_update = None
    if actions:
        warnings = apply_actions(base_board, actions)
        if warnings:
            logger.info("AI action warnings (user_id=%s): %s", user.id, warnings)
        try:
            validated_board = BoardDataSchema(**base_board)
            if not validated_board.columns:
                raise ValueError("refusing to apply changes that leave no columns")
            save_user_board(db, user.id, validated_board)
            board_update = get_user_board(db, user.id)
        except Exception as e:
            logger.warning("Discarding invalid AI board update (user_id=%s): %s", user.id, e)
            chat_response += f" (Note: I tried to update the board, but the result was invalid: {str(e)})"

    return {"chatResponse": chat_response, "boardUpdate": board_update}

# Health route
@app.get("/api/health")
async def health_check():
    return {"status": "ok", "message": "Kanban Studio API is running"}

# AI connectivity test route
@app.get("/api/ai/test")
async def test_ai_connectivity():
    try:
        res = run_test_query()
        return {"status": "success", "response": res}
    except Exception as e:
        return {"status": "error", "response": str(e)}

# SPA Catch-all and Static file serving route
@app.get("/{path:path}")
async def serve_static_or_fallback(path: str):
    static_dir = os.path.join(os.path.dirname(__file__), "static")

    # Check if a specific file is requested and exists
    file_path = os.path.join(static_dir, path)
    if path and os.path.isfile(file_path):
        return FileResponse(file_path)

    # Fallback to index.html for client-side routing
    index_file = os.path.join(static_dir, "index.html")
    if os.path.exists(index_file):
        return FileResponse(index_file)

    raise HTTPException(status_code=404, detail="Static assets not found. Build the frontend.")
