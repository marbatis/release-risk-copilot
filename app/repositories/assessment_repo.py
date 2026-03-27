"""Assessment persistence repository backed by SQLAlchemy."""

from __future__ import annotations

from collections.abc import Callable
from threading import Lock
from typing import Optional

from sqlalchemy import desc, select
from sqlalchemy.orm import Session

from app.db import SessionLocal, init_db
from app.models.db_models import AssessmentRecord
from app.schemas.models import Assessment

SessionFactory = Callable[[], Session]
_db_init_lock = Lock()
_db_initialized = False


def _ensure_db_initialized() -> None:
    """Create required DB objects once for API and tests."""

    global _db_initialized
    if _db_initialized:
        return

    with _db_init_lock:
        if not _db_initialized:
            init_db()
            _db_initialized = True


class AssessmentRepository:
    """Persist and query assessment history rows."""

    def __init__(self, session_factory: SessionFactory = SessionLocal) -> None:
        self.session_factory = session_factory

    def save(self, assessment: Assessment) -> None:
        """Insert an assessment row."""

        _ensure_db_initialized()
        record = AssessmentRecord(
            assessment_id=assessment.assessment_id,
            release_id=assessment.bundle.release_id,
            service=assessment.bundle.service,
            environment=assessment.bundle.environment,
            created_at=assessment.bundle.created_at,
            evaluated_at=assessment.evaluated_at,
            decision=assessment.decision.decision.value,
            risk_score=assessment.rules.risk_score,
            serialized_bundle=assessment.bundle.model_dump_json(),
            serialized_result=assessment.model_dump_json(),
        )

        with self.session_factory() as session:
            session.add(record)
            session.commit()

    def list_history(self, limit: int = 100) -> list[AssessmentRecord]:
        """Return newest assessments first."""

        _ensure_db_initialized()
        with self.session_factory() as session:
            stmt = select(AssessmentRecord).order_by(desc(AssessmentRecord.evaluated_at)).limit(limit)
            return list(session.scalars(stmt).all())

    def get_by_assessment_id(self, assessment_id: str) -> Optional[Assessment]:
        """Return one persisted assessment payload by external id."""

        _ensure_db_initialized()
        with self.session_factory() as session:
            stmt = select(AssessmentRecord).where(AssessmentRecord.assessment_id == assessment_id)
            record = session.scalars(stmt).first()
            if record is None:
                return None
            return Assessment.model_validate_json(record.serialized_result)
