import asyncio
import json
import logging
import re

import google.generativeai as genai
from google.generativeai.types import HarmCategory, HarmBlockThreshold

from app.config import settings

logger = logging.getLogger(__name__)

genai.configure(api_key=settings.GEMINI_API_KEY)

WRITING_SYSTEM_INSTRUCTION = """You are an experienced IELTS Writing examiner.
Evaluate the submitted IELTS Writing response strictly according to the official IELTS Writing band descriptors.

Rules:
- Score each dimension from 1.0 to 9.0 in increments of 0.5.
- Use realistic scoring. Most responses should fall between 5.0 and 7.0.
- Return ONLY valid JSON. No markdown, no code fences.
- All feedback text should be in English.

Return JSON using this exact schema:
{
  \"task_score\": 6.5,
  \"task_feedback\": \"Clear task-focused feedback.\",
  \"coherence_score\": 6.0,
  \"coherence_feedback\": \"Clear organisation feedback.\",
  \"lexical_score\": 6.0,
  \"lexical_feedback\": \"Clear vocabulary feedback.\",
  \"grammar_score\": 6.0,
  \"grammar_feedback\": \"Clear grammar feedback.\",
  \"overall_score\": 6.0,
  \"overall_feedback\": \"Short overall evaluation.\",
  \"key_improvements\": [\"Item 1\", \"Item 2\"],
  \"sample_answer\": \"Optional short sample paragraph or structure guidance.\"
}"""


def extract_json(text: str) -> dict:
    stripped = (text or "").strip()
    if not stripped:
        return {"error": "empty_response", "detail": "The model returned an empty response."}

    try:
        return json.loads(stripped)
    except json.JSONDecodeError:
        pass

    fence_match = re.search(r"```(?:json)?\s*\n([\s\S]*?)\n\s*```", stripped, re.IGNORECASE)
    if fence_match:
        candidate = fence_match.group(1).strip()
        try:
            return json.loads(candidate)
        except json.JSONDecodeError:
            pass

    first_brace = stripped.find("{")
    last_brace = stripped.rfind("}")
    if first_brace != -1 and last_brace > first_brace:
        candidate = stripped[first_brace:last_brace + 1]
        try:
            return json.loads(candidate)
        except json.JSONDecodeError:
            pass

    return {
        "error": "invalid_json",
        "detail": "Failed to parse the writing scoring response as JSON.",
        "raw_response": stripped[:2000],
    }


async def score_writing(task_type: str, prompt_title: str, prompt_text: str, essay_text: str) -> dict:
    if not essay_text or not essay_text.strip():
        return {
            "error": "empty_essay",
            "detail": "Essay text is required.",
            "task_score": 0.0,
            "coherence_score": 0.0,
            "lexical_score": 0.0,
            "grammar_score": 0.0,
            "overall_score": 0.0,
            "overall_feedback": "No essay text was submitted.",
            "task_feedback": "-",
            "coherence_feedback": "-",
            "lexical_feedback": "-",
            "grammar_feedback": "-",
            "key_improvements": ["Submit a non-empty essay response."],
            "sample_answer": "",
        }

    model = genai.GenerativeModel(
        model_name=settings.GEMINI_MODEL,
        system_instruction=WRITING_SYSTEM_INSTRUCTION,
    )
    user_prompt = (
        f"## IELTS Writing Assessment\n\n"
        f"### Task Type\n{task_type}\n\n"
        f"### Prompt Title\n{prompt_title}\n\n"
        f"### Prompt\n{prompt_text}\n\n"
        f"### Candidate Response\n{essay_text}\n\n"
        f"Evaluate this response and return only the JSON object described in your instructions."
    )

    try:
        response = await asyncio.wait_for(
            model.generate_content_async(
                user_prompt,
                generation_config=genai.GenerationConfig(
                    temperature=0.2,
                    max_output_tokens=4096,
                ),
                safety_settings={
                    HarmCategory.HARM_CATEGORY_HATE_SPEECH: HarmBlockThreshold.BLOCK_NONE,
                    HarmCategory.HARM_CATEGORY_HARASSMENT: HarmBlockThreshold.BLOCK_NONE,
                    HarmCategory.HARM_CATEGORY_SEXUALLY_EXPLICIT: HarmBlockThreshold.BLOCK_NONE,
                    HarmCategory.HARM_CATEGORY_DANGEROUS_CONTENT: HarmBlockThreshold.BLOCK_NONE,
                },
            ),
            timeout=max(1, settings.GEMINI_TIMEOUT_SECONDS),
        )
        raw_text = response.text or ""
        if not raw_text:
            raise ValueError("Gemini returned empty text")
        return extract_json(raw_text)
    except Exception as exc:
        logger.error("score_writing failed: %s", exc, exc_info=True)
        return {
            "error": "llm_generation_failed",
            "detail": str(exc),
            "task_score": 0.0,
            "coherence_score": 0.0,
            "lexical_score": 0.0,
            "grammar_score": 0.0,
            "overall_score": 0.0,
            "overall_feedback": f"Scoring failed: {exc}",
            "task_feedback": "-",
            "coherence_feedback": "-",
            "lexical_feedback": "-",
            "grammar_feedback": "-",
            "key_improvements": ["The writing response could not be scored automatically."],
            "sample_answer": "",
        }
