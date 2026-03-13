"""Azure Speech pronunciation assessment service."""

import azure.cognitiveservices.speech as speechsdk
from app.config import settings


def assess_pronunciation_sync(
    audio_bytes: bytes,
    reference_text: str,
) -> dict:
    """
    Assess pronunciation quality using Azure Speech Assessment.
    This is a SYNCHRONOUS function — call via asyncio.to_thread().

    Args:
        audio_bytes: Audio bytes (WAV format preferred)
        reference_text: The expected text (from ASR transcript)

    Returns:
        {
            "accuracy_score": 85.5,
            "fluency_score": 78.0,
            "completeness_score": 90.0,
            "pronunciation_score": 82.0,
            "words": [{"word": "hello", "accuracy": 95.0, "error_type": "None"}, ...]
        }
    """
    if not settings.AZURE_SPEECH_KEY:
        return {"error": "Azure Speech key not configured", "accuracy_score": 0}

    try:
        # Configure speech SDK
        speech_config = speechsdk.SpeechConfig(
            subscription=settings.AZURE_SPEECH_KEY,
            region=settings.AZURE_SPEECH_REGION,
        )

        # Use push stream to feed audio bytes
        push_stream = speechsdk.audio.PushAudioInputStream()
        audio_config = speechsdk.audio.AudioConfig(stream=push_stream)

        # Write audio data
        push_stream.write(audio_bytes)
        push_stream.close()

        # Configure pronunciation assessment
        pron_config = speechsdk.PronunciationAssessmentConfig(
            reference_text=reference_text,
            grading_system=speechsdk.PronunciationAssessmentGradingSystem.HundredMark,
            granularity=speechsdk.PronunciationAssessmentGranularity.Phoneme,
            enable_miscue=True,
        )

        # Create recognizer and apply pronunciation assessment
        recognizer = speechsdk.SpeechRecognizer(
            speech_config=speech_config,
            audio_config=audio_config,
            language="en-US",
        )
        pron_config.apply_to(recognizer)

        # Run recognition (blocking)
        result = recognizer.recognize_once()

        if result.reason == speechsdk.ResultReason.RecognizedSpeech:
            pron_result = speechsdk.PronunciationAssessmentResult(result)

            # Extract word-level scores
            word_scores = []
            for word in pron_result.words:
                word_scores.append({
                    "word": word.word,
                    "accuracy": word.accuracy_score,
                    "error_type": word.error_type,
                })

            return {
                "accuracy_score": pron_result.accuracy_score,
                "fluency_score": pron_result.fluency_score,
                "completeness_score": pron_result.completeness_score,
                "pronunciation_score": pron_result.pronunciation_score,
                "words": word_scores,
            }
        else:
            return {
                "error": f"Recognition failed: {result.reason}",
                "accuracy_score": 0,
            }

    except Exception as e:
        return {
            "error": f"Pronunciation assessment failed: {str(e)}",
            "accuracy_score": 0,
        }
