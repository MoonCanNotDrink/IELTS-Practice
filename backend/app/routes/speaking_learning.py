from __future__ import annotations

import difflib
from collections import Counter
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import and_, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models import PracticeSession, Recording
from app.routes.helpers import assert_session_access as _assert_session_access
from app.services.auth_service import User, get_current_user

router = APIRouter(prefix="/api/speaking", tags=["Speaking Learning"])

_SUGGESTION_BY_TAG = {
    "hesitation": "Practice answering in 45-second chunks and avoid long pauses between ideas.",
    "short_answer": "Add one concrete example and one reason to extend each answer naturally.",
    "underdeveloped_answer": "Use a simple structure: point, reason, and real-life example.",
    "grammar_errors": "Slow down slightly and focus on sentence control before adding complexity.",
    "limited_vocabulary": "Prepare 5-8 topic-specific phrases and reuse them accurately.",
    "repetitive_connectors": "Vary linkers by alternating because, for example, however, and as a result.",
}


def _as_tags(value: object) -> list[str]:
    if isinstance(value, list):
        return [item for item in value if isinstance(item, str)]
    return []


def _score_value(value: object) -> float:
    return float(value) if isinstance(value, (int, float)) else 0.0


def _score_snapshot(session: PracticeSession) -> dict[str, float]:
    return {
        "overall": _score_value(session.overall_score),
        "fluency": _score_value(session.fluency_score),
        "vocabulary": _score_value(session.vocabulary_score),
        "grammar": _score_value(session.grammar_score),
        "pronunciation": _score_value(session.pronunciation_score),
    }


def _score_deltas(
    current_session: PracticeSession, previous_session: PracticeSession
) -> dict[str, float]:
    current = _score_snapshot(current_session)
    previous = _score_snapshot(previous_session)
    return {key: current[key] - previous[key] for key in current.keys()}


def _sample_size_label(count: int) -> str:
    if count <= 2:
        return "early_signal"
    if count <= 4:
        return "emerging_pattern"
    return "recurring_pattern"


def _sample_size_note(count: int) -> str:
    if count <= 2:
        return "Early signal: keep practicing to confirm stable patterns."
    if count <= 4:
        return "Emerging pattern: trends are useful but may still shift quickly."
    return "Recurring pattern: enough recent answers to trust repeated weaknesses."


def _trend_direction(rows: list[dict[str, float]]) -> dict[str, str]:
    dimensions = ["overall", "fluency", "vocabulary", "grammar", "pronunciation"]
    if len(rows) < 2:
        return {dim: "insufficient_data" for dim in dimensions}

    mid = len(rows) // 2
    older = rows[:mid] if mid > 0 else rows[:1]
    newer = rows[mid:]
    if not older or not newer:
        return {dim: "insufficient_data" for dim in dimensions}

    trends: dict[str, str] = {}
    for dim in dimensions:
        older_avg = sum(item[dim] for item in older) / len(older)
        newer_avg = sum(item[dim] for item in newer) / len(newer)
        delta = newer_avg - older_avg
        if delta > 0.15:
            trends[dim] = "up"
        elif delta < -0.15:
            trends[dim] = "down"
        else:
            trends[dim] = "flat"
    return trends


def _recording_snapshot(recording: Recording) -> dict[str, object]:
    created_at = recording.created_at
    return {
        "recording_id": recording.id,
        "session_id": recording.session_id,
        "part": recording.part,
        "question_text": recording.question_text,
        "transcript": recording.transcript or "",
        "weakness_tags": _as_tags(recording.weakness_tags),
        "prompt_match_type": recording.prompt_match_type,
        "prompt_match_key": recording.prompt_match_key,
        "prompt_source": recording.prompt_source,
        "analysis_version": recording.analysis_version,
        "created_at": created_at.isoformat()
        if isinstance(created_at, datetime)
        else None,
    }


@router.get("/comparisons/{recording_id}")
async def get_speaking_comparison(
    recording_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    current = await db.get(Recording, recording_id)
    if current is None:
        raise HTTPException(status_code=404, detail="Recording not found")

    current_session = await db.get(PracticeSession, current.session_id)
    if current_session is None:
        raise HTTPException(status_code=404, detail="Session not found")
    _assert_session_access(current_session, current_user)

    prompt_match_key = (current.prompt_match_key or "").strip()
    if not prompt_match_key:
        return {"attempt_count": 1, "comparison": None}

    count_result = await db.execute(
        select(func.count(Recording.id))
        .select_from(Recording)
        .join(PracticeSession, Recording.session_id == PracticeSession.id)
        .where(
            PracticeSession.user_id == current_user.id,
            Recording.prompt_match_key == prompt_match_key,
        )
    )
    attempt_count = int(count_result.scalar() or 0) or 1

    previous_result = await db.execute(
        select(Recording)
        .join(PracticeSession, Recording.session_id == PracticeSession.id)
        .where(
            PracticeSession.user_id == current_user.id,
            Recording.prompt_match_key == prompt_match_key,
            or_(
                Recording.created_at < current.created_at,
                and_(
                    Recording.created_at == current.created_at,
                    Recording.id < current.id,
                ),
            ),
        )
        .order_by(Recording.created_at.desc(), Recording.id.desc())
        .limit(1)
    )
    previous = previous_result.scalars().first()
    if previous is None:
        return {"attempt_count": attempt_count, "comparison": None}

    previous_session = await db.get(PracticeSession, previous.session_id)
    if previous_session is None:
        raise HTTPException(status_code=404, detail="Session not found")

    previous_tags = set(_as_tags(previous.weakness_tags))
    current_tags = set(_as_tags(current.weakness_tags))

    return {
        "attempt_count": attempt_count,
        "comparison": {
            "current": _recording_snapshot(current),
            "previous": _recording_snapshot(previous),
            "score_deltas": _score_deltas(current_session, previous_session),
            "transcript_diff": list(
                difflib.ndiff(
                    (previous.transcript or "").splitlines(),
                    (current.transcript or "").splitlines(),
                )
            ),
            "weakness_follow_through": {
                "addressed_tags": sorted(previous_tags - current_tags),
                "unchanged_tags": sorted(previous_tags & current_tags),
                "new_tags": sorted(current_tags - previous_tags),
            },
        },
    }


@router.get("/weakness-summary")
async def get_weakness_summary(
    limit: int = Query(default=10, ge=1, le=50),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    result = await db.execute(
        select(Recording, PracticeSession)
        .join(PracticeSession, Recording.session_id == PracticeSession.id)
        .where(
            PracticeSession.user_id == current_user.id,
            Recording.transcript.is_not(None),
            Recording.transcript != "",
        )
        .order_by(Recording.created_at.desc(), Recording.id.desc())
        .limit(limit)
    )
    rows = result.all()
    recent_count = len(rows)

    tag_counter: Counter[str] = Counter()
    score_rows: list[dict[str, float]] = []
    for recording, session in rows:
        tag_counter.update(_as_tags(recording.weakness_tags))
        score_rows.append(_score_snapshot(session))

    ordered_tags = sorted(tag_counter.items(), key=lambda item: (-item[1], item[0]))
    top_tags = [{"tag": tag, "count": count} for tag, count in ordered_tags[:3]]
    actionable_suggestions = [
        {"tag": item["tag"], "suggestion": _SUGGESTION_BY_TAG.get(item["tag"], "")}
        for item in top_tags
        if _SUGGESTION_BY_TAG.get(item["tag"])
    ]

    trend_direction = _trend_direction(list(reversed(score_rows)))

    return {
        "recent_count": recent_count,
        "sample_size_label": _sample_size_label(recent_count),
        "sample_size_note": _sample_size_note(recent_count),
        "top_recurring_tags": top_tags,
        "trend_direction": trend_direction,
        "actionable_suggestions": actionable_suggestions,
    }
