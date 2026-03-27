"""SQLAlchemy models for persisted assessments."""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import DateTime, Float, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db import Base


class AssessmentRecord(Base):
    """Persisted release assessment row."""

    __tablename__ = "assessments"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    assessment_id: Mapped[str] = mapped_column(String(64), unique=True, index=True, nullable=False)
    release_id: Mapped[str] = mapped_column(String(128), nullable=False)
    service: Mapped[str] = mapped_column(String(128), nullable=False)
    environment: Mapped[str] = mapped_column(String(64), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    evaluated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    decision: Mapped[str] = mapped_column(String(16), nullable=False)
    risk_score: Mapped[float] = mapped_column(Float, nullable=False)
    serialized_bundle: Mapped[str] = mapped_column(Text, nullable=False)
    serialized_result: Mapped[str] = mapped_column(Text, nullable=False)
