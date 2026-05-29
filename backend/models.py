from sqlalchemy import Column, Integer, String, ForeignKey, ForeignKeyConstraint
from sqlalchemy.orm import relationship
from backend.database import Base

class UserModel(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, unique=True, index=True, nullable=False)
    password_hash = Column(String, nullable=False)

    columns = relationship("ColumnModel", back_populates="user", cascade="all, delete-orphan")
    cards = relationship("CardModel", back_populates="user", cascade="all, delete-orphan", overlaps="cards")


class ColumnModel(Base):
    __tablename__ = "columns"

    id = Column(String, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), primary_key=True)
    title = Column(String, nullable=False)
    position = Column(Integer, nullable=False)

    user = relationship("UserModel", back_populates="columns")
    cards = relationship("CardModel", back_populates="column", cascade="all, delete-orphan", overlaps="cards")


class CardModel(Base):
    __tablename__ = "cards"

    id = Column(String, primary_key=True)
    column_id = Column(String, nullable=False)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    title = Column(String, nullable=False)
    details = Column(String, nullable=False)
    position = Column(Integer, nullable=False)

    # Composite foreign key mapping to columns
    __table_args__ = (
        ForeignKeyConstraint(
            ["column_id", "user_id"],
            ["columns.id", "columns.user_id"],
            ondelete="CASCADE"
        ),
    )

    user = relationship("UserModel", back_populates="cards", overlaps="cards")
    column = relationship("ColumnModel", back_populates="cards", overlaps="cards,user")
