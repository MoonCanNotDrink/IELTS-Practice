"""Debug script to test Gemini API and scoring service."""
import asyncio
import sys
import json
import traceback

sys.path.insert(0, '.')

from app.config import settings
import google.generativeai as genai

genai.configure(api_key=settings.GEMINI_API_KEY)


async def test_gemini_basic():
    """Test basic Gemini connectivity and JSON output."""
    print(f"Model: {settings.GEMINI_MODEL}")
    print(f"Gemini key: {'SET' if settings.GEMINI_API_KEY else 'NOT SET'}\n")

    # List available models to verify model name
    try:
        models = [m.name for m in genai.list_models() if 'generateContent' in m.supported_generation_methods]
        flash_models = [m for m in models if 'flash' in m.lower()]
        print("Available Flash models:")
        for m in flash_models[:10]:
            print(f"  {m}")
        print()
    except Exception as e:
        print(f"Could not list models: {e}\n")

    # Test JSON generation
    try:
        model = genai.GenerativeModel(settings.GEMINI_MODEL)
        prompt = 'Return only valid JSON (no markdown, no code fences): {"test": "ok", "score": 7.5}'
        response = await model.generate_content_async(
            prompt,
            generation_config=genai.GenerationConfig(temperature=0.1, max_output_tokens=100)
        )
        raw = response.text
        print(f"Raw response: {repr(raw)}")
        parsed = json.loads(raw.strip())
        print(f"Parsed OK: {parsed}")
    except Exception as e:
        print(f"ERROR: {e}")
        traceback.print_exc()


async def test_full_scoring():
    """Test the full scoring service end-to-end."""
    print("\n--- Testing full scoring service ---")
    from app.services.scoring_service import score_speaking
    try:
        result = await score_speaking(
            transcript="I would like to talk about my smartphone. I use it every day for communication and entertainment.",
            question_text="Describe a piece of technology that you find useful",
            part="part2",
            word_timestamps=[
                {"word": "I", "start": 0.0, "end": 0.2},
                {"word": "would", "start": 0.25, "end": 0.5},
                {"word": "like", "start": 0.55, "end": 0.8},
                {"word": "to", "start": 0.85, "end": 1.0},
                {"word": "talk", "start": 1.05, "end": 1.4},
            ],
            pronunciation_data=None
        )
        print(f"Result keys: {list(result.keys())}")
        if "error" in result:
            print(f"ERROR in result: {result['error']}")
            print(f"Raw response:\n{result.get('raw_response', 'N/A')}")
        else:
            print(f"Fluency score: {result.get('fluency_score')}")
            print(f"Overall score: {result.get('overall_score')}")
            print("SUCCESS!")
    except Exception as e:
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(test_gemini_basic())
    asyncio.run(test_full_scoring())
