from typing import List, Dict, Optional
from pydantic import BaseModel

# Auth schemas
class LoginRequest(BaseModel):
    username: str
    password: str

class UserResponse(BaseModel):
    username: str


# Kanban schemas
class CardSchema(BaseModel):
    id: str
    title: str
    details: str


class ColumnSchema(BaseModel):
    id: str
    title: str
    cardIds: List[str]


class BoardDataSchema(BaseModel):
    columns: List[ColumnSchema]
    cards: Dict[str, CardSchema]


class ChatMessage(BaseModel):
    role: str
    content: str


class ChatRequest(BaseModel):
    messages: List[ChatMessage]
    currentBoard: BoardDataSchema


class ChatResponse(BaseModel):
    chatResponse: str
    boardUpdate: Optional[BoardDataSchema] = None

