import asyncio
import logging

import google.generativeai as genai
from google.generativeai.types import HarmBlockThreshold, HarmCategory

from app.config import settings
from app.services.writing_scoring_service import extract_json

logger = logging.getLogger(__name__)

genai.configure(api_key=settings.GEMINI_API_KEY)

CHART_SYSTEM_INSTRUCTION = """You are a data visualization expert for IELTS Writing Task 1.
Given a writing prompt, generate realistic chart data that matches the prompt description.

Rules:
- Return ONLY valid JSON. No markdown, no code fences.
- Choose the most appropriate chart type based on the prompt: bar, line, pie, or table.
- Keep values realistic and internally consistent.
- Use clear chart titles, labels, and axis names.

Return JSON using exactly one of these schemas:

Bar or line chart:
{
  "type": "bar",
  "data": {
    "labels": ["Label1", "Label2"],
    "datasets": [{
      "label": "Dataset name",
      "data": [10, 20],
      "backgroundColor": ["rgba(54, 162, 235, 0.7)", "rgba(255, 99, 132, 0.7)"],
      "borderColor": ["rgba(54, 162, 235, 1)", "rgba(255, 99, 132, 1)"],
      "borderWidth": 1
    }]
  },
  "options": {
    "responsive": true,
    "plugins": {
      "title": {"display": true, "text": "Chart Title"},
      "legend": {"display": false}
    },
    "scales": {
      "y": {"beginAtZero": true, "title": {"display": true, "text": "Y-axis label"}}
    }
  }
}

For line charts, datasets should include: "fill": false, "tension": 0.3 instead of backgroundColor array.
For line charts with multiple datasets, include "legend": {"position": "top"} instead of "display": false.

Single pie chart:
{
  "type": "pie",
  "data": {
    "labels": ["Segment1", "Segment2"],
    "datasets": [{"data": [30, 25], "backgroundColor": ["rgba(54, 162, 235, 0.7)", "rgba(255, 99, 132, 0.7)"]}]
  },
  "options": {
    "responsive": true,
    "plugins": {"title": {"display": true, "text": "Chart Title"}}
  }
}

Pie chart comparing two time periods:
{
  "type": "pie",
  "multi": true,
  "charts": [
    {"title": "Period 1", "data": {"labels": ["A", "B"], "datasets": [{"data": [10, 20], "backgroundColor": ["rgba(54, 162, 235, 0.7)", "rgba(255, 99, 132, 0.7)"]}]}} ,
    {"title": "Period 2", "data": {"labels": ["A", "B"], "datasets": [{"data": [12, 18], "backgroundColor": ["rgba(54, 162, 235, 0.7)", "rgba(255, 99, 132, 0.7)"]}]}}
  ]
}

Table:
{
  "type": "table",
  "title": "Table Title",
  "headers": ["Column1", "Column2"],
  "rows": [["Row1Col1", "Row1Col2"], ["Row2Col1", "Row2Col2"]]
}
"""


async def generate_chart_data(prompt_text: str) -> dict:
    if not prompt_text or not prompt_text.strip():
        return {"error": "empty_prompt", "detail": "Prompt text is required."}

    model = genai.GenerativeModel(
        model_name=settings.GEMINI_MODEL,
        system_instruction=CHART_SYSTEM_INSTRUCTION,
    )
    user_prompt = (
        "## IELTS Writing Task 1 Chart Data Generation\n\n"
        f"### Prompt\n{prompt_text}\n\n"
        "Generate realistic chart data that matches this prompt and return only the JSON object."
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
        logger.error("generate_chart_data failed: %s", exc, exc_info=True)
        return {
            "error": "llm_generation_failed",
            "detail": str(exc),
        }
