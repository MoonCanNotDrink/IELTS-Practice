import io
import json
import logging
import math
import os
import sys
import tempfile
import types
import unittest
import wave
from pathlib import Path
from unittest.mock import patch

from fastapi import FastAPI  # type: ignore
from fastapi.testclient import TestClient  # type: ignore
from sqlalchemy import select  # type: ignore
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine  # type: ignore

from app.config import settings
from app.models import Base, PracticeSession, Recording
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
        self.db_fd, self.db_path = tempfile.mkstemp(
            suffix=".db", dir=str(settings.data_dir)
        )
        os.close(self.db_fd)
        self.engine = create_async_engine(f"sqlite+aiosqlite:///{self.db_path}")
        self.session_factory = async_sessionmaker(
            self.engine, class_=AsyncSession, expire_on_commit=False
        )
        self.recordings_dir = tempfile.mkdtemp(dir=str(settings.data_dir))
        self.original_recordings_dir = settings.RECORDINGS_DIR
        settings.RECORDINGS_DIR = os.path.relpath(
            self.recordings_dir, settings.BASE_DIR
        )
        self._run_async(self._create_tables())

        # Ensure a real user row exists matching FakeUser.id so saved-topic ownership
        # and session ownership checks operate against an actual DB row.
        async def _create_fake_user_row():
            from app.models import User

            async with self.session_factory() as session:
                # set id explicitly to match FakeUser.id for tests
                u = User(
                    id=FakeUser.id, username=FakeUser.username, hashed_password="x"
                )
                session.add(u)
                await session.flush()
                await session.commit()

        self._run_async(_create_fake_user_row())

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

    def _extract_json_logs(self, output_entries: list[str]) -> list[dict]:
        parsed: list[dict] = []
        for entry in output_entries:
            brace_index = entry.find("{")
            if brace_index < 0:
                continue
            try:
                parsed.append(json.loads(entry[brace_index:]))
            except json.JSONDecodeError:
                continue
        return parsed

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

        fake_acoustic_module = types.SimpleNamespace(
            analyze_audio_fluency_sync=lambda *_args, **_kwargs: None
        )

        create_res = self.client.post(
            "/api/part2/sessions",
            json={"custom_topic": prompt},
            headers=self._auth_headers(),
        )
        self.assertEqual(create_res.status_code, 200)
        session_id = create_res.json()["session_id"]

        with (
            patch("app.routes.part2.transcribe_audio", fake_transcribe_audio),
            patch("app.routes.part2.score_speaking", fake_score_speaking),
            patch.dict(
                sys.modules, {"app.services.acoustic_service": fake_acoustic_module}
            ),
        ):
            upload_res = self.client.post(
                f"/api/part2/sessions/{session_id}/upload-audio",
                headers=self._auth_headers(),
                data={
                    "notes": "free practice notes",
                    "question_text": prompt,
                    "client_transcript": "I learned this skill by practicing online every day.",
                    # backend contract requires practice_source on uploads
                    "practice_source": "custom",
                },
                files={
                    "audio": ("free-practice.wav", build_demo_wav_bytes(), "audio/wav")
                },
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

    def _create_full_exam_session_with_recordings(self) -> int:
        async def _create_rows():
            from app.models import PracticeSession

            async with self.session_factory() as session:
                practice_session = PracticeSession(
                    user_id=FakeUser.id, status="in_progress"
                )
                session.add(practice_session)
                await session.flush()

                part2_audio_name = f"session_{practice_session.id}_part2.wav"
                (Path(self.recordings_dir) / part2_audio_name).write_bytes(
                    build_demo_wav_bytes()
                )

                session.add_all(
                    [
                        Recording(
                            session_id=practice_session.id,
                            part="part1",
                            question_index=0,
                            question_text="Part 1 question",
                            transcript="Part 1 answer",
                        ),
                        Recording(
                            session_id=practice_session.id,
                            part="part2",
                            question_index=0,
                            question_text="Part 2 question",
                            transcript="Part 2 answer with enough words",
                            audio_filename=part2_audio_name,
                            word_timestamps=[
                                {"word": "part", "start": 0.0, "end": 0.2}
                            ],
                        ),
                        Recording(
                            session_id=practice_session.id,
                            part="part3",
                            question_index=0,
                            question_text="Part 3 question",
                            transcript="Part 3 answer",
                        ),
                    ]
                )
                await session.commit()
                return practice_session.id

        return self._run_async(_create_rows())

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

        part2_history_res = self.client.get(
            "/api/part2/history?limit=20", headers=self._auth_headers()
        )
        self.assertEqual(part2_history_res.status_code, 200)
        part2_history_payload = part2_history_res.json()
        part2_match = next(
            item for item in part2_history_payload if item["session_id"] == session_id
        )
        self.assertEqual(part2_match["topic_title"], prompt)

        history_res = self.client.get(
            "/api/scoring/history?limit=20", headers=self._auth_headers()
        )
        self.assertEqual(history_res.status_code, 200)
        history_payload = history_res.json()
        matching = next(
            item for item in history_payload if item["session_id"] == session_id
        )
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
                data={"notes": "missing question text", "practice_source": "custom"},
                files={
                    "audio": ("free-practice.wav", build_demo_wav_bytes(), "audio/wav")
                },
            )

        self.assertEqual(upload_res.status_code, 400)
        self.assertEqual(
            upload_res.json()["detail"],
            "question_text is required for custom-topic sessions",
        )

    def test_free_practice_topics_grouped_and_saved_topic_dedupe(self):
        # Create one official topic row directly
        async def _insert_topic():
            from app.models import Topic, User, SavedTopic

            async with self.session_factory() as session:
                user = User(username="other", hashed_password="x")
                session.add(user)
                topic = Topic(
                    title="Official topic", points=["a", "b"], category="people"
                )
                session.add(topic)
                await session.flush()
                await session.commit()
                return topic.id, user.id

        topic_id, other_user_id = self._run_async(_insert_topic())

        # Initially no saved topics for FakeUser; ensure the response shape is correct
        res = self.client.get(
            "/api/part2/free-practice-topics", headers=self._auth_headers()
        )
        self.assertEqual(res.status_code, 200)
        payload = res.json()
        self.assertIn("official_topics", payload)
        self.assertIn("saved_topics", payload)
        # official_topics should be a list of objects with id/title/category
        self.assertIsInstance(payload["official_topics"], list)
        self.assertTrue(
            any(
                isinstance(t, dict) and all(k in t for k in ("id", "title", "category"))
                for t in payload["official_topics"]
            )
        )

        # Create a saved topic via POST
        create_res = self.client.post(
            "/api/part2/free-practice-topics",
            json={"prompt_text": "My custom prompt\nMore"},
            headers=self._auth_headers(),
        )
        self.assertEqual(create_res.status_code, 200)
        created = create_res.json()
        self.assertTrue(created["created"])

        # Creating same prompt again should dedupe (created==False)
        create_res2 = self.client.post(
            "/api/part2/free-practice-topics",
            json={"prompt_text": "  My   custom prompt\nMore  "},
            headers=self._auth_headers(),
        )
        self.assertEqual(create_res2.status_code, 200)
        self.assertFalse(create_res2.json()["created"])

        # Ensure saved_topics listing includes the saved topic we just created (by id)
        list_res = self.client.get(
            "/api/part2/free-practice-topics", headers=self._auth_headers()
        )
        self.assertEqual(list_res.status_code, 200)
        saved = list_res.json()["saved_topics"]
        created_topic_id = created["topic"]["id"]
        self.assertTrue(any(s["id"] == created_topic_id for s in saved))

        # Insert a saved topic for OTHER user and ensure it does not appear
        async def _insert_other_saved():
            from app.models import SavedTopic

            async with self.session_factory() as session:
                st = SavedTopic(
                    user_id=other_user_id,
                    title="Other",
                    prompt_text="x",
                    normalized_prompt="x",
                )
                session.add(st)
                await session.flush()
                await session.commit()

        self._run_async(_insert_other_saved())

        list_res2 = self.client.get(
            "/api/part2/free-practice-topics", headers=self._auth_headers()
        )
        saved2 = list_res2.json()["saved_topics"]
        # still only our user's saved topics
        self.assertTrue(all(s["title"] != "Other" for s in saved2))

    def test_saved_topic_session_start_and_mixed_source_rejection(self):
        # Create a saved topic for FakeUser via the public endpoint so ownership semantics match
        create_resp = self.client.post(
            "/api/part2/free-practice-topics",
            json={"prompt_text": "hello"},
            headers=self._auth_headers(),
        )
        self.assertEqual(create_resp.status_code, 200)
        saved_id = create_resp.json()["topic"]["id"]

        # Start session referencing saved_topic_id
        res = self.client.post(
            "/api/part2/sessions",
            json={"saved_topic_id": saved_id},
            headers=self._auth_headers(),
        )
        self.assertEqual(res.status_code, 200)
        payload = res.json()
        self.assertEqual(payload["saved_topic_id"], saved_id)

        # Mixed source: providing both saved_topic_id and custom_topic should be rejected
        bad = self.client.post(
            "/api/part2/sessions",
            json={"saved_topic_id": saved_id, "custom_topic": "x"},
            headers=self._auth_headers(),
        )
        self.assertEqual(bad.status_code, 400)

    def test_custom_upload_autosaves_and_no_duplicate_or_cross_user_leak(self):
        # Create a session with custom topic
        create_res = self.client.post(
            "/api/part2/sessions",
            json={"custom_topic": "Describe a skill you learned online"},
            headers=self._auth_headers(),
        )
        self.assertEqual(create_res.status_code, 200)
        session_id = create_res.json()["session_id"]

        # Patch transcribe to return non-empty transcript and score_speaking to noop
        async def fake_transcribe_audio(*_args, **_kwargs):
            return {"text": "I like testing", "words": [{"start": 0.0, "end": 0.5}]}

        async def fake_score_speaking(**kwargs):
            return {"fluency_score": 6.0}

        # Upload with practice_source=custom should autosave since transcript non-empty
        with (
            patch("app.routes.part2.transcribe_audio", fake_transcribe_audio),
            patch("app.routes.part2.score_speaking", fake_score_speaking),
        ):
            upload_res = self.client.post(
                f"/api/part2/sessions/{session_id}/upload-audio",
                headers=self._auth_headers(),
                data={
                    "notes": "notes",
                    "question_text": "Describe a skill you learned online",
                    "client_transcript": "",
                    "practice_source": "custom",
                },
                files={"audio": ("a.wav", build_demo_wav_bytes(), "audio/wav")},
            )
            self.assertEqual(upload_res.status_code, 200)

        # Check saved topics - there should be exactly one saved topic for FakeUser with normalized prompt
        list_res = self.client.get(
            "/api/part2/free-practice-topics", headers=self._auth_headers()
        )
        saved = list_res.json()["saved_topics"]
        matches = [s for s in saved if s["prompt_text"].startswith("Describe a skill")]
        self.assertEqual(len(matches), 1)

        # Upload again the same prompt - autosave should not create duplicate
        create_res2 = self.client.post(
            "/api/part2/sessions",
            json={"custom_topic": "Describe a skill you learned online"},
            headers=self._auth_headers(),
        )
        sid2 = create_res2.json()["session_id"]
        with (
            patch("app.routes.part2.transcribe_audio", fake_transcribe_audio),
            patch("app.routes.part2.score_speaking", fake_score_speaking),
        ):
            upload_res2 = self.client.post(
                f"/api/part2/sessions/{sid2}/upload-audio",
                headers=self._auth_headers(),
                data={
                    "notes": "notes",
                    "question_text": "Describe a skill you learned online",
                    "client_transcript": "",
                    "practice_source": "custom",
                },
                files={"audio": ("a.wav", build_demo_wav_bytes(), "audio/wav")},
            )
            self.assertEqual(upload_res2.status_code, 200)

        # Ensure still only one saved topic for this user with that prompt
        list_res3 = self.client.get(
            "/api/part2/free-practice-topics", headers=self._auth_headers()
        )
        saved3 = list_res3.json()["saved_topics"]
        matches3 = [
            s for s in saved3 if s["prompt_text"].startswith("Describe a skill")
        ]
        self.assertEqual(len(matches3), 1)

        # Now ensure another user does not see this saved topic
        async def _create_other_user_and_list():
            from app.models import User

            async with self.session_factory() as session:
                u = User(username="u2", hashed_password="x")
                session.add(u)
                await session.flush()
                return u.id

        other_id = self._run_async(_create_other_user_and_list())

        # Override dependency to simulate other user for a raw request
        app = FastAPI()
        app.include_router(part2_router)
        app.dependency_overrides = {
            part2_module.get_current_user: lambda: types.SimpleNamespace(id=other_id),
            part2_module.get_db: self._override_get_db,
        }
        other_client = TestClient(app)
        other_client.__enter__()
        try:
            other_list = other_client.get("/api/part2/free-practice-topics")
            self.assertEqual(other_list.status_code, 200)
            other_saved = other_list.json()["saved_topics"]
            # other user should not see our saved prompt
            self.assertTrue(
                all(
                    not s["prompt_text"].startswith("Describe a skill")
                    for s in other_saved
                )
            )
        finally:
            other_client.__exit__(None, None, None)

    def test_saved_topic_session_rejects_foreign_saved_topic(self):
        # Insert a saved topic belonging to a different user
        async def _create_other_user_and_saved():
            from app.models import User, SavedTopic

            async with self.session_factory() as session:
                u = User(username="foreign", hashed_password="x")
                session.add(u)
                await session.flush()
                st = SavedTopic(
                    user_id=u.id,
                    title="F",
                    prompt_text="foreign",
                    normalized_prompt="foreign",
                )
                session.add(st)
                await session.flush()
                await session.commit()
                return st.id

        foreign_saved_id = self._run_async(_create_other_user_and_saved())

        # Attempt to start a session using that saved_topic_id as the test user should be rejected (404)
        res = self.client.post(
            "/api/part2/sessions",
            json={"saved_topic_id": foreign_saved_id},
            headers=self._auth_headers(),
        )
        self.assertEqual(res.status_code, 404)

    def test_saved_practice_source_upload_respects_saved_topic_and_no_duplicate(self):
        # Create a saved topic for current user via public endpoint
        create_resp = self.client.post(
            "/api/part2/free-practice-topics",
            json={"prompt_text": "Saved source prompt"},
            headers=self._auth_headers(),
        )
        self.assertEqual(create_resp.status_code, 200)
        created_topic = create_resp.json()["topic"]
        saved_topic_id = created_topic["id"]

        # Start a custom session (topic_id should be NULL so autosave logic for practice_source applies)
        create_session = self.client.post(
            "/api/part2/sessions",
            json={"custom_topic": "Saved source prompt"},
            headers=self._auth_headers(),
        )
        self.assertEqual(create_session.status_code, 200)
        session_id = create_session.json()["session_id"]

        # Patch transcribe to return non-empty transcript and score to noop
        async def fake_transcribe_audio(*_args, **_kwargs):
            return {"text": "spoken words", "words": [{"start": 0.0, "end": 0.5}]}

        async def fake_score_speaking(**kwargs):
            return {"fluency_score": 6.0}

        with (
            patch("app.routes.part2.transcribe_audio", fake_transcribe_audio),
            patch("app.routes.part2.score_speaking", fake_score_speaking),
        ):
            upload_res = self.client.post(
                f"/api/part2/sessions/{session_id}/upload-audio",
                headers=self._auth_headers(),
                data={
                    "notes": "notes",
                    "question_text": "Saved source prompt",
                    "client_transcript": "",
                    "practice_source": "saved",
                    "saved_topic_id": saved_topic_id,
                },
                files={"audio": ("a.wav", build_demo_wav_bytes(), "audio/wav")},
            )
            self.assertEqual(upload_res.status_code, 200)

        # Ensure no duplicate saved topic created and that use_count has been incremented
        list_res = self.client.get(
            "/api/part2/free-practice-topics", headers=self._auth_headers()
        )
        self.assertEqual(list_res.status_code, 200)
        saved = list_res.json()["saved_topics"]
        matches = [s for s in saved if s["id"] == saved_topic_id]
        self.assertEqual(len(matches), 1)
        # use_count should be at least 1 after the upload increment
        self.assertTrue(matches[0].get("use_count", 0) >= 1)

    def test_empty_transcript_does_not_autosave(self):
        # Create a custom session
        create_res = self.client.post(
            "/api/part2/sessions",
            json={"custom_topic": "Silent topic"},
            headers=self._auth_headers(),
        )
        session_id = create_res.json()["session_id"]

        async def fake_transcribe_empty(*_args, **_kwargs):
            return {"text": "", "words": []}

        async def fake_score(**kwargs):
            return {"fluency_score": 0.0}

        with (
            patch("app.routes.part2.transcribe_audio", fake_transcribe_empty),
            patch("app.routes.part2.score_speaking", fake_score),
        ):
            upload_res = self.client.post(
                f"/api/part2/sessions/{session_id}/upload-audio",
                headers=self._auth_headers(),
                data={
                    "notes": "notes",
                    "question_text": "Silent topic",
                    "client_transcript": "",
                    "practice_source": "custom",
                },
                files={"audio": ("a.wav", build_demo_wav_bytes(), "audio/wav")},
            )
            # Upload should still succeed, but autosave must not create a saved topic
            self.assertEqual(upload_res.status_code, 200)

        list_res = self.client.get(
            "/api/part2/free-practice-topics", headers=self._auth_headers()
        )
        saved = list_res.json()["saved_topics"]
        self.assertTrue(
            all(not s["prompt_text"].startswith("Silent topic") for s in saved)
        )

    def test_part2_score_response_includes_request_id_and_structured_logs(self):
        session_id = self._complete_free_practice_session(
            "Describe a skill you learned online"
        )

        async def fake_score_speaking(**_kwargs):
            return {
                "error": "llm_generation_failed",
                "detail": "Gemini request timed out after 5s.",
                "fluency_score": 0.0,
                "vocabulary_score": 0.0,
                "grammar_score": 0.0,
                "pronunciation_score": 0.0,
                "overall_score": 0.0,
                "overall_feedback": "fallback",
            }

        with (
            patch("app.routes.part2.score_speaking", fake_score_speaking),
            self.assertLogs("app.routes.part2", level="INFO") as route_logs,
        ):
            response = self.client.post(
                f"/api/part2/sessions/{session_id}/score",
                headers=self._auth_headers(),
            )

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertIn("request_id", payload)
        self.assertTrue(payload["request_id"])

        structured_logs = self._extract_json_logs(route_logs.output)
        self.assertTrue(
            any(log.get("event") == "part2_scoring_started" for log in structured_logs)
        )
        self.assertTrue(
            any(
                log.get("event") == "part2_scoring_completed" for log in structured_logs
            )
        )
        self.assertTrue(
            any(
                log.get("fallback_reason") == "llm_timeout_or_failure"
                for log in structured_logs
            )
        )

    def test_part2_score_failure_returns_request_id_header(self):
        create_res = self.client.post(
            "/api/part2/sessions",
            json={"custom_topic": "Silent topic"},
            headers=self._auth_headers(),
        )
        session_id = create_res.json()["session_id"]

        async def fake_transcribe_empty(*_args, **_kwargs):
            return {"text": "", "words": []}

        with patch("app.routes.part2.transcribe_audio", fake_transcribe_empty):
            upload_res = self.client.post(
                f"/api/part2/sessions/{session_id}/upload-audio",
                headers=self._auth_headers(),
                data={
                    "notes": "notes",
                    "question_text": "Silent topic",
                    "client_transcript": "",
                    "practice_source": "custom",
                },
                files={"audio": ("a.wav", build_demo_wav_bytes(), "audio/wav")},
            )
        self.assertEqual(upload_res.status_code, 200)

        score_res = self.client.post(
            f"/api/part2/sessions/{session_id}/score",
            headers=self._auth_headers(),
        )
        self.assertEqual(score_res.status_code, 422)
        self.assertTrue(score_res.headers.get("x-request-id"))
        self.assertEqual(
            score_res.json()["detail"],
            "Transcription failed - no speech detected. Please re-record and speak clearly into your microphone.",
        )

    def test_upload_client_transcript_fallback_preserves_real_fallback_reason(self):
        create_res = self.client.post(
            "/api/part2/sessions",
            json={"custom_topic": "Fallback topic"},
            headers=self._auth_headers(),
        )
        session_id = create_res.json()["session_id"]

        async def fake_transcribe_empty(*_args, **_kwargs):
            return {
                "text": "",
                "words": [],
                "error": "faster-whisper is not installed",
            }

        with (
            patch("app.routes.part2.transcribe_audio", fake_transcribe_empty),
            self.assertLogs("app.routes.part2", level="INFO") as route_logs,
        ):
            upload_res = self.client.post(
                f"/api/part2/sessions/{session_id}/upload-audio",
                headers=self._auth_headers(),
                data={
                    "notes": "notes",
                    "question_text": "Fallback topic",
                    "client_transcript": "Recovered from browser transcript.",
                    "practice_source": "custom",
                },
                files={"audio": ("a.wav", build_demo_wav_bytes(), "audio/wav")},
            )

        self.assertEqual(upload_res.status_code, 200)
        structured_logs = self._extract_json_logs(route_logs.output)
        fallback_log = next(
            log
            for log in structured_logs
            if log.get("event") == "part2_asr_client_transcript_fallback"
        )
        self.assertEqual(
            fallback_log.get("fallback_reason"), "config_or_dependency_issue"
        )

    def test_full_scoring_response_includes_request_id_and_structured_logs(self):
        session_id = self._create_full_exam_session_with_recordings()

        async def fake_score_speaking(**_kwargs):
            return {
                "fluency_score": 6.0,
                "vocabulary_score": 6.0,
                "grammar_score": 6.0,
                "pronunciation_score": 6.0,
                "overall_score": 6.0,
                "overall_feedback": "ok",
            }

        fake_acoustic_module = types.SimpleNamespace(
            analyze_audio_fluency_sync=lambda *_args, **_kwargs: {"wpm": 120}
        )

        with (
            patch("app.routes.scoring.score_speaking", fake_score_speaking),
            patch(
                "app.routes.scoring.assess_pronunciation_sync",
                lambda *_args, **_kwargs: {"accuracy_score": 90},
            ),
            patch.dict(
                sys.modules, {"app.services.acoustic_service": fake_acoustic_module}
            ),
            self.assertLogs("app.routes.scoring", level="INFO") as route_logs,
        ):
            response = self.client.post(
                f"/api/scoring/sessions/{session_id}/score",
                headers=self._auth_headers(),
            )

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertIn("request_id", payload)
        self.assertTrue(payload["request_id"])

        structured_logs = self._extract_json_logs(route_logs.output)
        self.assertTrue(
            any(log.get("event") == "full_scoring_started" for log in structured_logs)
        )
        self.assertTrue(
            any(log.get("event") == "full_scoring_completed" for log in structured_logs)
        )
        self.assertTrue(
            any(
                log.get("stage") in {"pronunciation", "acoustic", "llm_scoring"}
                for log in structured_logs
            )
        )

    def test_full_scoring_failure_returns_request_id_header(self):
        async def _create_session_only():
            async with self.session_factory() as session:
                practice_session = PracticeSession(
                    user_id=FakeUser.id, status="in_progress"
                )
                session.add(practice_session)
                await session.flush()
                await session.commit()
                return practice_session.id

        session_id = self._run_async(_create_session_only())
        response = self.client.post(
            f"/api/scoring/sessions/{session_id}/score",
            headers=self._auth_headers(),
        )

        self.assertEqual(response.status_code, 400)
        self.assertTrue(response.headers.get("x-request-id"))
        self.assertEqual(response.json()["detail"], "No recordings for this session")


if __name__ == "__main__":
    unittest.main()
