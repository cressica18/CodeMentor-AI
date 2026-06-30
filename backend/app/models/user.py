from sqlalchemy import String, Integer, Float, JSON, DateTime, Text
from sqlalchemy.orm import Mapped, mapped_column
from datetime import datetime, timezone
from app.db.session import Base


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    cf_handle: Mapped[str] = mapped_column(String(100), unique=True, index=True, nullable=False)
    display_name: Mapped[str | None] = mapped_column(String(200), nullable=True)
    current_rating: Mapped[int | None] = mapped_column(Integer, nullable=True)
    max_rating: Mapped[int | None] = mapped_column(Integer, nullable=True)

    # Topic skill ratings stored as JSON: {"dp": 0.72, "graphs": 0.41, ...}
    topic_ratings: Mapped[dict | None] = mapped_column(JSON, nullable=True, default=dict)

    # Weak topics list: ["graphs", "segment_trees"]
    weak_topics: Mapped[list | None] = mapped_column(JSON, nullable=True, default=list)

    # Learning path state
    learning_path: Mapped[dict | None] = mapped_column(JSON, nullable=True, default=dict)

    # User preferences
    preferences: Mapped[dict | None] = mapped_column(JSON, nullable=True, default=dict)

    # Phase 2 — full CF analytics blob (rating trend, tag stats, heatmap …)
    cf_analytics: Mapped[dict | None] = mapped_column(JSON, nullable=True, default=None)

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)
    last_active: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    def __repr__(self) -> str:
        return f"<User cf_handle={self.cf_handle} rating={self.current_rating}>"
