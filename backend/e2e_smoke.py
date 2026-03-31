"""HTTP smoke test for local and deployed IELTS Speaking Practice environments."""

from __future__ import annotations

import argparse
import asyncio
import io
import math
import mimetypes
import os
import random
import time
import wave
from pathlib import Path

import httpx
from dotenv import load_dotenv


def build_demo_wav_bytes(duration_sec: float = 1.2, sample_rate: int = 16000) -> bytes:
    """Generate a tiny WAV payload for upload endpoints."""
    import array

    frames = io.BytesIO()
    with wave.open(frames, "wb") as wav_file:
        wav_file.setnchannels(1)
        wav_file.setsampwidth(2)
        wav_file.setframerate(sample_rate)
        total_samples = int(duration_sec * sample_rate)
        samples = array.array(
            "h",
            (
                int(12000 * math.sin(2 * math.pi * 440 * (index / sample_rate)))
                for index in range(total_samples)
            ),
        )
        wav_file.writeframes(samples.tobytes())
    return frames.getvalue()


def make_user_credentials() -> tuple[str, str]:
    stamp = int(time.time())
    suffix = random.randint(1000, 9999)
    return f"smoke_{stamp}_{suffix}", "SmokeTest123!"


def _env_flag(name: str, default: bool = False) -> bool:
    value = os.getenv(name)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


async def register_and_login(
    client: httpx.AsyncClient,
    base_url: str,
    invite_code: str,
) -> dict[str, str]:
    username, password = make_user_credentials()
    email = f"{username}@example.com"
    register_res = await client.post(
        f"{base_url}/api/auth/register",
        json={
            "username": username,
            "email": email,
            "password": password,
            "invite_code": invite_code,
        },
    )
    register_res.raise_for_status()
    register_payload = register_res.json()

    login_res = await client.post(
        f"{base_url}/api/auth/login",
        data={"username": username, "password": password},
        headers={"Content-Type": "application/x-www-form-urlencoded"},
    )
    login_res.raise_for_status()
    login_payload = login_res.json()

    token = login_payload["access_token"]
    assert register_payload.get("access_token"), "register did not return access token"
    return {"username": username, "email": email, "password": password, "token": token}


async def fetch_random_topic(client: httpx.AsyncClient, base_url: str, headers: dict[str, str]) -> dict:
    topic_res = await client.get(f"{base_url}/api/part2/topics/random", headers=headers)
    topic_res.raise_for_status()
    return topic_res.json()


async def create_part2_session(
    client: httpx.AsyncClient,
    base_url: str,
    headers: dict[str, str],
    topic_id: int,
) -> int:
    session_res = await client.post(
        f"{base_url}/api/part2/sessions",
        headers=headers,
        json={"topic_id": topic_id},
    )
    session_res.raise_for_status()
    return session_res.json()["session_id"]


async def upload_part2(
    client: httpx.AsyncClient,
    base_url: str,
    headers: dict[str, str],
    session_id: int,
    audio_bytes: bytes,
    client_transcript: str | None,
    filename: str = "smoke.wav",
    content_type: str = "audio/wav",
) -> dict:
    data = {"notes": "smoke test notes"}
    if client_transcript is not None:
        data["client_transcript"] = client_transcript
    upload_res = await client.post(
        f"{base_url}/api/part2/sessions/{session_id}/upload-audio",
        headers=headers,
        data=data,
        files={"audio": (filename, audio_bytes, content_type)},
    )
    upload_res.raise_for_status()
    return upload_res.json()


async def score_part2(
    client: httpx.AsyncClient,
    base_url: str,
    headers: dict[str, str],
    session_id: int,
) -> dict:
    score_res = await client.post(
        f"{base_url}/api/part2/sessions/{session_id}/score",
        headers=headers,
    )
    score_res.raise_for_status()
    return score_res.json()


async def run_full_exam(
    client: httpx.AsyncClient,
    base_url: str,
    headers: dict[str, str],
    topic: dict,
    audio_bytes: bytes,
) -> dict:
    start_res = await client.post(
        f"{base_url}/api/exam/start",
        headers=headers,
        json={"topic_id": topic["id"]},
    )
    start_res.raise_for_status()
    start_payload = start_res.json()
    session_id = start_payload["session_id"]

    async def upload_exam_part(part: str, question_index: int, question_text: str, transcript: str) -> dict:
        res = await client.post(
            f"{base_url}/api/exam/sessions/{session_id}/upload-part-audio",
            headers=headers,
            data={
                "part": part,
                "question_index": str(question_index),
                "question_text": question_text,
                "client_transcript": transcript,
            },
            files={"audio": (f"{part}.wav", audio_bytes, "audio/wav")},
        )
        res.raise_for_status()
        return res.json()

    await upload_exam_part(
        "part1",
        0,
        start_payload["question_text"],
        "I come from Shanghai and I enjoy its fast pace, food, and public transport.",
    )

    await upload_part2(
        client,
        base_url,
        headers,
        session_id,
        audio_bytes,
        "I would like to describe a place that helped me relax and reflect after work.",
    )

    part3_res = await client.get(
        f"{base_url}/api/exam/sessions/{session_id}/part3-questions",
        headers=headers,
    )
    part3_res.raise_for_status()
    part3_payload = part3_res.json()
    await upload_exam_part(
        "part3",
        0,
        part3_payload["first_question"],
        "Technology has improved communication, but it can also reduce the depth of face-to-face interaction.",
    )

    score_res = await client.post(
        f"{base_url}/api/scoring/sessions/{session_id}/score",
        headers=headers,
    )
    score_res.raise_for_status()
    return score_res.json()


async def assert_history_and_detail(
    client: httpx.AsyncClient,
    base_url: str,
    headers: dict[str, str],
    session_id: int,
) -> None:
    history_res = await client.get(f"{base_url}/api/scoring/history?limit=20", headers=headers)
    history_res.raise_for_status()
    history = history_res.json()
    assert any(item["session_id"] == session_id for item in history), "session missing from history"

    detail_res = await client.get(
        f"{base_url}/api/scoring/sessions/{session_id}/detail",
        headers=headers,
    )
    detail_res.raise_for_status()
    detail = detail_res.json()
    assert detail["session_id"] == session_id, "detail response mismatch"


async def assert_tts(
    client: httpx.AsyncClient,
    base_url: str,
    headers: dict[str, str],
) -> None:
    res = await client.post(
        f"{base_url}/api/scoring/tts",
        headers=headers,
        json={"text": "This is a smoke test for the IELTS speaking examiner."},
    )
    res.raise_for_status()
    content_type = res.headers.get("content-type", "")
    assert content_type.startswith("audio/"), f"unexpected TTS content-type: {content_type}"
    assert len(res.content) > 0, "empty TTS audio response"


async def main() -> None:
    load_dotenv(Path(__file__).resolve().parent / ".env")

    parser = argparse.ArgumentParser()
    parser.add_argument("--base-url", default=os.getenv("E2E_BASE_URL", "http://127.0.0.1:8000"))
    parser.add_argument("--invite-code", default=os.getenv("INVITE_CODE", "IELTS2025"))
    parser.add_argument("--asr-audio", default=os.getenv("E2E_ASR_AUDIO"))
    parser.add_argument("--skip-tts", action="store_true", default=_env_flag("E2E_SKIP_TTS", False))
    args = parser.parse_args()

    if args.invite_code == "IELTS2025" and os.getenv("INVITE_CODE"):
        args.invite_code = os.environ["INVITE_CODE"]

    async with httpx.AsyncClient(timeout=300.0) as client:
        auth = await register_and_login(client, args.base_url, args.invite_code)
        headers = {"Authorization": f"Bearer {auth['token']}"}
        topic = await fetch_random_topic(client, args.base_url, headers)
        demo_audio = build_demo_wav_bytes()

        session_id = await create_part2_session(client, args.base_url, headers, topic["id"])
        upload_payload = await upload_part2(
            client,
            args.base_url,
            headers,
            session_id,
            demo_audio,
            "This is an automated smoke test response about a memorable topic card.",
        )
        assert upload_payload["transcript"], "client transcript path did not persist"

        part2_score = await score_part2(client, args.base_url, headers, session_id)
        assert part2_score["scores"]["overall"] is not None, "part2 scoring missing overall score"
        await assert_history_and_detail(client, args.base_url, headers, session_id)

        full_score = await run_full_exam(client, args.base_url, headers, topic, demo_audio)
        assert full_score["scores"]["overall"] is not None, "full exam scoring missing overall score"
        await assert_history_and_detail(client, args.base_url, headers, full_score["session_id"])

        if not args.skip_tts:
            await assert_tts(client, args.base_url, headers)

        if args.asr_audio:
            audio_bytes = Path(args.asr_audio).read_bytes()
            asr_session_id = await create_part2_session(client, args.base_url, headers, topic["id"])
            guessed_type = mimetypes.guess_type(args.asr_audio)[0] or "application/octet-stream"
            asr_upload = await upload_part2(
                client,
                args.base_url,
                headers,
                asr_session_id,
                audio_bytes,
                None,
                filename=Path(args.asr_audio).name,
                content_type=guessed_type,
            )
            assert asr_upload["transcript"].strip(), "ASR fallback returned empty transcript"

        print("Smoke test passed")


if __name__ == "__main__":
    asyncio.run(main())
