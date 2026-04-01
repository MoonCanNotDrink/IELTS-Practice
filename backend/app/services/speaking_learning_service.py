from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import PracticeSession, Recording, SavedTopic
from app.services.saved_topic_service import normalize_saved_topic_prompt

THRESHOLDS = {
    "min_duration_seconds": 30.0,
    "min_word_count": 40,
}


@dataclass
class LearningMetadataSnapshot:
    recording_id: int | None
    part: str
    prompt_match_type: str
    prompt_match_key: str
    prompt_source: str
    weakness_tags: list[str]
    has_coaching_payload: bool
    analysis_version: str


def _recording_text(recording: Recording) -> str:
    value = recording.__dict__.get("transcript")
    return value if isinstance(value, str) else ""


def _recording_duration_seconds(recording: Recording) -> float | None:
    value = recording.__dict__.get("duration_seconds")
    if isinstance(value, (int, float)):
        return float(value)
    return None


def _recording_part(recording: Recording) -> str:
    value = recording.__dict__.get("part")
    return value if isinstance(value, str) else "unknown"


async def apply_learning_metadata(
    db: AsyncSession,
    recording: Recording,
    score_result: dict[str, Any],
    analysis_version: str,
) -> LearningMetadataSnapshot:
    transcript = _recording_text(recording)
    duration_seconds = _recording_duration_seconds(recording)
    prompt_identity = await compute_prompt_identity(db, recording)
    weakness_tags = detect_weakness_tags(score_result, transcript, duration_seconds)
    coaching_payload = build_coaching_payload(transcript, duration_seconds)

    setattr(recording, "prompt_match_type", prompt_identity["prompt_match_type"])
    setattr(recording, "prompt_match_key", prompt_identity["prompt_match_key"])
    setattr(recording, "prompt_source", prompt_identity["prompt_source"])
    setattr(recording, "weakness_tags", weakness_tags)
    setattr(recording, "coaching_payload", coaching_payload)
    setattr(recording, "analysis_version", analysis_version)

    raw_id = recording.__dict__.get("id")
    recording_id = raw_id if isinstance(raw_id, int) else None

    return LearningMetadataSnapshot(
        recording_id=recording_id,
        part=_recording_part(recording),
        prompt_match_type=prompt_identity["prompt_match_type"],
        prompt_match_key=prompt_identity["prompt_match_key"],
        prompt_source=prompt_identity["prompt_source"],
        weakness_tags=weakness_tags,
        has_coaching_payload=coaching_payload is not None,
        analysis_version=analysis_version,
    )


def _fallback_prompt_match_key(recording: Recording) -> str:
    if recording.id is not None:
        return f"recording:{recording.id}"

    session_part = (
        f"session:{recording.session_id}"
        if recording.session_id is not None
        else "session:none"
    )
    question_part = (
        f"q:{recording.question_index}"
        if recording.question_index is not None
        else "q:none"
    )
    part = recording.part or "unknown"
    return f"ungrouped:{session_part}:{part}:{question_part}"


def _is_official_part2_recording(
    session: PracticeSession | None, recording: Recording
) -> bool:
    return bool(
        session is not None
        and session.topic_id is not None
        and recording.part == "part2"
    )


def _is_exam_generated_prompt(
    session: PracticeSession | None, recording: Recording, prompt_text: str
) -> bool:
    return bool(
        session is not None
        and session.topic_id is not None
        and prompt_text
        and recording.part in {"part1", "part3"}
        and recording.question_index is not None
        and "\n" not in prompt_text
        and "?" in prompt_text
    )


async def compute_prompt_identity(
    db: AsyncSession, recording: Recording
) -> dict[str, str]:
    session_id = recording.session_id
    session = (
        await db.get(PracticeSession, session_id) if session_id is not None else None
    )

    topic_id = session.topic_id if session is not None else None
    if _is_official_part2_recording(session, recording) and topic_id is not None:
        return {
            "prompt_match_type": "official_topic",
            "prompt_match_key": f"topic:{topic_id}",
            "prompt_source": "official",
        }

    prompt_text = (recording.question_text or "").strip()
    normalized = normalize_saved_topic_prompt(prompt_text)

    if _is_exam_generated_prompt(session, recording, prompt_text):
        return {
            "prompt_match_type": "exam_generated",
            "prompt_match_key": normalized or _fallback_prompt_match_key(recording),
            "prompt_source": "exam",
        }

    user_id = session.user_id if session is not None else None
    if session is not None and user_id is not None and normalized:
        result = await db.execute(
            select(SavedTopic).where(
                SavedTopic.user_id == user_id,
                SavedTopic.normalized_prompt == normalized,
            )
        )
        saved_topic = result.scalars().first()
        if saved_topic:
            return {
                "prompt_match_type": "normalized_text",
                "prompt_match_key": normalized,
                "prompt_source": "saved",
            }

    return {
        "prompt_match_type": "normalized_text",
        "prompt_match_key": normalized or _fallback_prompt_match_key(recording),
        "prompt_source": "custom",
    }


def _score_value(score_result: dict[str, Any], key: str) -> float | None:
    value = score_result.get(key)
    if value is None:
        nested_scores = score_result.get("scores")
        if isinstance(nested_scores, dict):
            short_key = key.removesuffix("_score")
            value = nested_scores.get(short_key)
    if isinstance(value, (int, float)):
        return float(value)
    return None


def detect_weakness_tags(
    score_result: dict[str, Any], transcript: str, duration_seconds: float | None
) -> list[str]:
    tags: list[str] = []

    vocabulary_score = _score_value(score_result, "vocabulary_score")
    if vocabulary_score is not None and vocabulary_score < 5.0:
        tags.append("limited_vocabulary")

    grammar_score = _score_value(score_result, "grammar_score")
    if grammar_score is not None and grammar_score < 5.0:
        tags.append("grammar_errors")

    fluency_score = _score_value(score_result, "fluency_score")
    if fluency_score is not None and fluency_score < 5.0:
        tags.append("hesitation")

    words = (transcript or "").lower().split()
    and_count = words.count("and")
    if and_count >= 8 and and_count / max(len(words), 1) >= 0.12:
        tags.append("repetitive_connectors")

    if (
        duration_seconds is not None
        and duration_seconds < THRESHOLDS["min_duration_seconds"]
    ):
        tags.append("underdeveloped_answer")

    if len(words) < THRESHOLDS["min_word_count"]:
        tags.append("short_answer")

    return list(dict.fromkeys(tags))


def build_coaching_payload(
    transcript: str, duration_seconds: float | None
) -> dict[str, Any] | None:
    text = (transcript or "").strip()
    word_count = len(text.split())
    too_short = (
        duration_seconds is not None
        and duration_seconds < THRESHOLDS["min_duration_seconds"]
    ) or word_count < THRESHOLDS["min_word_count"]
    if not too_short:
        return None

    sentences = [sentence.strip() for sentence in text.split(".") if sentence.strip()]
    target = sentences[0] if sentences else text
    target_excerpt = target[:400]
    target_quote = target[:80] or "your main point"

    return {
        "expand_target_sentence": target_excerpt,
        "followup_angles": [
            "Give an extra example that supports your main point.",
            "Add a personal experience related to this topic.",
        ],
        "model_extension": (
            f"Try adding one concrete example and one reason to support '{target_quote}'"
        ),
        "retry_recommendation": (
            "Try again focusing on an example plus a reason. Aim for 40+ words."
        ),
    }
