"""Shared helper functions used by multiple route modules."""

import ast
import json
from pathlib import Path

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.models import PracticeSession, Recording, User


def assert_session_access(session: PracticeSession, current_user: User) -> None:
    """Ensure a session can only be accessed by its owner."""
    if session.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="You do not have access to this session")


def resolve_audio_extension(filename: str | None) -> str:
    """Extract and validate audio file extension against allowed formats."""
    ext = Path(filename or "").suffix.lower().lstrip(".")
    if ext in settings.ALLOWED_AUDIO_FORMATS:
        return ext
    raise HTTPException(
        status_code=400,
        detail=f"Unsupported audio format: .{ext or 'unknown'}",
    )


def parse_feedback_blob(raw_feedback: str | None) -> dict | None:
    """Parse a JSON feedback string into a dict, with ast.literal_eval fallback."""
    if not raw_feedback:
        return None

    try:
        parsed = json.loads(raw_feedback)
    except Exception:
        try:
            parsed = ast.literal_eval(raw_feedback)
        except Exception:
            parsed = None

    return parsed if isinstance(parsed, dict) else None


def feedback_error_info(raw_feedback: str | None) -> tuple[str, str, str]:
    """Extract error status, message, and detail from a feedback blob."""
    parsed = parse_feedback_blob(raw_feedback)
    if not parsed or not parsed.get("error"):
        return "ok", "", ""
    return "error", str(parsed.get("error", "")), str(parsed.get("detail", ""))


async def get_part2_prompt_title(db: AsyncSession, session_id: int) -> str | None:
    """Get the Part 2 prompt title (first question_text) for a session."""
    result = await db.execute(
        select(Recording.question_text)
        .where(
            Recording.session_id == session_id,
            Recording.part == "part2",
            Recording.question_text.is_not(None),
            Recording.question_text != "",
        )
        .order_by(Recording.question_index, Recording.created_at)
        .limit(1)
    )
    return result.scalar_one_or_none()
