from sqlalchemy import String, Integer, JSON, DateTime, ForeignKey, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship
from datetime import datetime, timezone
from app.db.session import Base


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


class ChatSession(Base):
    __tablename__ = "chat_sessions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    session_id: Mapped[str] = mapped_column(String(100), unique=True, index=True, nullable=False)

    # Session memory stored as JSON list of messages
    messages: Mapped[list | None] = mapped_column(JSON, nullable=True, default=list)

    # Session-level context
    session_context: Mapped[dict | None] = mapped_column(JSON, nullable=True, default=dict)

    # Summary generated at end of session
    summary: Mapped[str | None] = mapped_column(Text, nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)

    def __repr__(self) -> str:
        return f"<ChatSession id={self.session_id} user_id={self.user_id}>"
