"""API routes for Part 2 practice flow: draw topic 鈫?record 鈫?score."""

import uuid
import json
import asyncio
import logging
import time
from datetime import datetime
from pathlib import Path
from fastapi import APIRouter, Depends, UploadFile, File, Form, HTTPException
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func

from app.database import get_db
from app.models import Topic, PracticeSession, Recording, SavedTopic
from app.services.saved_topic_service import (
    upsert_saved_topic,
    normalize_saved_topic_prompt,
)
from app.config import settings
from app.services.asr_service import (
    transcribe_audio,
    _estimate_word_timestamps,
    _looks_like_wav,
    classify_asr_fallback,
)
from app.services.scoring_service import score_speaking, classify_scoring_fallback
from app.services.pronunciation_service import assess_pronunciation_sync
from app.services.auth_service import get_current_user, User
from app.routes.helpers import (
    assert_session_access as _assert_session_access,
    resolve_audio_extension as _resolve_audio_extension,
    get_part2_prompt_title as _get_part2_prompt_title,
)

router = APIRouter(prefix="/api/part2", tags=["Part 2"])
logger = logging.getLogger(__name__)
NO_SPEECH_DETAIL = (
    "Transcription failed - no speech detected. "
    "Please re-record and speak clearly into your microphone."
)


def _emit_structured_log(level: str, event: str, **payload) -> None:
    body = {"event": event, **payload}
    line = json.dumps(body, ensure_ascii=False, sort_keys=True)
    if level == "error":
        logger.error(line)
    elif level == "warning":
        logger.warning(line)
    else:
        logger.info(line)


def _request_id_headers(request_id: str) -> dict[str, str]:
    return {"X-Request-ID": request_id}


@router.get("/topics/random")
async def draw_topic(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Draw a random Part 2 topic card."""
    result = await db.execute(select(Topic).order_by(func.random()).limit(1))
    topic = result.scalars().first()
    if not topic:
        raise HTTPException(status_code=404, detail="No topics available")

    return {
        "id": topic.id,
        "title": topic.title,
        "points": topic.points,
        "category": topic.category,
    }


@router.get("/topics")
async def list_topics(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """List all available Part 2 topics."""
    result = await db.execute(select(Topic).order_by(Topic.category, Topic.id))
    topics = result.scalars().all()
    return [
        {
            "id": t.id,
            "title": t.title,
            "points": t.points,
            "category": t.category,
        }
        for t in topics
    ]


class CreateSavedTopicRequest(BaseModel):
    prompt_text: str
    category: str | None = None


@router.get("/free-practice-topics")
async def get_free_practice_topics(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Return grouped selector data for free-practice topics.

    Response shape MUST be exactly:
    { "official_topics": [...], "saved_topics": [...] }
    """
    # Official topics (selector needs id, title, category)
    result = await db.execute(select(Topic).order_by(Topic.category, Topic.id))
    official = result.scalars().all()
    official_topics = [
        {"id": t.id, "title": t.title, "category": t.category} for t in official
    ]

    # Saved topics scoped to current user (return specific fields for frontend wiring)
    result = await db.execute(
        select(SavedTopic)
        .where(SavedTopic.user_id == current_user.id, SavedTopic.is_archived == False)
        .order_by(SavedTopic.updated_at.desc())
    )
    saved_rows = result.scalars().all()
    saved_topics = [
        {
            "id": s.id,
            "title": s.title,
            "prompt_text": s.prompt_text,
            "category": s.category,
            "source": s.source,
            "use_count": s.use_count,
            "last_used_at": s.last_used_at.isoformat() if s.last_used_at else None,
        }
        for s in saved_rows
    ]

    return {"official_topics": official_topics, "saved_topics": saved_topics}


@router.post("/free-practice-topics")
async def create_free_practice_topic(
    body: CreateSavedTopicRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Create or dedupe a user-saved free-practice prompt.

    Accepts: { prompt_text: str, category?: str }
    Derives title from first non-empty line of prompt_text and upserts via upsert_saved_topic.
    Defaults category to 'general'. Response indicates created vs deduped.
    """
    prompt = (body.prompt_text or "").strip()
    if not prompt:
        raise HTTPException(status_code=400, detail="prompt_text is required")

    category = (body.category or "general").strip() or "general"

    # derive title from first line, truncated to 255 chars
    first_line = prompt.splitlines()[0].strip() if prompt.splitlines() else prompt
    title = (first_line[:255]) or "Untitled"

    # determine whether this will be a new row (dedupe by normalized_prompt scoped to user)
    normalized = normalize_saved_topic_prompt(prompt)
    result = await db.execute(
        select(SavedTopic).where(
            SavedTopic.user_id == current_user.id,
            SavedTopic.normalized_prompt == normalized,
        )
    )
    existing = result.scalars().first()

    topic = await upsert_saved_topic(
        db,
        current_user.id,
        title=title,
        prompt_text=prompt,
        category=category,
        source="user",
    )
    # ensure DB assigns id
    await db.flush()

    created = existing is None

    resp = {
        "created": created,
        "topic": {
            "id": topic.id,
            "title": topic.title,
            "prompt_text": topic.prompt_text,
            "category": topic.category,
            "source": topic.source,
            "use_count": topic.use_count,
            "last_used_at": topic.last_used_at.isoformat()
            if topic.last_used_at
            else None,
        },
    }
    return resp


class CreateSessionRequest(BaseModel):
    topic_id: int | None = None
    saved_topic_id: int | None = None
    custom_topic: str = ""


def _can_run_azure_pronunciation(
    audio_filename: str | None, audio_bytes: bytes
) -> bool:
    return bool(
        audio_filename
        and audio_filename.lower().endswith(".wav")
        and _looks_like_wav(audio_bytes)
    )


@router.post("/sessions")
async def create_session(
    request: CreateSessionRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Start a new practice session for Part 2."""
    custom_topic = request.custom_topic.strip()
    # Determine which source was provided. Exactly one of topic_id, saved_topic_id, custom_topic is required.
    provided = 0
    if request.topic_id is not None:
        provided += 1
    if request.saved_topic_id is not None:
        provided += 1
    if custom_topic:
        provided += 1

    if provided != 1:
        raise HTTPException(
            status_code=400,
            detail="Provide exactly one of topic_id, saved_topic_id, or custom_topic",
        )

    # Official topic path
    topic = None
    if request.topic_id is not None:
        topic = await db.get(Topic, request.topic_id)
        if not topic:
            raise HTTPException(status_code=404, detail="Topic not found")

    # Saved-topic path: must belong to current user and not be archived
    saved_topic = None
    if request.saved_topic_id is not None:
        saved_topic = await db.get(SavedTopic, request.saved_topic_id)
        if (
            not saved_topic
            or saved_topic.user_id != current_user.id
            or saved_topic.is_archived
        ):
            raise HTTPException(status_code=404, detail="Saved topic not found")
        # update usage metrics
        saved_topic.use_count = (saved_topic.use_count or 0) + 1
        saved_topic.last_used_at = datetime.utcnow()
        db.add(saved_topic)

    # Create session: we store official topic_id for official topics, otherwise leave topic_id NULL
    session_topic_id = request.topic_id if request.topic_id is not None else None
    session = PracticeSession(
        topic_id=session_topic_id, status="in_progress", user_id=current_user.id
    )
    db.add(session)
    await db.flush()

    # If a saved topic was provided, surface its prompt_text in the response as the active question source
    resolved_custom_topic = None
    if saved_topic is not None:
        resolved_custom_topic = saved_topic.prompt_text or None
    elif custom_topic:
        resolved_custom_topic = custom_topic

    return {
        "session_id": session.id,
        "topic_id": session_topic_id,
        "saved_topic_id": request.saved_topic_id,
        "custom_topic": resolved_custom_topic,
        "status": "in_progress",
    }


@router.post("/sessions/{session_id}/upload-audio")
async def upload_audio(
    session_id: int,
    audio: UploadFile = File(...),
    notes: str = Form(default=""),
    question_text: str = Form(default=""),
    client_transcript: str = Form(default=""),  # text from browser Web Speech API
    practice_source: str = Form(...),
    saved_topic_id: int | None = Form(default=None),
    custom_category: str = Form(default="general"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Upload Part 2 recording audio.
    Triggers ASR transcription and stores results.
    """
    request_id = uuid.uuid4().hex

    # Verify session exists
    session = await db.get(PracticeSession, session_id)
    if not session:
        raise HTTPException(
            status_code=404,
            detail="Session not found",
            headers=_request_id_headers(request_id),
        )
    _assert_session_access(session, current_user)

    # Read audio bytes
    audio_bytes = await audio.read()
    if len(audio_bytes) == 0:
        raise HTTPException(status_code=400, detail="Empty audio file")

    # Get topic info for context
    topic = await db.get(Topic, session.topic_id) if session.topic_id else None
    prompt_text = question_text.strip()
    question_text = ""
    if topic:
        question_text = topic.title + "\n" + "\n".join(f"- {p}" for p in topic.points)
    elif prompt_text:
        question_text = prompt_text
    else:
        raise HTTPException(
            status_code=400,
            detail="question_text is required for custom-topic sessions",
        )

    # Save audio file
    ext = _resolve_audio_extension(audio.filename)
    audio_filename = f"session_{session_id}_part2_{uuid.uuid4().hex[:8]}.{ext}"
    audio_path = settings.recordings_path / audio_filename
    with open(audio_path, "wb") as f:
        f.write(audio_bytes)

    asr_started = time.perf_counter()
    asr_result = await transcribe_audio(
        audio_bytes, audio_filename, request_id=request_id
    )
    asr_duration_ms = round((time.perf_counter() - asr_started) * 1000, 2)
    asr_detail = asr_result.get("error")
    _emit_structured_log(
        "info",
        "part2_asr_completed",
        request_id=request_id,
        route="/api/part2/sessions/{session_id}/upload-audio",
        stage="asr",
        status="ok" if asr_result.get("text") else "fallback",
        duration_ms=asr_duration_ms,
        fallback_reason=classify_asr_fallback(asr_detail),
        detail=asr_detail or "",
        session_id=session_id,
    )

    # ASR transcription: prefer server ASR, then fall back to browser-finalized text.
    if not asr_result.get("text") and client_transcript.strip():
        transcript = client_transcript.strip()
        words = _estimate_word_timestamps(transcript)
        asr_result = {"text": transcript, "words": words}
        fallback_reason = classify_asr_fallback(asr_detail) or "asr_failure"
        _emit_structured_log(
            "info",
            "part2_asr_client_transcript_fallback",
            request_id=request_id,
            route="/api/part2/sessions/{session_id}/upload-audio",
            stage="asr",
            status="fallback",
            fallback_reason=fallback_reason,
            session_id=session_id,
        )

    # Create recording entry
    recording = Recording(
        session_id=session_id,
        part="part2",
        question_index=0,
        question_text=question_text,
        audio_filename=audio_filename,
        transcript=asr_result["text"],
        word_timestamps=asr_result["words"],
        notes=notes,
    )

    # Calculate duration from timestamps
    if asr_result["words"]:
        recording.duration_seconds = asr_result["words"][-1]["end"]

    db.add(recording)
    await db.flush()

    # Autosave logic for custom prompts (only when session.topic_id is NULL)
    # - practice_source distinguishes 'custom' vs 'saved'
    # - only autosave when transcript is non-empty
    # - do NOT autosave official topics (topic is not None)
    # - for 'saved' source: validate ownership and update usage but do not create duplicates
    try:
        if session.topic_id is None:
            # saved-topic path: respect existing saved topic and increment usage
            if practice_source == "saved" and saved_topic_id is not None:
                saved = await db.get(SavedTopic, saved_topic_id)
                if not saved or saved.user_id != current_user.id or saved.is_archived:
                    raise HTTPException(status_code=404, detail="Saved topic not found")
                saved.use_count = (saved.use_count or 0) + 1
                saved.last_used_at = datetime.utcnow()
                db.add(saved)

            # custom prompt path: upsert only when transcript present
            elif practice_source == "custom":
                transcript_text = (asr_result.get("text") or "").strip()
                if transcript_text:
                    # derive title from first non-empty line of the question_text
                    first_line = (
                        question_text.splitlines()[0].strip()
                        if question_text.splitlines()
                        else question_text
                    )
                    title = (first_line[:255]) or "Untitled"
                    # use upsert_saved_topic to dedupe per user
                    topic_row = await upsert_saved_topic(
                        db,
                        current_user.id,
                        title=title,
                        prompt_text=question_text,
                        category=(custom_category or "general").strip() or "general",
                        source="user",
                    )
                    db.add(topic_row)
                    # ensure DB assigns id
                    await db.flush()

            # official topics: do nothing
    except HTTPException:
        # Re-raise HTTPExceptions for proper API response
        raise
    except Exception:
        # Silently ignore autosave failures (do not block upload)
        pass

    return {
        "recording_id": recording.id,
        "transcript": asr_result["text"],
        "word_count": len(asr_result["words"]),
        "duration_seconds": recording.duration_seconds,
        "request_id": request_id,
    }


@router.post("/sessions/{session_id}/score")
async def score_session(
    session_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Score a completed Part 2 session.
    Runs pronunciation assessment + LLM scoring in parallel.
    """
    request_id = uuid.uuid4().hex
    scoring_started = time.perf_counter()
    _emit_structured_log(
        "info",
        "part2_scoring_started",
        request_id=request_id,
        route="/api/part2/sessions/{session_id}/score",
        session_id=session_id,
    )

    # Load session and recordings
    session = await db.get(PracticeSession, session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    _assert_session_access(session, current_user)

    result = await db.execute(
        select(Recording).where(Recording.session_id == session_id)
    )
    recordings = result.scalars().all()
    if not recordings:
        raise HTTPException(
            status_code=400,
            detail="No recordings found for this session",
            headers=_request_id_headers(request_id),
        )

    # Get the Part 2 recording (primary)
    part2_recording = next((r for r in recordings if r.part == "part2"), recordings[0])

    if not part2_recording.transcript:
        _emit_structured_log(
            "warning",
            "part2_scoring_failed",
            request_id=request_id,
            route="/api/part2/sessions/{session_id}/score",
            stage="input_validation",
            fallback_reason="audio_or_no_speech_issue",
            detail="missing_part2_transcript",
            session_id=session_id,
        )
        raise HTTPException(
            status_code=422,
            detail=NO_SPEECH_DETAIL,
            headers=_request_id_headers(request_id),
        )

    # Get topic
    topic = await db.get(Topic, session.topic_id) if session.topic_id else None
    question_text = ""
    if topic:
        question_text = topic.title + "\n" + "\n".join(f"- {p}" for p in topic.points)
    elif part2_recording.question_text:
        question_text = part2_recording.question_text

    # Run pronunciation assessment (if audio file exists and Azure is configured)
    pron_data = None
    pron_started = time.perf_counter()
    pron_status = "skipped"
    pron_fallback_reason = None
    from app.config import settings as app_settings

    if app_settings.AZURE_SPEECH_KEY and part2_recording.audio_filename:
        audio_path = app_settings.recordings_path / part2_recording.audio_filename
        if audio_path.exists():
            audio_bytes = audio_path.read_bytes()
            if _can_run_azure_pronunciation(
                part2_recording.audio_filename, audio_bytes
            ):
                # Azure SDK is synchronous 鈥?run in thread pool
                try:
                    pron_data = await asyncio.wait_for(
                        asyncio.to_thread(
                            assess_pronunciation_sync,
                            audio_bytes,
                            part2_recording.transcript,
                        ),
                        timeout=max(1, app_settings.PRONUNCIATION_TIMEOUT_SECONDS),
                    )
                    pron_status = "ok"
                except asyncio.TimeoutError:
                    pron_data = None
                    pron_status = "error"
                    pron_fallback_reason = "config_or_dependency_issue"
    _emit_structured_log(
        "info",
        "part2_scoring_stage_timing",
        request_id=request_id,
        route="/api/part2/sessions/{session_id}/score",
        stage="pronunciation",
        status=pron_status,
        duration_ms=round((time.perf_counter() - pron_started) * 1000, 2),
        fallback_reason=pron_fallback_reason,
        session_id=session_id,
    )

    # Acoustic analysis (librosa)
    acoustic_data = None
    acoustic_started = time.perf_counter()
    acoustic_status = "skipped"
    acoustic_fallback_reason = None
    from app.services.acoustic_service import analyze_audio_fluency_sync

    if part2_recording.audio_filename and part2_recording.transcript:
        from app.config import settings as app_settings

        audio_path = app_settings.recordings_path / part2_recording.audio_filename
        if audio_path.exists():
            word_count = len(part2_recording.transcript.split())
            try:
                acoustic_data = await asyncio.to_thread(
                    analyze_audio_fluency_sync, str(audio_path), word_count
                )
                acoustic_status = "ok" if acoustic_data else "fallback"
            except Exception:
                acoustic_data = None
                acoustic_status = "error"
                acoustic_fallback_reason = "config_or_dependency_issue"
    _emit_structured_log(
        "info",
        "part2_scoring_stage_timing",
        request_id=request_id,
        route="/api/part2/sessions/{session_id}/score",
        stage="acoustic",
        status=acoustic_status,
        duration_ms=round((time.perf_counter() - acoustic_started) * 1000, 2),
        fallback_reason=acoustic_fallback_reason,
        session_id=session_id,
    )

    # Run LLM scoring
    llm_started = time.perf_counter()
    score_result = await score_speaking(
        transcript=part2_recording.transcript,
        question_text=question_text,
        part="part2",
        word_timestamps=part2_recording.word_timestamps,
        pronunciation_data=pron_data,
        acoustic_data=acoustic_data,
        request_id=request_id,
    )
    llm_fallback_reason = classify_scoring_fallback(
        score_result.get("error"),
        score_result.get("detail"),
    )
    _emit_structured_log(
        "info",
        "part2_scoring_stage_timing",
        request_id=request_id,
        route="/api/part2/sessions/{session_id}/score",
        stage="llm_scoring",
        status="error" if score_result.get("error") else "ok",
        duration_ms=round((time.perf_counter() - llm_started) * 1000, 2),
        fallback_reason=llm_fallback_reason,
        session_id=session_id,
    )

    # Update session with scores
    if score_result.get("error") == "empty_transcript":
        _emit_structured_log(
            "warning",
            "part2_scoring_failed",
            request_id=request_id,
            route="/api/part2/sessions/{session_id}/score",
            stage="llm_scoring",
            fallback_reason="audio_or_no_speech_issue",
            detail=score_result.get("detail", ""),
            session_id=session_id,
        )
        raise HTTPException(status_code=422, detail=NO_SPEECH_DETAIL)

    # Save the result, even if it's an LLM fallback with an "error" key.
    # This ensures the 0.0 fallback values and error message are visible to the user.
    session.fluency_score = score_result.get("fluency_score", 0.0)
    session.vocabulary_score = score_result.get("vocabulary_score", 0.0)
    session.grammar_score = score_result.get("grammar_score", 0.0)
    session.pronunciation_score = score_result.get("pronunciation_score", 0.0)
    session.overall_score = score_result.get("overall_score", 0.0)
    session.sample_answer = score_result.get("sample_answer", "")

    if "error" in score_result:
        # Persist JSON so parsing is stable on history/detail pages.
        session.feedback = json.dumps(
            {
                "overall_feedback": score_result.get(
                    "overall_feedback", "Scoring failed."
                ),
                "error": score_result.get("error", "llm_generation_failed"),
                "detail": score_result.get("detail", ""),
            },
            ensure_ascii=False,
        )
    else:
        # Persist full JSON result instead of Python repr.
        session.feedback = json.dumps(score_result, ensure_ascii=False)

    # Update pronunciation data on recording
    if pron_data and "error" not in pron_data:
        part2_recording.pronunciation_accuracy = pron_data.get("accuracy_score")
        part2_recording.pronunciation_details = pron_data

    session.status = "completed"
    session.finished_at = datetime.utcnow()

    _emit_structured_log(
        "info",
        "part2_scoring_completed",
        request_id=request_id,
        route="/api/part2/sessions/{session_id}/score",
        status="error" if score_result.get("error") else "ok",
        fallback_reason=llm_fallback_reason,
        duration_ms=round((time.perf_counter() - scoring_started) * 1000, 2),
        session_id=session_id,
    )

    return {
        "request_id": request_id,
        "session_id": session_id,
        "exam_scope": "part2_only",
        "is_full_flow": False,
        "missing_parts": ["part1", "part3"],
        "scores": {
            "fluency": score_result.get("fluency_score"),
            "vocabulary": score_result.get("vocabulary_score"),
            "grammar": score_result.get("grammar_score"),
            "pronunciation": score_result.get("pronunciation_score"),
            "overall": score_result.get("overall_score"),
        },
        "feedback": {
            "fluency": score_result.get("fluency_feedback", ""),
            "vocabulary": score_result.get("vocabulary_feedback", ""),
            "grammar": score_result.get("grammar_feedback", ""),
            "pronunciation": score_result.get("pronunciation_feedback", ""),
            "overall": score_result.get("overall_feedback", ""),
        },
        "key_improvements": score_result.get("key_improvements", []),
        "sample_answer": score_result.get("sample_answer", ""),
        "pronunciation_data": pron_data,
    }


@router.get("/history")
async def get_history(
    limit: int = 20,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get recent practice session history with scores."""
    result = await db.execute(
        select(PracticeSession, Topic.title)
        .outerjoin(Topic, PracticeSession.topic_id == Topic.id)
        .where(
            PracticeSession.status == "completed",
            PracticeSession.user_id == current_user.id,
        )
        .order_by(PracticeSession.finished_at.desc())
        .limit(limit)
    )
    rows = result.all()

    history = []
    for s, topic_title in rows:
        resolved_title = (
            topic_title or await _get_part2_prompt_title(db, s.id) or "Unknown"
        )
        history.append(
            {
                "session_id": s.id,
                "topic_title": resolved_title,
                "date": s.finished_at.isoformat() if s.finished_at else None,
                "scores": {
                    "fluency": s.fluency_score,
                    "vocabulary": s.vocabulary_score,
                    "grammar": s.grammar_score,
                    "pronunciation": s.pronunciation_score,
                    "overall": s.overall_score,
                },
            }
        )

    return history
