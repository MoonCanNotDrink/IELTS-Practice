import os
import tempfile
import unittest
from datetime import datetime, timedelta

from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.config import settings
from app.models import Base, PracticeSession, Recording, User
from app.routes import speaking_learning as speaking_learning_module
from app.routes.speaking_learning import router as speaking_learning_router


class FakeUser:
    id = 1
    username = "tester"


class SpeakingLearningRouteTests(unittest.TestCase):
    def setUp(self):
        self.db_fd, self.db_path = tempfile.mkstemp(
            suffix=".db", dir=str(settings.data_dir)
        )
        os.close(self.db_fd)
        self.engine = create_async_engine(f"sqlite+aiosqlite:///{self.db_path}")
        self.session_factory = async_sessionmaker(
            self.engine, class_=AsyncSession, expire_on_commit=False
        )
        self._run_async(self._create_tables())
        self._run_async(self._create_users())

        app = FastAPI()
        app.include_router(speaking_learning_router)
        app.dependency_overrides = {
            speaking_learning_module.get_current_user: lambda: FakeUser(),
            speaking_learning_module.get_db: self._override_get_db,
        }
        self.client = TestClient(app)
        self.client.__enter__()

    def tearDown(self):
        self.client.__exit__(None, None, None)
        self._run_async(self.engine.dispose())
        os.unlink(self.db_path)

    async def _create_tables(self):
        async with self.engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)

    async def _create_users(self):
        async with self.session_factory() as session:
            session.add_all(
                [
                    User(id=1, username="tester", hashed_password="x"),
                    User(id=2, username="other", hashed_password="x"),
                ]
            )
            await session.flush()
            await session.commit()

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

    def _seed_comparison_data(self):
        async def _seed():
            async with self.session_factory() as session:
                now = datetime.utcnow()
                old_session = PracticeSession(
                    user_id=1,
                    status="completed",
                    finished_at=now - timedelta(days=4),
                    overall_score=5.0,
                    fluency_score=5.0,
                    vocabulary_score=5.0,
                    grammar_score=5.0,
                    pronunciation_score=5.0,
                )
                prev_session = PracticeSession(
                    user_id=1,
                    status="completed",
                    finished_at=now - timedelta(days=2),
                    overall_score=5.5,
                    fluency_score=5.0,
                    vocabulary_score=5.5,
                    grammar_score=5.5,
                    pronunciation_score=5.0,
                )
                cur_session = PracticeSession(
                    user_id=1,
                    status="completed",
                    finished_at=now,
                    overall_score=6.5,
                    fluency_score=6.0,
                    vocabulary_score=6.0,
                    grammar_score=6.0,
                    pronunciation_score=6.5,
                )
                session.add_all([old_session, prev_session, cur_session])
                await session.flush()

                old_recording = Recording(
                    session_id=old_session.id,
                    part="part2",
                    question_index=0,
                    question_text="Describe a skill you learned online",
                    transcript="I learned coding online.\nI practiced every weekend.",
                    prompt_match_key="prompt:skill-online",
                    weakness_tags=["short_answer"],
                    created_at=now - timedelta(days=4),
                )
                prev_recording = Recording(
                    session_id=prev_session.id,
                    part="part2",
                    question_index=0,
                    question_text="Describe a skill you learned online",
                    transcript="I learned coding online.\nI practiced every day with friends.",
                    prompt_match_key="prompt:skill-online",
                    weakness_tags=["hesitation", "short_answer"],
                    created_at=now - timedelta(days=2),
                )
                cur_recording = Recording(
                    session_id=cur_session.id,
                    part="part2",
                    question_index=0,
                    question_text="Describe a skill you learned online",
                    transcript="I learned coding online.\nI practiced every day with projects.",
                    prompt_match_key="prompt:skill-online",
                    weakness_tags=["hesitation", "grammar_errors"],
                    created_at=now,
                )
                session.add_all([old_recording, prev_recording, cur_recording])
                await session.flush()
                await session.commit()
                return cur_recording.id, prev_recording.id

        return self._run_async(_seed())

    def _seed_summary_data(self, count: int = 5):
        async def _seed():
            async with self.session_factory() as session:
                base = datetime.utcnow() - timedelta(days=10)
                created_ids = []
                for index in range(count):
                    session_row = PracticeSession(
                        user_id=1,
                        status="completed",
                        finished_at=base + timedelta(days=index),
                        overall_score=5.0 + (index * 0.4),
                        fluency_score=5.0 + (index * 0.3),
                        vocabulary_score=5.0 + (index * 0.2),
                        grammar_score=5.0 + (index * 0.25),
                        pronunciation_score=5.0 + (index * 0.35),
                    )
                    session.add(session_row)
                    await session.flush()

                    tags = []
                    if index in {0, 1, 3}:
                        tags.append("hesitation")
                    if index in {1, 4}:
                        tags.append("short_answer")
                    if index in {2}:
                        tags.append("grammar_errors")

                    rec = Recording(
                        session_id=session_row.id,
                        part="part2",
                        question_index=0,
                        question_text="Describe a course you completed",
                        transcript=f"answer {index}",
                        prompt_match_key=f"prompt:{index}",
                        weakness_tags=tags,
                        created_at=base + timedelta(days=index),
                    )
                    session.add(rec)
                    await session.flush()
                    created_ids.append(rec.id)

                await session.commit()
                return created_ids

        return self._run_async(_seed())

    def test_comparison_returns_previous_attempt_deltas_diff_and_follow_through(self):
        current_id, previous_id = self._seed_comparison_data()

        response = self.client.get(
            f"/api/speaking/comparisons/{current_id}",
            headers=self._auth_headers(),
        )
        self.assertEqual(response.status_code, 200)

        payload = response.json()
        self.assertEqual(payload["attempt_count"], 3)
        self.assertTrue(payload["comparison"])
        self.assertEqual(payload["comparison"]["current"]["recording_id"], current_id)
        self.assertEqual(payload["comparison"]["previous"]["recording_id"], previous_id)
        self.assertAlmostEqual(payload["comparison"]["score_deltas"]["overall"], 1.0)
        self.assertIn("transcript_diff", payload["comparison"])
        self.assertTrue(
            any(
                line.startswith("- ") or line.startswith("+ ")
                for line in payload["comparison"]["transcript_diff"]
            )
        )
        follow_through = payload["comparison"]["weakness_follow_through"]
        self.assertIn("short_answer", follow_through["addressed_tags"])
        self.assertIn("hesitation", follow_through["unchanged_tags"])
        self.assertIn("grammar_errors", follow_through["new_tags"])

    def test_comparison_returns_no_comparison_payload_when_no_previous_match(self):
        ids = self._seed_summary_data(count=1)
        response = self.client.get(
            f"/api/speaking/comparisons/{ids[0]}",
            headers=self._auth_headers(),
        )
        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(payload["attempt_count"], 1)
        self.assertIsNone(payload["comparison"])

    def test_weakness_summary_returns_top_tags_trend_and_suggestions(self):
        self._seed_summary_data(count=5)

        response = self.client.get(
            "/api/speaking/weakness-summary?limit=5",
            headers=self._auth_headers(),
        )
        self.assertEqual(response.status_code, 200)

        payload = response.json()
        self.assertEqual(payload["recent_count"], 5)
        self.assertEqual(payload["sample_size_label"], "recurring_pattern")
        self.assertEqual(payload["top_recurring_tags"][0]["tag"], "hesitation")
        self.assertEqual(payload["top_recurring_tags"][0]["count"], 3)
        self.assertEqual(payload["trend_direction"]["overall"], "up")
        self.assertTrue(
            any(
                item["tag"] == "hesitation"
                for item in payload["actionable_suggestions"]
            )
        )

    def test_weakness_summary_handles_small_samples_gracefully(self):
        self._seed_summary_data(count=2)

        response = self.client.get(
            "/api/speaking/weakness-summary?limit=20",
            headers=self._auth_headers(),
        )
        self.assertEqual(response.status_code, 200)

        payload = response.json()
        self.assertEqual(payload["recent_count"], 2)
        self.assertEqual(payload["sample_size_label"], "early_signal")
        self.assertIn("overall", payload["trend_direction"])


if __name__ == "__main__":
    unittest.main()
