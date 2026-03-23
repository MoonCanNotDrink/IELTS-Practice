"""Helpers for SavedTopic persistence: normalization + upsert by user_id.

Keep this file small and route-agnostic. Provides:
- normalize_saved_topic_prompt(text): trim, collapse whitespace, lowercase
- async upsert_saved_topic(db, user_id, title, prompt_text, **kwargs)

The upsert uses normalized_prompt to dedupe per-user.
"""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import SavedTopic


def normalize_saved_topic_prompt(text: str | None) -> str:
    """Normalize prompt: trim, collapse internal whitespace to single spaces, lowercase.

    Exact rules:
    - If text is falsy, return empty string
    - Strip leading/trailing whitespace
    - Replace any run of whitespace (\t, \n, multiple spaces) with a single space
    - Lowercase the result
    """
    if not text:
        return ""
    # strip
    s = text.strip()
    # collapse internal whitespace
    parts = s.split()
    collapsed = " ".join(parts)
    return collapsed.lower()


async def upsert_saved_topic(
    db: AsyncSession,
    user_id: int,
    title: str,
    prompt_text: str | None = None,
    **kwargs,
) -> SavedTopic:
    """Insert or update a SavedTopic for user_id based on normalized prompt.

    Behavior:
    - Compute normalized_prompt from prompt_text
    - If a SavedTopic exists for (user_id, normalized_prompt) -> update title/prompt_text/other fields
    - Else create a new SavedTopic with provided fields
    - Returns the ORM instance (attached to session). Caller should commit/flush as needed.

    Note: this function is async but relies on SQLAlchemy ORM session operations.
    """
    normalized = normalize_saved_topic_prompt(prompt_text)

    # Query for existing row scoped by user_id + normalized_prompt
    result = await db.execute(
        select(SavedTopic).where(
            SavedTopic.user_id == user_id,
            SavedTopic.normalized_prompt == normalized,
        )
    )
    existing = result.scalars().first()

    if existing:
        # Update fields minimally
        existing.title = title or existing.title
        existing.prompt_text = prompt_text or existing.prompt_text
        existing.normalized_prompt = normalized or existing.normalized_prompt
        for k, v in kwargs.items():
            if hasattr(existing, k):
                setattr(existing, k, v)
        # ensure it's attached
        db.add(existing)
        return existing

    # Create new
    new = SavedTopic(
        user_id=user_id,
        title=title,
        prompt_text=prompt_text,
        normalized_prompt=normalized,
        **{k: v for k, v in kwargs.items() if hasattr(SavedTopic, k)},
    )
    db.add(new)
    return new
