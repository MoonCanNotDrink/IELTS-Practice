"""Azure Speech cognitive service — speech-to-text with word-level timestamps.

Accepts WAV audio files (16kHz mono PCM), produced by the browser's
AudioContext WAV encoder. Azure SDK handles WAV natively without any
format conversion.

Word-level timestamps are returned in the Detailed JSON output format:
  NBest[0].Words[{Word, Offset (100ns ticks), Duration (100ns ticks)}]
"""

import json
import logging
import asyncio
import tempfile
import os
import threading

import azure.cognitiveservices.speech as speechsdk
from app.config import settings

logger = logging.getLogger(__name__)

_TICKS_PER_SEC = 10_000_000  # Azure ticks are 100-nanosecond units


def _make_config() -> speechsdk.SpeechConfig:
    cfg = speechsdk.SpeechConfig(
        subscription=settings.AZURE_SPEECH_KEY,
        region=settings.AZURE_SPEECH_REGION,
    )
    cfg.speech_recognition_language = "en-US"
    cfg.output_format = speechsdk.OutputFormat.Detailed
    # Allow up to 2s of silence before cutting a segment (helps long Part 2 recordings)
    cfg.set_property(
        speechsdk.PropertyId.Speech_SegmentationSilenceTimeoutMs, "2000"
    )
    return cfg


def _parse_words(result_json_str: str) -> list[dict]:
    """Extract word-level timestamps from Azure Detailed JSON."""
    try:
        detail = json.loads(result_json_str)
        nbest = detail.get("NBest", [])
        if not nbest:
            return []
        return [
            {
                "word": w["Word"].strip(),
                "start": round(w["Offset"] / _TICKS_PER_SEC, 3),
                "end": round((w["Offset"] + w["Duration"]) / _TICKS_PER_SEC, 3),
            }
            for w in nbest[0].get("Words", [])
            if w.get("Word", "").strip()
        ]
    except (json.JSONDecodeError, KeyError, TypeError):
        return []


def _transcribe_wav_sync(wav_path: str) -> dict:
    """
    Synchronous Azure Speech transcription from a WAV file.
    Uses continuous recognition so recordings up to several minutes work correctly.
    """
    cfg = _make_config()
    audio_cfg = speechsdk.AudioConfig(filename=wav_path)
    recognizer = speechsdk.SpeechRecognizer(speech_config=cfg, audio_config=audio_cfg)

    all_texts: list[str] = []
    all_words: list[dict] = []
    done = threading.Event()
    error: list[str] = []

    def on_recognized(evt):
        r = evt.result
        if r.reason == speechsdk.ResultReason.RecognizedSpeech and r.text:
            all_texts.append(r.text.strip())
            all_words.extend(_parse_words(r.json))

    def on_canceled(evt):
        d = evt.result.cancellation_details
        if d.reason == speechsdk.CancellationReason.Error:
            error.append(f"{d.error_code}: {d.error_details}")
            logger.error("Azure ASR canceled: %s", error[0])
        done.set()

    def on_stopped(evt):
        done.set()

    recognizer.recognized.connect(on_recognized)
    recognizer.canceled.connect(on_canceled)
    recognizer.session_stopped.connect(on_stopped)

    recognizer.start_continuous_recognition()
    done.wait(timeout=300)  # 5-minute timeout
    recognizer.stop_continuous_recognition()

    if error:
        raise RuntimeError(f"Azure ASR error: {error[0]}")

    text = " ".join(all_texts).strip()
    logger.info("Azure ASR: %d segments → %d words, %d chars", len(all_texts), len(all_words), len(text))
    return {"text": text, "words": all_words}


async def transcribe_audio(audio_bytes: bytes, filename: str = "audio.wav") -> dict:
    """
    Async wrapper — writes audio to a temp WAV file, runs Azure ASR in a thread.

    The frontend converts all recordings to WAV (16kHz mono PCM) before uploading,
    so Azure SDK can read the file directly without any format conversion.
    """
    suffix = ".wav"  # Always save as WAV (browser sends pre-converted WAV)
    with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as f:
        f.write(audio_bytes)
        tmp_path = f.name

    try:
        result = await asyncio.to_thread(_transcribe_wav_sync, tmp_path)
        return result
    except Exception as e:
        logger.error("Azure ASR failed: %s", e, exc_info=True)
        return {"text": "", "words": [], "error": str(e)}
    finally:
        try:
            os.unlink(tmp_path)
        except OSError:
            pass


def _estimate_word_timestamps(transcript: str, assumed_wpm: float = 120.0) -> list[dict]:
    """
    Fallback: estimate word timestamps when real timing is unavailable.
    Used when client_transcript is provided directly (no audio ASR).
    """
    if not transcript:
        return []
    words = transcript.split()
    sec_per_word = 60.0 / assumed_wpm
    gap = 0.05
    result, t = [], 0.0
    for word in words:
        dur = sec_per_word * (0.7 + 0.3 * len(word) / 5.0)
        result.append({"word": word, "start": round(t, 3), "end": round(t + dur, 3)})
        t += dur + gap
    return result
