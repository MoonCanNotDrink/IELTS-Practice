"""Gemini LLM scoring service — IELTS four-dimension assessment."""

import json
import re
import logging
import google.generativeai as genai
from google.generativeai.types import HarmCategory, HarmBlockThreshold
from app.config import settings

logger = logging.getLogger(__name__)

logger.info("Configuring Gemini with API key: %s...", settings.GEMINI_API_KEY[:10] if settings.GEMINI_API_KEY else "EMPTY")
genai.configure(api_key=settings.GEMINI_API_KEY)

SCORING_SYSTEM_INSTRUCTION = """You are an experienced IELTS speaking examiner with 15+ years of experience.
You must evaluate a candidate's speaking performance strictly according to the official IELTS Band Descriptors.

IMPORTANT SCORING RULES:
- Score each dimension from 1.0 to 9.0, in increments of 0.5
- Be realistic and strict — most candidates score between 5.0 and 7.0
- Always cite specific examples from the transcript to justify your scores
- The overall band score is the average of four dimensions, rounded to nearest 0.5
- You MUST respond ONLY with valid JSON. No markdown, no code fences, no explanation before or after.
- ALL feedback text fields (fluency_feedback, vocabulary_feedback, grammar_feedback, pronunciation_feedback, overall_feedback, key_improvements, sample_answer) MUST be written in Simplified Chinese (简体中文). Do NOT use English in any text field.

The JSON must follow this exact schema:
{
    "fluency_score": 6.5,
    "fluency_feedback": "（中文评价）你的回答整体流利，但出现了几处明显的停顿……",
    "vocabulary_score": 6.0,
    "vocabulary_feedback": "（中文评价）词汇范围较为合理……",
    "grammar_score": 6.0,
    "grammar_feedback": "（中文评价）你使用了简单和复杂句型的组合……",
    "pronunciation_score": 6.5,
    "pronunciation_feedback": "（中文评价）发音整体清晰……",
    "overall_score": 6.5,
    "overall_feedback": "（中文总评）整体来看，你的表现……",
    "key_improvements": [
        "减少犹豫停顿，练习限时回答",
        "扩充该话题的词汇量，特别是搭配词",
        "练习使用条件句等复杂句型"
    ],
    "sample_answer": "（中文旁注 + 英文范文）以下是本题的7分以上范例回答：..."
}"""


def _build_fluency_context(word_timestamps: list[dict]) -> str:
    """Analyze word timestamps to provide quantitative fluency data to the LLM."""
    if not word_timestamps or len(word_timestamps) < 2:
        return "No timing data available."

    speech_start = word_timestamps[0]["start"]
    speech_end = word_timestamps[-1]["end"]
    total_duration = speech_end - speech_start
    total_words = len(word_timestamps)

    wpm = (total_words / total_duration * 60) if total_duration > 0 else 0

    # Detect pauses > 0.8s
    pauses = []
    for i in range(1, total_words):
        gap = word_timestamps[i]["start"] - word_timestamps[i - 1]["end"]
        if gap > 0.8:
            pauses.append({
                "after_word": word_timestamps[i - 1]["word"],
                "before_word": word_timestamps[i]["word"],
                "duration": round(gap, 2),
            })

    long_pause_count = sum(1 for p in pauses if p["duration"] > 2.0)

    context = (
        f"FLUENCY METRICS (from audio analysis):\n"
        f"- Total speaking time: {total_duration:.1f} seconds\n"
        f"- Word count: {total_words}\n"
        f"- Speaking rate: {wpm:.0f} words/minute "
        f"(native average 120-150 WPM; IELTS Band 7+ typically 100-130 WPM)\n"
        f"- Pauses > 0.8s: {len(pauses)} occurrences\n"
        f"- Long pauses > 2.0s: {long_pause_count} occurrences"
    )

    if pauses:
        context += "\n- Pause details:"
        for p in pauses[:10]:
            context += (
                f'\n  • {p["duration"]}s pause between '
                f'"{p["after_word"]}" and "{p["before_word"]}"'
            )

    return context


def _extract_json(text: str) -> dict:
    """Robustly extract a JSON object from LLM output.
    
    Handles multiple formats Gemini may return:
    - Raw JSON
    - ```json\n{...}\n```  (markdown code fence)
    - ```\n{...}\n```  (plain code fence)
    - Text before/after JSON
    """
    logger.info("_extract_json: input length=%d, first 300 chars: %r", len(text), text[:300])
    original = text
    text = text.strip()

    # 1. Try direct parse (clean JSON with no wrapping)
    try:
        result = json.loads(text)
        logger.info("_extract_json: direct parse succeeded, keys=%s", list(result.keys()))
        return result
    except json.JSONDecodeError as e:
        logger.info("_extract_json: direct parse failed: %s", e)

    # 2. Strip markdown code fences explicitly
    # Match: ```json\n...\n``` or ```\n...\n```
    fence_pattern = re.compile(r'```(?:json)?\s*\n([\s\S]*?)\n\s*```', re.IGNORECASE)
    fence_match = fence_pattern.search(text)
    if fence_match:
        inner = fence_match.group(1).strip()
        logger.info("_extract_json: found code fence, inner length=%d, first 200: %r", len(inner), inner[:200])
        try:
            result = json.loads(inner)
            logger.info("_extract_json: fence-stripped parse succeeded, keys=%s", list(result.keys()))
            return result
        except json.JSONDecodeError as e:
            logger.info("_extract_json: fence-stripped parse failed: %s", e)

    # 3. Find first { and last } and try to parse everything between them
    first_brace = text.find('{')
    last_brace = text.rfind('}')
    if first_brace != -1 and last_brace > first_brace:
        candidate = text[first_brace:last_brace + 1]
        logger.info("_extract_json: trying brace extraction [%d:%d], length=%d", first_brace, last_brace + 1, len(candidate))
        try:
            result = json.loads(candidate)
            logger.info("_extract_json: brace extraction succeeded, keys=%s", list(result.keys()))
            return result
        except json.JSONDecodeError as e:
            logger.info("_extract_json: brace extraction failed: %s", e)
            
    # 4. Try parsing a truncated JSON string (missing closing brace)
    if first_brace != -1 and last_brace == -1:
        # Extreme fallback: auto-append missing '}' and any likely missing quotes
        logger.info("_extract_json: output appears truncated. Attempting simple repair.")
        repair = text[first_brace:] + '"}'
        try:
            result = json.loads(repair)
            return result
        except json.JSONDecodeError:
            pass
        repair_2 = text[first_brace:] + '}'
        try:
            return json.loads(repair_2)
        except json.JSONDecodeError:
            pass

    # 5. Give up — return error with raw text for debugging
    logger.error("_extract_json: ALL STRATEGIES FAILED. Raw text: %r", original[:1000])
    return {
        "error": "Failed to parse LLM response",
        "raw_response": original[:2000],  # Truncate to avoid huge payloads
    }


async def score_speaking(
    transcript: str,
    question_text: str,
    part: str,
    word_timestamps: list[dict] | None = None,
    pronunciation_data: dict | None = None,
    acoustic_data: dict | None = None,
) -> dict:
    """
    Score a speaking response using Gemini LLM.
    Returns a dict with scores, feedback, improvements, and sample answer.
    """
    # Guard: refuse to score empty transcript — the LLM would return 0s
    if not transcript or not transcript.strip():
        return {
            "error": "empty_transcript",
            "detail": "No speech was detected. Please try recording again and speak clearly.",
            "scores": {"fluency": 0, "vocabulary": 0, "grammar": 0, "pronunciation": 0, "overall": 0},
        }

    fluency_context = _build_fluency_context(word_timestamps or [])

    if pronunciation_data and "error" not in pronunciation_data:
        pron_context = (
            f"PRONUNCIATION ASSESSMENT (from Azure Speech):\n"
            f"- Overall accuracy: {pronunciation_data.get('accuracy_score', 'N/A')}%\n"
            f"- Fluency: {pronunciation_data.get('fluency_score', 'N/A')}%\n"
            f"- Completeness: {pronunciation_data.get('completeness_score', 'N/A')}%\n"
            f"- Pronunciation score: {pronunciation_data.get('pronunciation_score', 'N/A')}%"
        )
    else:
        pron_context = "Pronunciation assessment: not available for this session."

    if acoustic_data:
        acoustic_context = (
            f"ACOUSTIC FLUENCY ANALYSIS (from audio waveform):\n"
            f"- Total duration: {acoustic_data.get('total_duration_sec')}s\n"
            f"- Speaking vs Silence ratio: {acoustic_data.get('speaking_ratio')} (1.0 is pure speaking)\n"
            f"- Pauses (>0.3s): {acoustic_data.get('pause_count')}\n"
            f"- Long Pauses (>1.0s): {acoustic_data.get('long_pause_count')}\n"
            f"- Estimated speech rate: {acoustic_data.get('wpm')} Words Per Minute (WPM)"
        )
    else:
        acoustic_context = "Acoustic fluency analysis: not available for this session."

    user_prompt = (
        f"## IELTS Speaking {part.upper()} Assessment\n\n"
        f"### Question / Cue Card\n{question_text}\n\n"
        f"### Candidate's Response (Transcript)\n{transcript}\n\n"
        f"### {fluency_context}\n\n"
        f"### {pron_context}\n\n"
        f"### {acoustic_context}\n\n"
        f"Evaluate this response and return ONLY the JSON object specified in your instructions."
    )

    model = genai.GenerativeModel(
        model_name=settings.GEMINI_MODEL,
        system_instruction=SCORING_SYSTEM_INSTRUCTION,
    )

    logger.info("score_speaking: calling Gemini model=%s, transcript_len=%d", settings.GEMINI_MODEL, len(transcript))
    try:
        response = await model.generate_content_async(
            user_prompt,
            generation_config=genai.GenerationConfig(
                temperature=0.3,
                max_output_tokens=4096,
            ),
            safety_settings={
                HarmCategory.HARM_CATEGORY_HATE_SPEECH: HarmBlockThreshold.BLOCK_NONE,
                HarmCategory.HARM_CATEGORY_HARASSMENT: HarmBlockThreshold.BLOCK_NONE,
                HarmCategory.HARM_CATEGORY_SEXUALLY_EXPLICIT: HarmBlockThreshold.BLOCK_NONE,
                HarmCategory.HARM_CATEGORY_DANGEROUS_CONTENT: HarmBlockThreshold.BLOCK_NONE,
            }
        )
        # Log finish_reason to diagnose truncation issues
        raw_text = ""
        if response.candidates:
            cand = response.candidates[0]
            finish_reason = str(cand.finish_reason)
            logger.info("score_speaking: finish_reason=%s, text_length=%d", finish_reason, len(response.text or ""))
            if finish_reason not in ("FinishReason.STOP", "1", "STOP"):
                logger.error("score_speaking: ABNORMAL finish_reason=%s safety_ratings=%s — response may be truncated or blocked",
                             finish_reason, cand.safety_ratings)
            raw_text = response.text or ""
        else:
            logger.error("score_speaking: no candidates in Gemini response — likely blocked entirely")
            raw_text = ""

        if not raw_text:
            raise ValueError("Gemini returned empty response (possible safety block or prompt_feedback issue)")

        result = _extract_json(raw_text)
        logger.info("score_speaking: parsed result keys=%s, overall_score=%s", list(result.keys()), result.get('overall_score'))
        return result
    except Exception as e:
        logger.error("score_speaking: EXCEPTION %s: %s", type(e).__name__, str(e), exc_info=True)
        return {
            "error": "llm_generation_failed",
            "detail": str(e),
            "fluency_score": 0.0,
            "vocabulary_score": 0.0,
            "grammar_score": 0.0,
            "pronunciation_score": 0.0,
            "overall_score": 0.0,
            "overall_feedback": f"❌ Scoring Failed: The AI model refused to score this transcript or encountered an error. Detail: {str(e)}\n\n(This sometimes happens if safety filters incorrectly flag the speech.)",
            "fluency_feedback": "-",
            "vocabulary_feedback": "-",
            "grammar_feedback": "-",
            "pronunciation_feedback": "-",
            "key_improvements": ["Could not parse assessment."],
            "sample_answer": ""
        }
