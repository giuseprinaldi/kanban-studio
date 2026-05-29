import os
import logging
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

# AI Chat route
@app.post("/api/chat", response_model=ChatResponse)
async def chat(chat_request: ChatRequest, username: str = Depends(get_current_user), db: Session = Depends(get_db)):
    user = db.query(UserModel).filter(UserModel.username == username).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
        
    messages_list = [{"role": msg.role, "content": msg.content} for msg in chat_request.messages]
    current_board_dict = chat_request.currentBoard.model_dump()

    result = run_chat_query(messages_list, current_board_dict)

    board_update = result.get("boardUpdate")
    if board_update:
        try:
            validated_board = BoardDataSchema(**board_update)
            # Guard against an LLM wiping the board: a board with no columns is
            # almost certainly a bad response, not an intentional "delete everything".
            if not validated_board.columns:
                raise ValueError("refusing to apply a board update with no columns")
            save_user_board(db, user.id, validated_board)
            result["boardUpdate"] = get_user_board(db, user.id)
        except Exception as e:
            logger.warning("Discarding invalid AI board update (user_id=%s): %s", user.id, e)
            result["boardUpdate"] = None
            result["chatResponse"] += f" (Note: I tried to update the board, but the structure was invalid: {str(e)})"

    return result

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
