import os
import tempfile
import unittest
from datetime import datetime, timedelta

from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.config import settings
from app.models import Base, PracticeSession, Recording, User, WritingAttempt
from app.routes import dashboard as dashboard_module
from app.routes.dashboard import router as dashboard_router


class FakeUser:
    id = 1
    username = "tester"


class DashboardRouteTests(unittest.TestCase):
    def setUp(self):
        self.db_fd, self.db_path = tempfile.mkstemp(suffix=".db", dir=str(settings.data_dir))
        os.close(self.db_fd)
        self.engine = create_async_engine(f"sqlite+aiosqlite:///{self.db_path}")
        self.session_factory = async_sessionmaker(self.engine, class_=AsyncSession, expire_on_commit=False)
        self._run_async(self._create_tables())
        self._run_async(self._create_users())

        app = FastAPI()
        app.include_router(dashboard_router)
        app.dependency_overrides = {
            dashboard_module.get_current_user: lambda: FakeUser(),
            dashboard_module.get_db: self._override_get_db,
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
            session.add_all([
                User(id=1, username="tester", hashed_password="x"),
                User(id=2, username="other", hashed_password="x"),
            ])
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

    def _seed_entries(self):
        async def _seed():
            async with self.session_factory() as session:
                speaking_time = datetime.utcnow() - timedelta(hours=2)
                writing_time = datetime.utcnow() - timedelta(hours=1)
                foreign_time = datetime.utcnow()

                speaking = PracticeSession(
                    user_id=1,
                    status="completed",
                    finished_at=speaking_time,
                    overall_score=6.5,
                    fluency_score=6.5,
                    vocabulary_score=6.0,
                    grammar_score=6.0,
                    pronunciation_score=6.5,
                    feedback='{"overall_feedback": "ok"}',
                )
                session.add(speaking)
                await session.flush()
                session.add(
                    Recording(
                        session_id=speaking.id,
                        part="part2",
                        question_index=0,
                        question_text="Describe a skill you learned online",
                        transcript="I learned it by practicing every day.",
                    )
                )

                writing = WritingAttempt(
                    user_id=1,
                    task_type="task2",
                    prompt_title="Task 2 · Public transport investment",
                    prompt_text="Governments should spend more money on public transport...",
                    essay_text="Public transport deserves more investment because it benefits more citizens.",
                    word_count=11,
                    task_score=6.0,
                    coherence_score=6.0,
                    lexical_score=6.0,
                    grammar_score=6.0,
                    overall_score=6.0,
                    feedback='{"overall_feedback": "ok"}',
                    completed_at=writing_time,
                )
                session.add(writing)

                foreign = WritingAttempt(
                    user_id=2,
                    task_type="task1",
                    prompt_title="Foreign entry",
                    prompt_text="Foreign prompt",
                    essay_text="Foreign essay",
                    word_count=2,
                    task_score=5.0,
                    coherence_score=5.0,
                    lexical_score=5.0,
                    grammar_score=5.0,
                    overall_score=5.0,
                    feedback='{"overall_feedback": "ok"}',
                    completed_at=foreign_time,
                )
                session.add(foreign)
                await session.flush()
                await session.commit()

        self._run_async(_seed())

    def test_dashboard_history_merges_and_sorts_entries(self):
        self._seed_entries()
        response = self.client.get("/api/dashboard/history?limit=10", headers=self._auth_headers())
        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(len(payload), 2)
        self.assertEqual(payload[0]["module_type"], "writing")
        self.assertEqual(payload[1]["module_type"], "speaking")
        self.assertEqual(payload[0]["detail_api_path"], f"/api/writing/attempts/{payload[0]['id']}/detail")

    def test_dashboard_history_filters_module_and_task_type(self):
        self._seed_entries()
        response = self.client.get(
            "/api/dashboard/history?module_type=writing&task_type=task2",
            headers=self._auth_headers(),
        )
        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(len(payload), 1)
        self.assertEqual(payload[0]["module_type"], "writing")
        self.assertEqual(payload[0]["task_type"], "task2")
        self.assertNotIn("pronunciation", payload[0]["scores"])

    def test_dashboard_history_is_user_scoped(self):
        self._seed_entries()
        response = self.client.get("/api/dashboard/history?limit=10", headers=self._auth_headers())
        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertTrue(all(item["title"] != "Foreign entry" for item in payload))


if __name__ == "__main__":
    unittest.main()
