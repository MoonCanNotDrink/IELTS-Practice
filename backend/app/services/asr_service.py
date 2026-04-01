"""Speech-to-text service with layered fallbacks.

Priority:
1. Azure Speech when configured
2. Local faster-whisper model bundled with the repo

Both paths return the same {text, words} shape.
"""

import json
import logging
import asyncio
import tempfile
import os
import threading
from pathlib import Path
from typing import Any

import azure.cognitiveservices.speech as speechsdk
from app.config import settings

try:
    from faster_whisper import WhisperModel
except ImportError:  # pragma: no cover - optional dependency for local fallback
    WhisperModel = None

logger = logging.getLogger(__name__)

_TICKS_PER_SEC = 10_000_000  # Azure ticks are 100-nanosecond units
_WHISPER_MODEL: Any | None = None


def _normalize_audio_suffix(filename: str | None) -> str:
    suffix = Path(filename or "").suffix.lower()
    return suffix if suffix in {".wav", ".webm", ".mp3", ".ogg"} else ".wav"


def _looks_like_wav(audio_bytes: bytes) -> bool:
    return (
        len(audio_bytes) >= 12
        and audio_bytes[:4] == b"RIFF"
        and audio_bytes[8:12] == b"WAVE"
    )


def classify_asr_fallback(error_detail: str | None) -> str | None:
    if not error_detail:
        return None
    text = error_detail.lower()
    if any(
        token in text for token in ("not configured", "not installed", "no asr backend")
    ):
        return "config_or_dependency_issue"
    if any(
        token in text
        for token in ("empty transcript", "no speech", "not valid wav", "invalid wav")
    ):
        return "audio_or_no_speech_issue"
    if any(
        token in text for token in ("azure asr failed", "whisper asr failed", "asr")
    ):
        return "asr_failure"
    return "asr_failure"


def _make_config() -> speechsdk.SpeechConfig:
    cfg = speechsdk.SpeechConfig(
        subscription=settings.AZURE_SPEECH_KEY,
        region=settings.AZURE_SPEECH_REGION,
    )
    cfg.speech_recognition_language = "en-US"
    cfg.output_format = speechsdk.OutputFormat.Detailed
    # Allow up to 2s of silence before cutting a segment (helps long Part 2 recordings)
    cfg.set_property(speechsdk.PropertyId.Speech_SegmentationSilenceTimeoutMs, "2000")
    return cfg


def _get_local_model_path() -> str | None:
    """Return a usable local whisper model path if one exists."""
    candidates = [
        settings.BASE_DIR / settings.WHISPER_MODEL_PATH,
        settings.BASE_DIR / "whisper_base_model",
    ]
    for path in candidates:
        if path.exists():
            return str(path)
    return None


def _get_model() -> Any:
    """Lazily initialize the local faster-whisper model."""
    global _WHISPER_MODEL
    if _WHISPER_MODEL is not None:
        return _WHISPER_MODEL

    if WhisperModel is None:
        raise RuntimeError("faster-whisper is not installed")

    model_ref = _get_local_model_path() or settings.WHISPER_MODEL_SIZE
    logger.info(
        "Loading faster-whisper model: ref=%s device=%s compute_type=%s",
        model_ref,
        settings.WHISPER_DEVICE,
        settings.WHISPER_COMPUTE_TYPE,
    )
    _WHISPER_MODEL = WhisperModel(
        model_ref,
        device=settings.WHISPER_DEVICE,
        compute_type=settings.WHISPER_COMPUTE_TYPE,
    )
    return _WHISPER_MODEL


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
    logger.info(
        "Azure ASR: %d segments → %d words, %d chars",
        len(all_texts),
        len(all_words),
        len(text),
    )
    return {"text": text, "words": all_words}


def _transcribe_with_whisper_sync(audio_path: str) -> dict:
    """Synchronous faster-whisper transcription with word timestamps."""
    model = _get_model()
    segments, _info = model.transcribe(
        audio_path,
        language="en",
        beam_size=1,
        vad_filter=True,
        word_timestamps=True,
        condition_on_previous_text=False,
    )

    all_texts: list[str] = []
    all_words: list[dict] = []

    for segment in segments:
        segment_text = (segment.text or "").strip()
        if segment_text:
            all_texts.append(segment_text)
        for word in getattr(segment, "words", []) or []:
            token = (word.word or "").strip()
            if not token:
                continue
            all_words.append(
                {
                    "word": token,
                    "start": round(float(word.start), 3),
                    "end": round(float(word.end), 3),
                }
            )

    text = " ".join(all_texts).strip()
    logger.info(
        "Whisper ASR: %d segments → %d words, %d chars",
        len(all_texts),
        len(all_words),
        len(text),
    )
    return {"text": text, "words": all_words}


async def transcribe_audio(
    audio_bytes: bytes,
    filename: str = "audio.wav",
    request_id: str | None = None,
) -> dict:
    """
    Async wrapper around the layered ASR pipeline.
    """
    suffix = _normalize_audio_suffix(filename)
    with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as f:
        f.write(audio_bytes)
        tmp_path = f.name

    try:
        errors: list[str] = []

        azure_compatible = suffix == ".wav" and _looks_like_wav(audio_bytes)
        if settings.AZURE_SPEECH_KEY and azure_compatible:
            try:
                result = await asyncio.to_thread(_transcribe_wav_sync, tmp_path)
                if result.get("text"):
                    logger.info(
                        json.dumps(
                            {
                                "event": "asr_transcription_completed",
                                "stage": "asr",
                                "status": "ok",
                                "request_id": request_id,
                                "backend": "azure",
                                "word_count": len(result.get("words") or []),
                            },
                            ensure_ascii=False,
                            sort_keys=True,
                        )
                    )
                    return result
                errors.append("Azure ASR returned empty transcript")
            except Exception as e:
                logger.error("Azure ASR failed: %s", e, exc_info=True)
                errors.append(f"Azure ASR failed: {e}")
        elif settings.AZURE_SPEECH_KEY and suffix == ".wav":
            errors.append(
                "Azure ASR skipped: uploaded .wav payload is not valid WAV data"
            )

        try:
            result = await asyncio.to_thread(_transcribe_with_whisper_sync, tmp_path)
            if result.get("text"):
                logger.info(
                    json.dumps(
                        {
                            "event": "asr_transcription_completed",
                            "stage": "asr",
                            "status": "ok",
                            "request_id": request_id,
                            "backend": "whisper",
                            "word_count": len(result.get("words") or []),
                        },
                        ensure_ascii=False,
                        sort_keys=True,
                    )
                )
                return result
            errors.append("Whisper ASR returned empty transcript")
        except Exception as e:
            logger.error("Whisper ASR failed: %s", e, exc_info=True)
            errors.append(f"Whisper ASR failed: {e}")
        error_text = " | ".join(errors) or "No ASR backend available"
        logger.warning(
            json.dumps(
                {
                    "event": "asr_transcription_fallback",
                    "stage": "asr",
                    "status": "fallback",
                    "request_id": request_id,
                    "detail": error_text,
                    "fallback_reason": classify_asr_fallback(error_text),
                },
                ensure_ascii=False,
                sort_keys=True,
            )
        )
        return {"text": "", "words": [], "error": error_text}
    finally:
        try:
            os.unlink(tmp_path)
        except OSError:
            pass


def _estimate_word_timestamps(
    transcript: str, assumed_wpm: float = 120.0
) -> list[dict]:
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
