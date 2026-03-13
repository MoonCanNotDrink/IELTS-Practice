"""API routes for Part 2 practice flow: draw topic 鈫?record 鈫?score."""

import uuid
import json
import asyncio
from datetime import datetime
from pathlib import Path
from fastapi import APIRouter, Depends, UploadFile, File, Form, HTTPException
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func

from app.database import get_db
from app.models import Topic, PracticeSession, Recording
from app.config import settings
from app.services.asr_service import transcribe_audio, _estimate_word_timestamps, _looks_like_wav
from app.services.scoring_service import score_speaking
from app.services.pronunciation_service import assess_pronunciation_sync
from app.services.auth_service import get_current_user, User

router = APIRouter(prefix="/api/part2", tags=["Part 2"])
NO_SPEECH_DETAIL = (
    "Transcription failed - no speech detected. "
    "Please re-record and speak clearly into your microphone."
)


@router.get("/topics/random")
async def draw_topic(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Draw a random Part 2 topic card."""
    result = await db.execute(
        select(Topic).order_by(func.random()).limit(1)
    )
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


class CreateSessionRequest(BaseModel):
    topic_id: int


def _assert_session_access(session: PracticeSession, current_user: User) -> None:
    """Ensure a session can only be accessed by its owner."""
    if session.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="You do not have access to this session")


def _resolve_audio_extension(filename: str | None) -> str:
    ext = Path(filename or "").suffix.lower().lstrip(".")
    if ext in settings.ALLOWED_AUDIO_FORMATS:
        return ext
    raise HTTPException(
        status_code=400,
        detail=f"Unsupported audio format: .{ext or 'unknown'}",
    )


def _can_run_azure_pronunciation(audio_filename: str | None, audio_bytes: bytes) -> bool:
    return bool(audio_filename and audio_filename.lower().endswith(".wav") and _looks_like_wav(audio_bytes))


@router.post("/sessions")
async def create_session(
    request: CreateSessionRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Start a new practice session for Part 2."""
    # Verify topic exists
    topic = await db.get(Topic, request.topic_id)
    if not topic:
        raise HTTPException(status_code=404, detail="Topic not found")

    session = PracticeSession(topic_id=request.topic_id, status="in_progress", user_id=current_user.id)
    db.add(session)
    await db.flush()

    return {"session_id": session.id, "topic_id": request.topic_id, "status": "in_progress"}


@router.post("/sessions/{session_id}/upload-audio")
async def upload_audio(
    session_id: int,
    audio: UploadFile = File(...),
    notes: str = Form(default=""),
    client_transcript: str = Form(default=""),  # text from browser Web Speech API
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Upload Part 2 recording audio.
    Triggers ASR transcription and stores results.
    """
    # Verify session exists
    session = await db.get(PracticeSession, session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    _assert_session_access(session, current_user)

    # Read audio bytes
    audio_bytes = await audio.read()
    if len(audio_bytes) == 0:
        raise HTTPException(status_code=400, detail="Empty audio file")

    # Get topic info for context
    topic = await db.get(Topic, session.topic_id)
    question_text = ""
    if topic:
        question_text = topic.title + "\n" + "\n".join(f"- {p}" for p in topic.points)

    # Save audio file
    ext = _resolve_audio_extension(audio.filename)
    audio_filename = f"session_{session_id}_part2_{uuid.uuid4().hex[:8]}.{ext}"
    audio_path = settings.recordings_path / audio_filename
    with open(audio_path, "wb") as f:
        f.write(audio_bytes)

    # ASR transcription: prefer server ASR, then fall back to browser-finalized text.
    asr_result = await transcribe_audio(audio_bytes, audio_filename)
    if not asr_result.get("text") and client_transcript.strip():
        transcript = client_transcript.strip()
        words = _estimate_word_timestamps(transcript)
        asr_result = {"text": transcript, "words": words}

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

    return {
        "recording_id": recording.id,
        "transcript": asr_result["text"],
        "word_count": len(asr_result["words"]),
        "duration_seconds": recording.duration_seconds,
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
        raise HTTPException(status_code=400, detail="No recordings found for this session")

    # Get the Part 2 recording (primary)
    part2_recording = next((r for r in recordings if r.part == "part2"), recordings[0])

    if not part2_recording.transcript:
        raise HTTPException(status_code=422, detail=NO_SPEECH_DETAIL)

    # Get topic
    topic = await db.get(Topic, session.topic_id)
    question_text = ""
    if topic:
        question_text = topic.title + "\n" + "\n".join(f"- {p}" for p in topic.points)

    # Run pronunciation assessment (if audio file exists and Azure is configured)
    pron_data = None
    from app.config import settings as app_settings
    if app_settings.AZURE_SPEECH_KEY and part2_recording.audio_filename:
        audio_path = app_settings.recordings_path / part2_recording.audio_filename
        if audio_path.exists():
            audio_bytes = audio_path.read_bytes()
            if _can_run_azure_pronunciation(part2_recording.audio_filename, audio_bytes):
                # Azure SDK is synchronous 鈥?run in thread pool
                try:
                    pron_data = await asyncio.wait_for(
                        asyncio.to_thread(
                            assess_pronunciation_sync, audio_bytes, part2_recording.transcript
                        ),
                        timeout=max(1, app_settings.PRONUNCIATION_TIMEOUT_SECONDS),
                    )
                except asyncio.TimeoutError:
                    pron_data = None

    # Acoustic analysis (librosa)
    acoustic_data = None
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
            except Exception:
                acoustic_data = None

    # Run LLM scoring
    score_result = await score_speaking(
        transcript=part2_recording.transcript,
        question_text=question_text,
        part="part2",
        word_timestamps=part2_recording.word_timestamps,
        pronunciation_data=pron_data,
        acoustic_data=acoustic_data,
    )

    # Update session with scores
    if score_result.get("error") == "empty_transcript":
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
                "overall_feedback": score_result.get("overall_feedback", "Scoring failed."),
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

    return {
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
        history.append({
            "session_id": s.id,
            "topic_title": topic_title or "Unknown",
            "date": s.finished_at.isoformat() if s.finished_at else None,
            "scores": {
                "fluency": s.fluency_score,
                "vocabulary": s.vocabulary_score,
                "grammar": s.grammar_score,
                "pronunciation": s.pronunciation_score,
                "overall": s.overall_score,
            },
        })

    return history


