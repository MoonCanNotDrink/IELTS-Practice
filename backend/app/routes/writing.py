import json
from datetime import datetime
from typing import Any, cast

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models import WritingAttempt, WritingPrompt
from app.services.auth_service import get_current_user, User
from app.services.chart_generation_service import generate_chart_data
from app.services.writing_scoring_service import score_writing
from app.routes.helpers import parse_feedback_blob, feedback_error_info

router = APIRouter(prefix="/api/writing", tags=["Writing"])

VALID_TASK_TYPES = {"task1", "task2"}
MAX_ESSAY_CHARACTERS = 12000


def normalize_task_type(task_type: str) -> str:
    normalized = (task_type or "").strip().lower()
    if normalized not in VALID_TASK_TYPES:
        raise HTTPException(status_code=400, detail="task_type must be either 'task1' or 'task2'")
    return normalized


def assert_attempt_access(attempt: WritingAttempt, current_user: User) -> None:
    if cast(Any, attempt.user_id) != current_user.id:
        raise HTTPException(status_code=403, detail="You do not have access to this writing attempt")


def serialize_prompt(prompt: WritingPrompt) -> dict:
    return {
        "id": prompt.id,
        "slug": prompt.slug,
        "task_type": prompt.task_type,
        "title": prompt.title,
        "prompt_text": prompt.prompt_text,
        "prompt_details": prompt.prompt_details or {},
    }


def serialize_attempt_detail(attempt: WritingAttempt) -> dict:
    feedback = parse_feedback_blob(cast(str | None, attempt.feedback)) or {}
    scoring_status, scoring_error, scoring_error_detail = feedback_error_info(cast(str | None, attempt.feedback))
    return {
        "attempt_id": attempt.id,
        "module_type": "writing",
        "task_type": attempt.task_type,
        "title": attempt.prompt_title,
        "date": (lambda dt: dt.isoformat() if dt else None)(cast(Any, attempt.completed_at)),
        "status": "completed",
        "scoring_status": scoring_status,
        "scoring_error": scoring_error,
        "scoring_error_detail": scoring_error_detail,
        "prompt": {
            "title": attempt.prompt_title,
            "prompt_text": attempt.prompt_text,
            "prompt_details": attempt.prompt_details or {},
        },
        "essay_text": attempt.essay_text,
        "word_count": attempt.word_count,
        "scores": {
            "task": attempt.task_score,
            "coherence": attempt.coherence_score,
            "lexical": attempt.lexical_score,
            "grammar": attempt.grammar_score,
            "overall": attempt.overall_score,
        },
        "feedback": {
            "task": feedback.get("task_feedback", ""),
            "coherence": feedback.get("coherence_feedback", ""),
            "lexical": feedback.get("lexical_feedback", ""),
            "grammar": feedback.get("grammar_feedback", ""),
            "overall": feedback.get("overall_feedback", ""),
        },
        "key_improvements": feedback.get("key_improvements", []),
        "sample_answer": attempt.sample_answer or feedback.get("sample_answer", ""),
    }


class CreateWritingAttemptRequest(BaseModel):
    prompt_id: int | None = None
    custom_prompt: str | None = None
    custom_task_type: str | None = None
    essay_text: str


class GenerateChartRequest(BaseModel):
    prompt_text: str


@router.get("/prompts/random")
async def get_random_prompt(
    task_type: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    normalized_task_type = normalize_task_type(task_type)
    result = await db.execute(
        select(WritingPrompt)
        .where(WritingPrompt.task_type == normalized_task_type)
        .order_by(func.random())
        .limit(1)
    )
    prompt = result.scalars().first()
    if not prompt:
        raise HTTPException(status_code=404, detail="No writing prompts available")
    return serialize_prompt(prompt)


@router.get("/prompts")
async def list_prompts(
    task_type: str | None = None,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if task_type:
        normalized = normalize_task_type(task_type)
        result = await db.execute(select(WritingPrompt).where(WritingPrompt.task_type == normalized))
    else:
        result = await db.execute(select(WritingPrompt))
    prompts = result.scalars().all()
    return [serialize_prompt(p) for p in prompts]


@router.post("/generate-chart")
async def generate_chart(
    body: GenerateChartRequest,
    current_user: User = Depends(get_current_user),
):
    prompt_text = (body.prompt_text or "").strip()
    if not prompt_text:
        raise HTTPException(status_code=400, detail="prompt_text is required")

    result = await generate_chart_data(prompt_text)
    if "error" in result:
        return result

    return {"chart_data": result}


@router.post("/attempts")
async def create_writing_attempt(
    body: CreateWritingAttemptRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    essay_text = (body.essay_text or "").strip()
    if not essay_text:
        raise HTTPException(status_code=400, detail="essay_text is required")
    if len(essay_text) > MAX_ESSAY_CHARACTERS:
        raise HTTPException(status_code=400, detail=f"essay_text exceeds the {MAX_ESSAY_CHARACTERS} character limit")

    prompt = None
    prompt_title = None
    prompt_text = None
    prompt_task_type = None
    prompt_details = None

    if body.prompt_id is not None:
        prompt = await db.get(WritingPrompt, body.prompt_id)
        if not prompt:
            raise HTTPException(status_code=404, detail="Writing prompt not found")
        prompt_title = prompt.title
        prompt_text = prompt.prompt_text
        prompt_task_type = prompt.task_type
        prompt_details = prompt.prompt_details
    elif body.custom_prompt:
        if not body.custom_task_type:
            raise HTTPException(status_code=400, detail="custom_task_type is required for custom prompts")
        prompt_task_type = normalize_task_type(body.custom_task_type)
        prompt_title = body.custom_prompt
        prompt_text = body.custom_prompt
        prompt_details = {}
    else:
        raise HTTPException(status_code=400, detail="Either prompt_id or custom_prompt must be provided")

    word_count = len([token for token in essay_text.split() if token.strip()])
    task_type_arg = cast(str, prompt_task_type)
    prompt_title_arg = cast(str, prompt_title)
    prompt_text_arg = cast(str, prompt_text)
    score_result = await score_writing(
        task_type=task_type_arg,
        prompt_title=prompt_title_arg,
        prompt_text=prompt_text_arg,
        essay_text=essay_text,
    )

    if "error" in score_result:
        feedback_blob = json.dumps(
            {
                "overall_feedback": score_result.get("overall_feedback", "Scoring failed."),
                "task_feedback": score_result.get("task_feedback", ""),
                "coherence_feedback": score_result.get("coherence_feedback", ""),
                "lexical_feedback": score_result.get("lexical_feedback", ""),
                "grammar_feedback": score_result.get("grammar_feedback", ""),
                "error": score_result.get("error", "llm_generation_failed"),
                "detail": score_result.get("detail", ""),
                "key_improvements": score_result.get("key_improvements", []),
                "sample_answer": score_result.get("sample_answer", ""),
            },
            ensure_ascii=False,
        )
    else:
        feedback_blob = json.dumps(score_result, ensure_ascii=False)

    attempt = WritingAttempt(
        user_id=current_user.id,
        prompt_id=(prompt.id if prompt else None),
        task_type=prompt_task_type,
        prompt_title=prompt_title,
        prompt_text=prompt_text,
        prompt_details=prompt_details,
        essay_text=essay_text,
        word_count=word_count,
        task_score=score_result.get("task_score", 0.0),
        coherence_score=score_result.get("coherence_score", 0.0),
        lexical_score=score_result.get("lexical_score", 0.0),
        grammar_score=score_result.get("grammar_score", 0.0),
        overall_score=score_result.get("overall_score", 0.0),
        feedback=feedback_blob,
        sample_answer=score_result.get("sample_answer", ""),
        completed_at=datetime.utcnow(),
    )
    db.add(attempt)
    await db.flush()

    return serialize_attempt_detail(attempt)


@router.get("/attempts/{attempt_id}/detail")
async def get_writing_attempt_detail(
    attempt_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    attempt = await db.get(WritingAttempt, attempt_id)
    if not attempt:
        raise HTTPException(status_code=404, detail="Writing attempt not found")
    assert_attempt_access(attempt, current_user)
    return serialize_attempt_detail(attempt)
