"""Full-exam scoring route 鈥?combines Part 1 + Part 2 + Part 3 for final assessment."""

import json
import asyncio
import base64
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, Response
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
import httpx

from app.database import get_db
from app.models import PracticeSession, Recording, Topic
from app.services.scoring_service import score_speaking
from app.services.pronunciation_service import assess_pronunciation_sync
from app.services.auth_service import get_current_user, User
from app.config import settings

router = APIRouter(prefix="/api/scoring", tags=["Scoring"])


def _assert_session_access(session: PracticeSession, current_user: User) -> None:
    """Ensure a session can only be accessed by its owner."""
    if session.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="You do not have access to this session")


def _determine_exam_scope(recorded_parts: set[str], is_full_flow: bool) -> str:
    if is_full_flow:
        return "full_exam"
    if recorded_parts == {"part2"}:
        return "part2_only"
    return "partial_exam"


def _parse_feedback_blob(raw_feedback: str | None) -> dict | None:
    if not raw_feedback:
        return None

    import ast

    try:
        parsed = json.loads(raw_feedback)
    except Exception:
        try:
            parsed = ast.literal_eval(raw_feedback)
        except Exception:
            parsed = None

    return parsed if isinstance(parsed, dict) else None


def _feedback_error_info(raw_feedback: str | None) -> tuple[str, str, str]:
    parsed = _parse_feedback_blob(raw_feedback)
    if not parsed or not parsed.get("error"):
        return "ok", "", ""
    return "error", str(parsed.get("error", "")), str(parsed.get("detail", ""))


def _is_valid_wav_payload(audio_filename: str | None, audio_bytes: bytes) -> bool:
    return bool(
        audio_filename
        and audio_filename.lower().endswith(".wav")
        and len(audio_bytes) >= 12
        and audio_bytes[:4] == b"RIFF"
        and audio_bytes[8:12] == b"WAVE"
    )


def _build_combined_transcript(recordings: list) -> tuple[str, str, str, str, list]:
    """
    Build per-part transcripts and a combined full transcript.
    Returns (full_transcript, part1_text, part2_text, part3_text).
    """
    parts = {"part1": [], "part2": [], "part3": []}
    word_timestamps = []

    for r in sorted(recordings, key=lambda x: (x.part, x.question_index)):
        if r.part not in parts:
            continue
        if r.transcript:
            qa = f"Q: {r.question_text}\nA: {r.transcript}" if r.question_text else r.transcript
            parts[r.part].append(qa)
        # Use Part 2 timestamps for fluency (it's the longest monologue)
        if r.part == "part2" and r.word_timestamps:
            word_timestamps = r.word_timestamps

    part1_text = "\n\n".join(parts["part1"]) or "No Part 1 recording."
    part2_text = "\n\n".join(parts["part2"]) or "No Part 2 recording."
    part3_text = "\n\n".join(parts["part3"]) or "No Part 3 recording."

    full_transcript = (
        f"=== PART 1 ===\n{part1_text}\n\n"
        f"=== PART 2 ===\n{part2_text}\n\n"
        f"=== PART 3 ===\n{part3_text}"
    )

    return full_transcript, part1_text, part2_text, part3_text, word_timestamps


@router.post("/sessions/{session_id}/score")
async def score_full_session(
    session_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Score a completed IELTS mock exam session (Part 1 + 2 + 3).
    Runs pronunciation assessment + LLM scoring and persists results.
    """
    session = await db.get(PracticeSession, session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    _assert_session_access(session, current_user)

    rec_result = await db.execute(
        select(Recording)
        .where(Recording.session_id == session_id)
        .order_by(Recording.part, Recording.question_index)
    )
    recordings = rec_result.scalars().all()
    if not recordings:
        raise HTTPException(status_code=400, detail="No recordings for this session")
    recorded_parts = {r.part for r in recordings if (r.transcript or "").strip()}
    required_parts = ("part1", "part2", "part3")
    missing_parts = [p for p in required_parts if p not in recorded_parts]
    is_full_flow = len(missing_parts) == 0
    exam_scope = _determine_exam_scope(recorded_parts, is_full_flow)

    topic = await db.get(Topic, session.topic_id) if session.topic_id else None

    # Build combined transcript
    full_transcript, p1, p2, p3, word_timestamps = _build_combined_transcript(recordings)

    question_text = (
        f"{topic.title}\nYou should say:\n" + "\n".join(f"- {pt}" for pt in topic.points)
        if topic else "Full IELTS Speaking Mock Test"
    )

    # Pronunciation: use Part 2 audio (longest monologue)
    pron_data = None
    part2_rec = next((r for r in recordings if r.part == "part2" and r.audio_filename), None)
    if part2_rec and settings.AZURE_SPEECH_KEY:
        audio_path = settings.recordings_path / part2_rec.audio_filename
        if audio_path.exists() and part2_rec.transcript:
            audio_bytes = audio_path.read_bytes()
            if _is_valid_wav_payload(part2_rec.audio_filename, audio_bytes):
                try:
                    pron_data = await asyncio.wait_for(
                        asyncio.to_thread(
                            assess_pronunciation_sync, audio_bytes, part2_rec.transcript
                        ),
                        timeout=max(1, settings.PRONUNCIATION_TIMEOUT_SECONDS),
                    )
                except (Exception, asyncio.TimeoutError):
                    pron_data = None

    # Acoustic analysis (librosa) on Part 2 audio
    acoustic_data = None
    from app.services.acoustic_service import analyze_audio_fluency_sync
    if part2_rec and part2_rec.transcript:
        audio_path = settings.recordings_path / part2_rec.audio_filename
        if audio_path.exists():
            word_count = len(part2_rec.transcript.split())
            try:
                acoustic_data = await asyncio.to_thread(
                    analyze_audio_fluency_sync, str(audio_path), word_count
                )
            except Exception:
                acoustic_data = None

    # LLM scoring 鈥?send full combined transcript
    score_result = await score_speaking(
        transcript=full_transcript,
        question_text=question_text,
        part="full exam (Part 1 + Part 2 + Part 3)",
        word_timestamps=word_timestamps,
        pronunciation_data=pron_data,
        acoustic_data=acoustic_data,
    )

    # Persist scores
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

    if pron_data and "error" not in pron_data and part2_rec:
        part2_rec.pronunciation_accuracy = pron_data.get("accuracy_score")
        part2_rec.pronunciation_details = pron_data

    session.status = "completed"
    session.finished_at = datetime.utcnow()

    return {
        "session_id": session_id,
        "exam_scope": exam_scope,
        "is_full_flow": is_full_flow,
        "missing_parts": missing_parts,
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
        "transcripts": {"part1": p1, "part2": p2, "part3": p3},
    }


@router.get("/history")
async def get_history(
    limit: int = 20,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Return recent completed sessions with scores for trend chart."""
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
        scoring_status, scoring_error, scoring_error_detail = _feedback_error_info(s.feedback)
        history.append({
            "session_id": s.id,
            "topic_title": topic_title or "Unknown",
            "date": s.finished_at.isoformat() if s.finished_at else None,
            "scoring_status": scoring_status,
            "scoring_error": scoring_error,
            "scoring_error_detail": scoring_error_detail,
            "scores": {
                "fluency": s.fluency_score,
                "vocabulary": s.vocabulary_score,
                "grammar": s.grammar_score,
                "pronunciation": s.pronunciation_score,
                "overall": s.overall_score,
            },
        })

    return history


@router.get("/sessions/{session_id}/detail")
async def get_session_detail(
    session_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Return full scoring results for a specific session (for history review)."""
    session = await db.get(PracticeSession, session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    _assert_session_access(session, current_user)

    # Fetch topic and recordings
    topic = await db.get(Topic, session.topic_id) if session.topic_id else None
    result = await db.execute(
        select(Recording)
        .where(Recording.session_id == session_id)
        .order_by(Recording.part, Recording.question_index)
    )
    recordings = result.scalars().all()
    recorded_parts = {r.part for r in recordings if (r.transcript or "").strip()}
    required_parts = ("part1", "part2", "part3")
    missing_parts = [p for p in required_parts if p not in recorded_parts]
    is_full_flow = len(missing_parts) == 0
    exam_scope = _determine_exam_scope(recorded_parts, is_full_flow)

    # Build transcripts per part
    transcripts = {}
    for r in recordings:
        if r.transcript:
            part_key = r.part  # 'part1','part2','part3'
            transcripts[part_key] = (transcripts.get(part_key, '') + ' ' + r.transcript).strip()

    feedback = {}
    key_improvements = []
    sample_answer = ""
    scoring_status, scoring_error, scoring_error_detail = _feedback_error_info(session.feedback)
    if session.feedback:
        fb = _parse_feedback_blob(session.feedback)
        if isinstance(fb, dict):
            feedback = {
                "fluency": fb.get("fluency_feedback", ""),
                "vocabulary": fb.get("vocabulary_feedback", ""),
                "grammar": fb.get("grammar_feedback", ""),
                "pronunciation": fb.get("pronunciation_feedback", ""),
                "overall": fb.get("overall_feedback", ""),
            }
            key_improvements = fb.get("key_improvements", [])
            sample_answer = fb.get("sample_answer", "")
        elif isinstance(session.feedback, str) and session.feedback.strip():
            feedback = {"overall": session.feedback}

    return {
        "session_id": session_id,
        "topic_title": topic.title if topic else "Unknown",
        "date": session.finished_at.isoformat() if session.finished_at else None,
        "exam_scope": exam_scope,
        "is_full_flow": is_full_flow,
        "missing_parts": missing_parts,
        "scores": {
            "fluency": session.fluency_score,
            "vocabulary": session.vocabulary_score,
            "grammar": session.grammar_score,
            "pronunciation": session.pronunciation_score,
            "overall": session.overall_score,
        },
        "scoring_status": scoring_status,
        "scoring_error": scoring_error,
        "scoring_error_detail": scoring_error_detail,
        "feedback": feedback,
        "key_improvements": key_improvements,
        "sample_answer": session.sample_answer or sample_answer,
        "transcripts": transcripts,
    }

class TTSRequest(BaseModel):
    text: str
    voice_name: str = "Aoede"

async def _generate_tts_response(req: TTSRequest) -> Response:
    """
    Generate examiner TTS using Gemini 2.5 Flash Native Audio.
    Proxies the request to avoid CORS and SSL blockages on the client.
    """
    if not settings.GEMINI_API_KEY:
        raise HTTPException(status_code=500, detail="GEMINI_API_KEY not configured")

    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash-preview-tts:generateContent?key={settings.GEMINI_API_KEY}"
    
    payload = {
      "contents": [{"parts": [{"text": req.text}]}],
      "generationConfig": {
        "responseModalities": ["AUDIO"],
        "speechConfig": {
          "voiceConfig": {
            "prebuiltVoiceConfig": {
              "voiceName": req.voice_name
            }
          }
        }
      }
    }
    
    async with httpx.AsyncClient(timeout=15.0) as client:
        try:
            res = await client.post(url, json=payload)
            res.raise_for_status()
            data = res.json()
            
            # Extract base64 audio from response
            parts = data.get('candidates', [{}])[0].get('content', {}).get('parts', [])
            for p in parts:
                if 'inlineData' in p and p['inlineData']['mimeType'].startswith("audio/"):
                    audio_b64 = p['inlineData']['data']
                    audio_bytes = base64.b64decode(audio_b64)
                    return Response(content=audio_bytes, media_type=p['inlineData']['mimeType'])
            
            raise HTTPException(status_code=500, detail="Gemini response contained no audio data.")
        except httpx.HTTPStatusError as e:
            error_body = e.response.text
            raise HTTPException(status_code=e.response.status_code, detail=f"Gemini API Error: {error_body}")
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))


@router.post("/tts")
async def generate_tts(req: TTSRequest, current_user: User = Depends(get_current_user)):
    return await _generate_tts_response(req)


