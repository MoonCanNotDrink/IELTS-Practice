"""API routes for Part 1 and Part 3 鈥?dynamic AI examiner with follow-up questions."""

import uuid
from datetime import datetime
from typing import Literal
from fastapi import APIRouter, Depends, UploadFile, File, Form, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
import google.generativeai as genai

from app.database import get_db
from app.models import PracticeSession, Recording, Topic
from app.services.asr_service import transcribe_audio, _estimate_word_timestamps
from app.services.auth_service import get_current_user, User
from app.config import settings
from app.routes.helpers import assert_session_access as _assert_session_access, resolve_audio_extension as _resolve_audio_extension

router = APIRouter(prefix="/api/exam", tags=["Full Exam"])

genai.configure(api_key=settings.GEMINI_API_KEY)
VALID_RECORDING_PARTS = {"part1", "part2", "part3"}
FOLLOWUP_PARTS = {"part1", "part3"}

# 鈹€鈹€鈹€ Part 1 question bank 鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€
# Organized by topic 鈥?the examiner picks ~4-5 questions from one topic
PART1_TOPICS = {
    "Hometown": [
        "Where are you from originally?",
        "What do you like most about your hometown?",
        "Has your hometown changed much since you were a child?",
        "Would you like to live in your hometown in the future? Why or why not?",
        "Is your hometown a good place for young people to live?",
    ],
    "Work or Study": [
        "Do you work or are you a student?",
        "What do you do in your job / What are you studying?",
        "Why did you choose this job / subject?",
        "What do you enjoy most about your work or studies?",
        "Would you like to change your career or field of study in the future?",
    ],
    "Free Time": [
        "What do you enjoy doing in your free time?",
        "Has the way you spend your free time changed over the years?",
        "Do you think people today have more or less free time than in the past?",
        "What activities would you like to try in the future?",
        "Is it important to have hobbies? Why?",
    ],
    "Travel": [
        "Do you enjoy travelling?",
        "What kinds of places do you most like to visit?",
        "Have you ever been abroad?",
        "What is the most interesting place you have visited?",
        "How has travel changed your outlook on life?",
    ],
    "Technology": [
        "How important is technology in your daily life?",
        "What kind of technology do you use most often?",
        "Do you think people rely on technology too much?",
        "What technology did you use as a child?",
        "How has technology changed the way people communicate?",
    ],
    "Food": [
        "Do you enjoy cooking?",
        "What is your favourite food?",
        "Has your diet changed over the years?",
        "Do you prefer eating at home or in restaurants?",
        "Do you think people today eat more healthily than in the past?",
    ],
}

# Part 3 questions keyed to topic categories
PART3_QUESTIONS = {
    "people": [
        "Do you think people are influenced more by their family or their friends? Why?",
        "How has the way people make friends changed in recent years?",
        "Do you think it's important to maintain relationships with people we don't see often?",
        "In what ways can influential people have a negative effect on society?",
        "How do you think society will change the way it values different professions in the future?",
    ],
    "places": [
        "Do you think cities are becoming too crowded? What are the consequences?",
        "How important is it for governments to invest in public spaces?",
        "Do you think tourism has had a mostly positive or negative effect on popular destinations?",
        "How has urbanisation changed people's lifestyle in your country?",
        "What measures can be taken to reduce environmental damage caused by tourism?",
    ],
    "experiences": [
        "Do you think taking risks is an important part of life? Why?",
        "How valuable is it to learn from our own mistakes versus learning from others?",
        "Do you think young people today face more challenges than previous generations?",
        "How has the definition of success changed in modern society?",
        "Should governments encourage people to take more calculated risks? How?",
    ],
    "objects": [
        "How has technology changed the products people buy and use?",
        "Do you think people are becoming too materialistic?",
        "Should manufacturers be responsible for making products more environmentally friendly?",
        "How does advertising influence what people choose to buy?",
        "Do you think the quality of products has improved or declined over time?",
    ],
    "culture": [
        "How important is it for countries to preserve their traditional culture?",
        "Do you think globalisation is causing cultures to become more similar?",
        "Should governments fund traditional arts and cultural events?",
        "How can young people be encouraged to appreciate their cultural heritage?",
        "What are the advantages and disadvantages of a multicultural society?",
    ],
    "media": [
        "How has the rise of social media changed the way people communicate?",
        "Do you think the media has too much influence on public opinion?",
        "Should there be stricter controls on what can be published online?",
        "How important is it for people to read books in the digital age?",
        "Do you think entertainment today is more or less meaningful than in the past?",
    ],
    "education": [
        "Do you think the education system in your country prepares young people for the real world?",
        "Should schools focus more on academic subjects or practical skills?",
        "How has technology changed the way people learn?",
        "Do you think homework should be abolished?",
        "What are the advantages and disadvantages of studying abroad?",
    ],
    "general": [
        "How has globalisation affected people's daily lives?",
        "Do you think technology is making people's lives better or worse overall?",
        "Should governments or individuals take more responsibility for social problems?",
        "How important is it for societies to encourage innovation?",
        "What changes would most improve the quality of life in modern society?",
    ],
}


def _get_part3_questions(topic_category: str | None) -> list[str]:
    """Return Part 3 questions appropriate for the given topic category."""
    if topic_category and topic_category in PART3_QUESTIONS:
        return PART3_QUESTIONS[topic_category]
    return PART3_QUESTIONS["general"]


# 鈹€鈹€鈹€ Models 鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€

class StartExamRequest(BaseModel):
    topic_id: int  # Part 2 topic to use (determines Part 3 category)


class AnswerRequest(BaseModel):
    session_id: int
    part: str        # "part1" | "part3"
    question_index: int
    question_text: str


class NextQuestionRequest(BaseModel):
    part: Literal["part1", "part3"]
    topic_name: str   # e.g., "Hometown" or "Technology"
    current_index: int = Field(ge=0)


# 鈹€鈹€鈹€ Examiner AI 鈥?dynamic follow-up generator 鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€

EXAMINER_SYSTEM = """You are an IELTS speaking examiner conducting a live speaking test.
Your job is to generate the NEXT question to ask the candidate based on their previous answer.
You must keep the conversation natural, professional, and follow IELTS Part 1 or Part 3 guidelines.

Rules:
- Part 1: Ask short, personal, everyday questions. Keep it conversational. 2-4 sentences max per question.
- Part 3: Ask abstract, analytical, society-level questions. Encourage extended responses.
- Follow up naturally on what the candidate said 鈥?make it feel like a real conversation, not a fixed questionnaire.
- After 4-5 questions in a part, signal it's time to move on.

Respond ONLY with valid JSON:
{
    "question": "The next question to ask...",
    "is_final": false,
    "transition_note": ""
}
If this should be the LAST question in this part, set "is_final": true and optionally add a "transition_note"."""


async def generate_followup_question(
    part: str,
    topic: str,
    conversation_history: list[dict],
    question_index: int,
    max_questions: int = 5,
) -> dict:
    """Generate the next examiner question using Gemini."""
    is_last = question_index >= max_questions - 1

    history_text = "\n".join(
        f"Q{i+1}: {turn['question']}\nA: {turn['answer']}"
        for i, turn in enumerate(conversation_history)
    )

    prompt = (
        f"IELTS Speaking {part.upper()} 鈥?Topic area: {topic}\n\n"
        f"Conversation so far:\n{history_text or 'None yet.'}\n\n"
        f"Question index: {question_index + 1} of {max_questions}.\n"
        f"{'This should be the LAST question 鈥?wrap up naturally.' if is_last else 'Generate the next logical question.'}\n\n"
        f"Return ONLY the JSON object."
    )

    model = genai.GenerativeModel(
        model_name=settings.GEMINI_MODEL,
        system_instruction=EXAMINER_SYSTEM,
    )
    response = await model.generate_content_async(
        prompt,
        generation_config=genai.GenerationConfig(temperature=0.7, max_output_tokens=300),
    )

    import re, json as _json
    text = response.text.strip()
    text = re.sub(r'^```(?:json)?\s*', '', text, flags=re.MULTILINE)
    text = re.sub(r'\s*```\s*$', '', text, flags=re.MULTILINE)
    try:
        return _json.loads(text.strip())
    except Exception:
        match = re.search(r'\{[\s\S]*\}', text)
        if match:
            try:
                return _json.loads(match.group())
            except Exception:
                pass
    return {"question": "Thank you for your answer. Could you tell me more?", "is_final": False, "transition_note": ""}


# 鈹€鈹€鈹€ Routes 鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€

@router.post("/start")
async def start_full_exam(
    request: StartExamRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Start a full IELTS mock exam session.
    Returns the session ID and the first Part 1 question.
    """
    import random

    topic = await db.get(Topic, request.topic_id)
    if not topic:
        raise HTTPException(status_code=404, detail="Topic not found")

    session = PracticeSession(topic_id=request.topic_id, status="in_progress", user_id=current_user.id)
    db.add(session)
    await db.flush()

    # Select a Part 1 topic and get questions
    part1_topic_name = random.choice(list(PART1_TOPICS.keys()))
    questions = PART1_TOPICS[part1_topic_name]
    first_question = questions[0]  # Always start with Q1

    return {
        "session_id": session.id,
        "part": "part1",
        "part1_topic": part1_topic_name,
        "question_index": 0,
        "question_text": first_question,
        "total_questions": len(questions),
        "all_questions": questions,  # Send all questions upfront for Part 1
    }


@router.post("/sessions/{session_id}/upload-part-audio")
async def upload_part_audio(
    session_id: int,
    audio: UploadFile = File(...),
    part: str = Form(...),
    question_index: int = Form(...),
    question_text: str = Form(default=""),
    notes: str = Form(default=""),
    client_transcript: str = Form(default=""),  # from browser Web Speech API
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Upload audio for Part 1 or Part 3 (and Part 2).
    Runs ASR and stores the recording.
    """
    session = await db.get(PracticeSession, session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    _assert_session_access(session, current_user)
    if part not in VALID_RECORDING_PARTS:
        raise HTTPException(status_code=400, detail=f"Invalid part: {part}")
    if question_index < 0:
        raise HTTPException(status_code=400, detail="question_index must be >= 0")

    audio_bytes = await audio.read()
    if not audio_bytes:
        raise HTTPException(status_code=400, detail="Empty audio file")

    # Save audio
    ext = _resolve_audio_extension(audio.filename)
    audio_filename = f"session_{session_id}_{part}_{question_index}_{uuid.uuid4().hex[:6]}.{ext}"
    audio_path = settings.recordings_path / audio_filename
    with open(audio_path, "wb") as f:
        f.write(audio_bytes)

    # ASR: prefer server transcription, then fall back to browser-finalized text.
    asr_result = await transcribe_audio(audio_bytes, audio_filename)
    if not asr_result.get("text") and client_transcript.strip():
        transcript = client_transcript.strip()
        words = _estimate_word_timestamps(transcript)
        asr_result = {"text": transcript, "words": words}

    recording = Recording(
        session_id=session_id,
        part=part,
        question_index=question_index,
        question_text=question_text,
        audio_filename=audio_filename,
        transcript=asr_result["text"],
        word_timestamps=asr_result["words"],
        notes=notes,
    )
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


@router.get("/sessions/{session_id}/part3-questions")
async def get_part3_questions(
    session_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Return the FIRST Part 3 question for this session's topic category."""
    import random
    session = await db.get(PracticeSession, session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    _assert_session_access(session, current_user)

    topic = await db.get(Topic, session.topic_id) if session.topic_id else None
    category = topic.category if topic else "general"
    questions = _get_part3_questions(category)

    first_question = random.choice(questions)

    return {
        "category": category,
        "first_question": first_question,
    }


@router.post("/sessions/{session_id}/next-question")
async def get_next_question(
    session_id: int,
    request: NextQuestionRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Generate the dynamic follow-up question based on conversation history.
    """
    session = await db.get(PracticeSession, session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    _assert_session_access(session, current_user)

    result = await db.execute(
        select(Recording)
        .where(Recording.session_id == session_id, Recording.part == request.part)
        .order_by(Recording.question_index)
    )
    recordings = result.scalars().all()

    conversation_history = [
        {"question": r.question_text, "answer": r.transcript}
        for r in recordings if r.transcript
    ]

    next_q_data = await generate_followup_question(
        part=request.part,
        topic=request.topic_name,
        conversation_history=conversation_history,
        question_index=request.current_index,
        max_questions=5,
    )

    return next_q_data


@router.post("/sessions/{session_id}/complete")
async def complete_session(
    session_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Mark the session as ready-for-scoring after all parts are recorded.
    Returns combined transcripts for scoring.
    """
    session = await db.get(PracticeSession, session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    _assert_session_access(session, current_user)

    result = await db.execute(
        select(Recording)
        .where(Recording.session_id == session_id)
        .order_by(Recording.part, Recording.question_index)
    )
    recordings = result.scalars().all()

    # Build combined transcript by part
    parts = {"part1": [], "part2": [], "part3": []}
    for r in recordings:
        if r.transcript:
            if r.part not in parts:
                continue
            parts[r.part].append({
                "q": r.question_text or "",
                "a": r.transcript,
            })

    return {
        "session_id": session_id,
        "parts": parts,
        "recording_count": len(recordings),
    }

