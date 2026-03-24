import json

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models import PracticeSession, Recording, Topic, WritingAttempt
from app.services.auth_service import get_current_user, User

router = APIRouter(prefix="/api/dashboard", tags=["Dashboard"])


def parse_feedback_blob(raw_feedback: str | None) -> dict | None:
    if not raw_feedback:
        return None
    try:
        parsed = json.loads(raw_feedback)
    except Exception:
        parsed = None
    return parsed if isinstance(parsed, dict) else None


def feedback_error_info(raw_feedback: str | None) -> tuple[str, str, str]:
    parsed = parse_feedback_blob(raw_feedback)
    if not parsed or not parsed.get("error"):
        return "ok", "", ""
    return "error", str(parsed.get("error", "")), str(parsed.get("detail", ""))


def determine_speaking_task_type(recordings: list[Recording]) -> str:
    recorded_parts = {recording.part for recording in recordings if (recording.transcript or "").strip()}
    if recorded_parts == {"part2"}:
        return "part2_only"
    if {"part1", "part2", "part3"}.issubset(recorded_parts):
        return "full_exam"
    return "partial_exam"


async def resolve_speaking_title(db: AsyncSession, session: PracticeSession, topic_title: str | None) -> str:
    if topic_title:
        return topic_title
    result = await db.execute(
        select(Recording.question_text)
        .where(
            Recording.session_id == session.id,
            Recording.part == "part2",
            Recording.question_text.is_not(None),
            Recording.question_text != "",
        )
        .order_by(Recording.question_index, Recording.created_at)
        .limit(1)
    )
    return result.scalar_one_or_none() or "Unknown"


@router.get("/history")
async def get_dashboard_history(
    limit: int = 20,
    module_type: str = "all",
    task_type: str | None = None,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    normalized_module = (module_type or "all").strip().lower()
    normalized_task = (task_type or "").strip().lower() or None
    entries: list[dict] = []

    if normalized_module in {"all", "speaking"}:
        result = await db.execute(
            select(PracticeSession, Topic.title)
            .outerjoin(Topic, PracticeSession.topic_id == Topic.id)
            .where(
                PracticeSession.status == "completed",
                PracticeSession.user_id == current_user.id,
            )
        )
        for session, topic_title in result.all():
            recordings_result = await db.execute(
                select(Recording)
                .where(Recording.session_id == session.id)
                .order_by(Recording.part, Recording.question_index)
            )
            recordings = recordings_result.scalars().all()
            speaking_task_type = determine_speaking_task_type(recordings)
            if normalized_task and normalized_task != speaking_task_type:
                continue
            scoring_status, scoring_error, scoring_error_detail = feedback_error_info(session.feedback)
            completed_at = session.finished_at.isoformat() if session.finished_at else None
            entries.append(
                {
                    "entry_id": f"speaking:{session.id}",
                    "id": session.id,
                    "module_type": "speaking",
                    "task_type": speaking_task_type,
                    "title": await resolve_speaking_title(db, session, topic_title),
                    "date": completed_at,
                    "completed_at": completed_at,
                    "status": "completed",
                    "scoring_status": scoring_status,
                    "scoring_error": scoring_error,
                    "scoring_error_detail": scoring_error_detail,
                    "scores": {
                        "fluency": session.fluency_score,
                        "vocabulary": session.vocabulary_score,
                        "grammar": session.grammar_score,
                        "pronunciation": session.pronunciation_score,
                        "overall": session.overall_score,
                    },
                    "detail_api_path": f"/api/scoring/sessions/{session.id}/detail",
                }
            )

    if normalized_module in {"all", "writing"}:
        result = await db.execute(
            select(WritingAttempt)
            .where(WritingAttempt.user_id == current_user.id)
        )
        for attempt in result.scalars().all():
            if normalized_task and normalized_task != attempt.task_type:
                continue
            scoring_status, scoring_error, scoring_error_detail = feedback_error_info(attempt.feedback)
            completed_at = attempt.completed_at.isoformat() if attempt.completed_at else None
            entries.append(
                {
                    "entry_id": f"writing:{attempt.id}",
                    "id": attempt.id,
                    "module_type": "writing",
                    "task_type": attempt.task_type,
                    "title": attempt.prompt_title,
                    "date": completed_at,
                    "completed_at": completed_at,
                    "status": "completed",
                    "scoring_status": scoring_status,
                    "scoring_error": scoring_error,
                    "scoring_error_detail": scoring_error_detail,
                    "scores": {
                        "task": attempt.task_score,
                        "coherence": attempt.coherence_score,
                        "lexical": attempt.lexical_score,
                        "grammar": attempt.grammar_score,
                        "overall": attempt.overall_score,
                    },
                    "detail_api_path": f"/api/writing/attempts/{attempt.id}/detail",
                }
            )

    entries.sort(key=lambda item: item.get("completed_at") or "", reverse=True)
    return entries[: max(1, limit)]
