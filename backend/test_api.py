import uuid

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from backend.main import app
from backend.database import Base, get_db
from backend.models import UserModel
from backend.auth import hash_password

# A dedicated in-memory SQLite database for tests. StaticPool keeps a single
# shared connection so every session in a test sees the same data, fully
# isolated from the real pm.db.
engine = create_engine(
    "sqlite://",
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def override_get_db():
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()


client = TestClient(app)


@pytest.fixture(autouse=True)
def fresh_database():
    """Recreate schema and seed the default user before each test; clean up after."""
    Base.metadata.create_all(bind=engine)
    db = TestingSessionLocal()
    try:
        db.add(UserModel(username="user", password_hash=hash_password("password")))
        db.commit()
    finally:
        db.close()

    app.dependency_overrides[get_db] = override_get_db
    client.cookies.clear()
    yield
    app.dependency_overrides.clear()
    Base.metadata.drop_all(bind=engine)


def test_health_endpoint():
    response = client.get("/api/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"


def test_unauthorized_endpoints():
    response = client.get("/api/auth/me")
    assert response.status_code == 401

    response = client.get("/api/kanban")
    assert response.status_code == 401


def test_login_flow():
    # Invalid login
    response = client.post(
        "/api/auth/login",
        json={"username": "user", "password": "wrong_password"},
    )
    assert response.status_code == 401

    # Valid login
    response = client.post(
        "/api/auth/login",
        json={"username": "user", "password": "password"},
    )
    assert response.status_code == 200
    assert response.json()["status"] == "success"

    # Verify cookie was set
    assert "session_token" in response.cookies


def test_kanban_retrieval_and_update():
    # Login (cookie persists on the client for subsequent requests)
    login_response = client.post(
        "/api/auth/login",
        json={"username": "user", "password": "password"},
    )
    assert login_response.status_code == 200

    # Retrieve board (auto-seeded on first access)
    board_response = client.get("/api/kanban")
    assert board_response.status_code == 200
    board_data = board_response.json()
    assert "columns" in board_data
    assert "cards" in board_data
    assert len(board_data["columns"]) == 5

    # Modify board (rename first column)
    board_data["columns"][0]["title"] = "Test Backlog Rename"

    update_response = client.post("/api/kanban", json=board_data)
    assert update_response.status_code == 200
    assert update_response.json()["status"] == "success"

    # Retrieve again to verify persistence
    verify_response = client.get("/api/kanban")
    assert verify_response.status_code == 200
    assert verify_response.json()["columns"][0]["title"] == "Test Backlog Rename"


def test_chat_endpoint(monkeypatch):
    # Generate a unique card ID for the mock run
    generated_card_id = f"card-test-{uuid.uuid4().hex[:6]}"

    def mock_run_chat_query(messages, current_board):
        updated_board = {
            "columns": [dict(c) for c in current_board["columns"]],
            "cards": dict(current_board["cards"]),
        }
        updated_board["cards"][generated_card_id] = {
            "id": generated_card_id,
            "title": "AI Card",
            "details": "Created by AI",
        }
        updated_board["columns"][0] = dict(updated_board["columns"][0])
        updated_board["columns"][0]["cardIds"] = [
            *updated_board["columns"][0]["cardIds"],
            generated_card_id,
        ]
        return {
            "chatResponse": "I created a card for you.",
            "boardUpdate": updated_board,
        }

    # main.py imports run_chat_query at module level, so patch it there.
    monkeypatch.setattr("backend.main.run_chat_query", mock_run_chat_query)

    # Login
    login_response = client.post(
        "/api/auth/login",
        json={"username": "user", "password": "password"},
    )
    assert login_response.status_code == 200

    # Get current board
    board_response = client.get("/api/kanban")
    assert board_response.status_code == 200
    board_data = board_response.json()

    # Send chat query
    chat_payload = {
        "messages": [{"role": "user", "content": "Add AI Card to Backlog"}],
        "currentBoard": board_data,
    }
    chat_response = client.post("/api/chat", json=chat_payload)
    assert chat_response.status_code == 200
    res_data = chat_response.json()
    assert res_data["chatResponse"] == "I created a card for you."
    assert "boardUpdate" in res_data
    assert generated_card_id in res_data["boardUpdate"]["cards"]

    # Verify the card was transactionally saved to the database
    board_response2 = client.get("/api/kanban")
    assert board_response2.status_code == 200
    assert generated_card_id in board_response2.json()["cards"]
