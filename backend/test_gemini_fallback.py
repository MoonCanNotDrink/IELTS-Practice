import asyncio
import os
import google.generativeai as genai
from dotenv import load_dotenv

load_dotenv()
genai.configure(api_key=os.getenv("GEMINI_API_KEY"))

SCORING_SYSTEM_INSTRUCTION = """You are an experienced IELTS speaking examiner with 15+ years of experience.
You must evaluate a candidate's speaking performance strictly according to the official IELTS Band Descriptors.

IMPORTANT SCORING RULES:
- Score each dimension from 1.0 to 9.0, in increments of 0.5
- Be realistic and strict — most candidates score between 5.0 and 7.0
- Always cite specific examples from the transcript to justify your scores
- The overall band score is the average of four dimensions, rounded to nearest 0.5
- You MUST respond ONLY with valid JSON. No markdown, no code fences, no explanation before or after.

The JSON must follow this exact schema:
{
    "fluency_score": 6.5,
    "fluency_feedback": "Your response was generally fluent with some hesitation...",
    "vocabulary_score": 6.0,
    "vocabulary_feedback": "You used a reasonable range of vocabulary...",
    "grammar_score": 6.0,
    "grammar_feedback": "You used a mix of simple and complex structures...",
    "pronunciation_score": 6.5,
    "pronunciation_feedback": "Your pronunciation was generally clear...",
    "overall_score": 6.5,
    "overall_feedback": "Overall, your performance demonstrates...",
    "key_improvements": [
        "Focus on reducing hesitation pauses by practicing with timed responses",
        "Expand vocabulary on topic X by learning collocations",
        "Practice complex sentence structures such as conditionals"
    ],
    "sample_answer": "Here is a Band 7+ sample answer for this topic: ..."
}"""

async def test_llm():
    transcript = "This is a building. I'm interested. The building is. Uh. Do that Dover, please, please. Uh, which is located in Paris. It's very interesting."
    
    user_prompt = (
        f"## IELTS Speaking PART2 Assessment\n\n"
        f"### Question / Cue Card\nDescribe a building you enjoyed visiting.\n\n"
        f"### Candidate's Response (Transcript)\n{transcript}\n\n"
        f"### PRONUNCIATION ASSESSMENT (from Azure Speech):\n- Overall accuracy: 80%\n\n"
        f"Evaluate this response and return ONLY the JSON object specified in your instructions."
    )

    model = genai.GenerativeModel(
        model_name="gemini-2.5-flash",
        system_instruction=SCORING_SYSTEM_INSTRUCTION,
    )

    print("Requesting Gemini...")
    try:
        response = await model.generate_content_async(
            user_prompt,
            generation_config=genai.GenerationConfig(
                temperature=0.3,
                max_output_tokens=2000,
            ),
        )
        print("Response received:")
        print(response.text)
    except Exception as e:
        print(f"Exception: {type(e).__name__} - {str(e)}")

asyncio.run(test_llm())
