import io
import math
import os
import sys
import tempfile
import types
import unittest
import wave
from pathlib import Path
from unittest.mock import patch

from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.config import settings
from app.models import Base, PracticeSession
from app.routes import part2 as part2_module
from app.routes import scoring as scoring_module
from app.routes.part2 import router as part2_router
from app.routes.scoring import router as scoring_router


def build_demo_wav_bytes(duration_sec: float = 0.5, sample_rate: int = 16000) -> bytes:
    frames = io.BytesIO()
    with wave.open(frames, "wb") as wav_file:
        wav_file.setnchannels(1)
        wav_file.setsampwidth(2)
        wav_file.setframerate(sample_rate)
        total_samples = int(duration_sec * sample_rate)
        samples = bytearray()
        for index in range(total_samples):
            value = int(12000 * math.sin(2 * math.pi * 440 * (index / sample_rate)))
            samples.extend(int(value).to_bytes(2, byteorder="little", signed=True))
        wav_file.writeframes(bytes(samples))
    return frames.getvalue()


class FakeUser:
    id = 1
    username = "tester"


class FreePracticeRouteTests(unittest.TestCase):
    def setUp(self):
        self.db_fd, self.db_path = tempfile.mkstemp(suffix=".db", dir=str(settings.data_dir))
        os.close(self.db_fd)
        self.engine = create_async_engine(f"sqlite+aiosqlite:///{self.db_path}")
        self.session_factory = async_sessionmaker(self.engine, class_=AsyncSession, expire_on_commit=False)
        self.recordings_dir = tempfile.mkdtemp(dir=str(settings.data_dir))
        self.original_recordings_dir = settings.RECORDINGS_DIR
        settings.RECORDINGS_DIR = os.path.relpath(self.recordings_dir, settings.BASE_DIR)
        self._run_async(self._create_tables())

        app = FastAPI()
        app.include_router(part2_router)
        app.include_router(scoring_router)
        app.dependency_overrides = {
            part2_module.get_current_user: lambda: FakeUser(),
            scoring_module.get_current_user: lambda: FakeUser(),
            part2_module.get_db: self._override_get_db,
            scoring_module.get_db: self._override_get_db,
        }

        self.client = TestClient(app)
        self.client.__enter__()

    def tearDown(self):
        self.client.__exit__(None, None, None)
        self._run_async(self.engine.dispose())
        settings.RECORDINGS_DIR = self.original_recordings_dir
        Path(self.db_path).unlink(missing_ok=True)
        for item in Path(self.recordings_dir).glob("*"):
            item.unlink(missing_ok=True)
        Path(self.recordings_dir).rmdir()

    async def _create_tables(self):
        async with self.engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)

    async def _override_get_db(self):
        async with self.session_factory() as session:
            try:
                yield session
                await session.commit()
            except Exception:
                await session.rollback()
                raise

    def _run_async(self, coro):
        import asyncio

        return asyncio.run(coro)

    def _auth_headers(self):
        return {"Authorization": "Bearer test-token"}

    def _fetch_session(self, session_id: int) -> PracticeSession:
        async def _query():
            async with self.session_factory() as session:
                return await session.get(PracticeSession, session_id)

        return self._run_async(_query())

    def _complete_free_practice_session(self, prompt: str) -> int:
        captured = {}

        async def fake_transcribe_audio(*_args, **_kwargs):
            return {"text": "", "words": []}

        async def fake_score_speaking(**kwargs):
            captured.update(kwargs)
            return {
                "fluency_score": 6.5,
                "vocabulary_score": 6.0,
                "grammar_score": 6.0,
                "pronunciation_score": 6.5,
                "overall_score": 6.5,
                "fluency_feedback": "Good flow.",
                "vocabulary_feedback": "Good range.",
                "grammar_feedback": "Mostly accurate.",
                "pronunciation_feedback": "Clear enough.",
                "overall_feedback": "Solid answer.",
                "key_improvements": ["Add more detail."],
                "sample_answer": "Sample answer.",
            }

        fake_acoustic_module = types.SimpleNamespace(analyze_audio_fluency_sync=lambda *_args, **_kwargs: None)

        create_res = self.client.post(
            "/api/part2/sessions",
            json={"custom_topic": prompt},
            headers=self._auth_headers(),
        )
        self.assertEqual(create_res.status_code, 200)
        session_id = create_res.json()["session_id"]

        with patch("app.routes.part2.transcribe_audio", fake_transcribe_audio), patch(
            "app.routes.part2.score_speaking", fake_score_speaking
        ), patch.dict(sys.modules, {"app.services.acoustic_service": fake_acoustic_module}):
            upload_res = self.client.post(
                f"/api/part2/sessions/{session_id}/upload-audio",
                headers=self._auth_headers(),
                data={
                    "notes": "free practice notes",
                    "question_text": prompt,
                    "client_transcript": "I learned this skill by practicing online every day.",
                },
                files={"audio": ("free-practice.wav", build_demo_wav_bytes(), "audio/wav")},
            )
            self.assertEqual(upload_res.status_code, 200)

            score_res = self.client.post(
                f"/api/part2/sessions/{session_id}/score",
                headers=self._auth_headers(),
            )

        self.assertEqual(score_res.status_code, 200)
        self.assertEqual(score_res.json()["exam_scope"], "part2_only")
        self.assertEqual(captured.get("question_text"), prompt)
        return session_id

    def test_create_session_accepts_custom_topic(self):
        response = self.client.post(
            "/api/part2/sessions",
            json={"custom_topic": "Describe a skill you learned online"},
            headers=self._auth_headers(),
        )

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(payload["status"], "in_progress")
        self.assertEqual(payload["custom_topic"], "Describe a skill you learned online")

        session = self._fetch_session(payload["session_id"])
        self.assertIsNone(session.topic_id)
        self.assertEqual(session.user_id, FakeUser.id)

    def test_part2_score_uses_recording_question_text_fallback(self):
        self._complete_free_practice_session("Describe a skill you learned online")

    def test_history_detail_use_custom_prompt_title(self):
        prompt = "Describe a skill you learned online"
        session_id = self._complete_free_practice_session(prompt)

        part2_history_res = self.client.get("/api/part2/history?limit=20", headers=self._auth_headers())
        self.assertEqual(part2_history_res.status_code, 200)
        part2_history_payload = part2_history_res.json()
        part2_match = next(item for item in part2_history_payload if item["session_id"] == session_id)
        self.assertEqual(part2_match["topic_title"], prompt)

        history_res = self.client.get("/api/scoring/history?limit=20", headers=self._auth_headers())
        self.assertEqual(history_res.status_code, 200)
        history_payload = history_res.json()
        matching = next(item for item in history_payload if item["session_id"] == session_id)
        self.assertEqual(matching["topic_title"], prompt)

        detail_res = self.client.get(
            f"/api/scoring/sessions/{session_id}/detail",
            headers=self._auth_headers(),
        )
        self.assertEqual(detail_res.status_code, 200)
        self.assertEqual(detail_res.json()["topic_title"], prompt)

    def test_upload_requires_question_text_for_custom_topic_session(self):
        create_res = self.client.post(
            "/api/part2/sessions",
            json={"custom_topic": "Describe a skill you learned online"},
            headers=self._auth_headers(),
        )
        self.assertEqual(create_res.status_code, 200)
        session_id = create_res.json()["session_id"]

        async def fake_transcribe_audio(*_args, **_kwargs):
            return {"text": "fallback transcript", "words": []}

        with patch("app.routes.part2.transcribe_audio", fake_transcribe_audio):
            upload_res = self.client.post(
                f"/api/part2/sessions/{session_id}/upload-audio",
                headers=self._auth_headers(),
                data={"notes": "missing question text"},
                files={"audio": ("free-practice.wav", build_demo_wav_bytes(), "audio/wav")},
            )

        self.assertEqual(upload_res.status_code, 400)
        self.assertEqual(upload_res.json()["detail"], "question_text is required for custom-topic sessions")


if __name__ == "__main__":
    unittest.main()
