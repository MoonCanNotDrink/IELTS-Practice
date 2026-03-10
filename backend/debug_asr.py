"""Test faster-whisper with a real audio file."""
import sys, asyncio, os
sys.path.insert(0, '.')

async def test():
    from app.services.asr_service import transcribe_audio, _get_model

    # Load the model (first time downloads ~150MB)
    print("Loading model (first time may take 30-60s to download)...")
    model = _get_model()
    print("Model loaded!")

    # Look for any saved audio file in recordings/
    from app.config import settings
    audio_files = list(settings.recordings_path.glob("*.webm")) + \
                  list(settings.recordings_path.glob("*.wav"))

    if audio_files:
        f = audio_files[0]
        print(f"\nTranscribing: {f.name} ({f.stat().st_size/1024:.0f} KB)")
        audio_bytes = f.read_bytes()
        result = await transcribe_audio(audio_bytes, f.name)
        print(f"Transcript: '{result['text'][:200]}'")
        print(f"Words: {len(result['words'])}")
        if result['words']:
            print(f"First word: {result['words'][0]}")
            print(f"Last word: {result['words'][-1]}")
    else:
        print("No recordings found. Model loaded OK — ready for real recordings.")

asyncio.run(test())
