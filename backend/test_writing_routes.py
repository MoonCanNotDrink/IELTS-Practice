import os
import tempfile
import unittest
from unittest.mock import patch

from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.config import settings
from app.models import Base, User, WritingAttempt, WritingPrompt
from app.routes import writing as writing_module
from app.routes.writing import router as writing_router
from app.seed_data import SEED_WRITING_PROMPTS, seed_writing_prompts


class FakeUser:
    id = 1
    username = "tester"


class WritingRouteTests(unittest.TestCase):
    def setUp(self):
        self.db_fd, self.db_path = tempfile.mkstemp(suffix=".db", dir=str(settings.data_dir))
        os.close(self.db_fd)
        self.engine = create_async_engine(f"sqlite+aiosqlite:///{self.db_path}")
        self.session_factory = async_sessionmaker(self.engine, class_=AsyncSession, expire_on_commit=False)
        self._run_async(self._create_tables())
        self._run_async(self._create_user())

        app = FastAPI()
        app.include_router(writing_router)
        app.dependency_overrides = {
            writing_module.get_current_user: lambda: FakeUser(),
            writing_module.get_db: self._override_get_db,
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

    async def _create_user(self):
        async with self.session_factory() as session:
            session.add(User(id=FakeUser.id, username=FakeUser.username, hashed_password="x"))
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

    def _seed_prompts(self):
        async def _seed():
            async with self.session_factory() as session:
                await seed_writing_prompts(session)

        self._run_async(_seed())

    def _get_prompt(self, task_type: str) -> WritingPrompt:
        async def _query():
            async with self.session_factory() as session:
                result = await session.execute(
                    select(WritingPrompt).where(WritingPrompt.task_type == task_type).limit(1)
                )
                return result.scalars().first()

        return self._run_async(_query())

    def test_seed_writing_prompts_idempotent(self):
        self._seed_prompts()
        self._seed_prompts()

        async def _count_prompts():
            async with self.session_factory() as session:
                result = await session.execute(select(func.count(WritingPrompt.id)))
                return result.scalar_one()

        self.assertEqual(self._run_async(_count_prompts()), len(SEED_WRITING_PROMPTS))

    def test_seed_writing_prompts_updates_existing_prompt_details(self):
        async def _create_stale_prompt():
            async with self.session_factory() as session:
                session.add(
                    WritingPrompt(
                        slug="task1-library-visits-bar-chart",
                        task_type="task1",
                        title="Old title",
                        prompt_text="Old prompt",
                        prompt_details={},
                        source="seed",
                    )
                )
                await session.commit()

        self._run_async(_create_stale_prompt())
        self._seed_prompts()

        async def _query_prompt():
            async with self.session_factory() as session:
                result = await session.execute(
                    select(WritingPrompt).where(WritingPrompt.slug == "task1-library-visits-bar-chart")
                )
                return result.scalars().one()

        prompt = self._run_async(_query_prompt())
        self.assertEqual(prompt.title, "Task 1 · Library visits by age group")
        self.assertIn("chart_data", prompt.prompt_details)

    def test_random_prompt_rejects_invalid_task_type(self):
        self._seed_prompts()
        response = self.client.get(
            "/api/writing/prompts/random?task_type=task3",
            headers=self._auth_headers(),
        )
        self.assertEqual(response.status_code, 400)
        self.assertIn("task_type", response.json()["detail"])

    def test_create_attempt_rejects_blank_essay(self):
        self._seed_prompts()
        prompt = self._get_prompt("task1")
        response = self.client.post(
            "/api/writing/attempts",
            json={"prompt_id": prompt.id, "essay_text": "   "},
            headers=self._auth_headers(),
        )
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json()["detail"], "essay_text is required")

    def test_create_attempt_rejects_oversize_essay(self):
        self._seed_prompts()
        prompt = self._get_prompt("task2")
        response = self.client.post(
            "/api/writing/attempts",
            json={"prompt_id": prompt.id, "essay_text": "x" * 12001},
            headers=self._auth_headers(),
        )
        self.assertEqual(response.status_code, 400)
        self.assertIn("character limit", response.json()["detail"])

    def test_create_attempt_scores_and_persists_snapshot(self):
        self._seed_prompts()
        prompt = self._get_prompt("task1")

        async def fake_score_writing(**_kwargs):
            return {
                "task_score": 6.5,
                "task_feedback": "Addresses the main trends clearly.",
                "coherence_score": 6.0,
                "coherence_feedback": "Logical overall structure.",
                "lexical_score": 6.0,
                "lexical_feedback": "Adequate range of academic vocabulary.",
                "grammar_score": 6.0,
                "grammar_feedback": "Mostly accurate sentence control.",
                "overall_score": 6.0,
                "overall_feedback": "A solid response with room for sharper comparisons.",
                "key_improvements": ["Add clearer overview sentence."],
                "sample_answer": "Sample answer.",
            }

        with patch("app.routes.writing.score_writing", fake_score_writing):
            response = self.client.post(
                "/api/writing/attempts",
                json={
                    "prompt_id": prompt.id,
                    "essay_text": "The chart shows that adults visited the library most often.",
                },
                headers=self._auth_headers(),
            )

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(payload["module_type"], "writing")
        self.assertEqual(payload["task_type"], "task1")
        self.assertEqual(payload["scores"]["overall"], 6.0)
        self.assertEqual(payload["prompt"]["title"], prompt.title)

        async def _query_attempt():
            async with self.session_factory() as session:
                result = await session.execute(select(WritingAttempt).limit(1))
                return result.scalars().first()

        attempt = self._run_async(_query_attempt())
        self.assertIsNotNone(attempt)
        self.assertEqual(attempt.prompt_title, prompt.title)
        self.assertTrue(attempt.word_count > 0)

    def test_attempt_detail_is_user_scoped(self):
        self._seed_prompts()
        prompt = self._get_prompt("task2")

        async def fake_score_writing(**_kwargs):
            return {
                "task_score": 6.0,
                "task_feedback": "Reasonable response.",
                "coherence_score": 6.0,
                "coherence_feedback": "Reasonable organisation.",
                "lexical_score": 6.0,
                "lexical_feedback": "Reasonable range.",
                "grammar_score": 6.0,
                "grammar_feedback": "Reasonable control.",
                "overall_score": 6.0,
                "overall_feedback": "Reasonable overall quality.",
                "key_improvements": [],
                "sample_answer": "",
            }

        with patch("app.routes.writing.score_writing", fake_score_writing):
            create_response = self.client.post(
                "/api/writing/attempts",
                json={
                    "prompt_id": prompt.id,
                    "essay_text": "Online learning requires strong personal discipline.",
                },
                headers=self._auth_headers(),
            )

        attempt_id = create_response.json()["attempt_id"]

        other_app = FastAPI()
        other_app.include_router(writing_router)
        other_app.dependency_overrides = {
            writing_module.get_current_user: lambda: type("OtherUser", (), {"id": 2, "username": "other"})(),
            writing_module.get_db: self._override_get_db,
        }

        async def _create_other_user():
            async with self.session_factory() as session:
                result = await session.execute(select(User).where(User.id == 2))
                if result.scalars().first() is None:
                    session.add(User(id=2, username="other", hashed_password="x"))
                    await session.flush()
                    await session.commit()

        self._run_async(_create_other_user())

        with TestClient(other_app) as other_client:
            detail_response = other_client.get(
                f"/api/writing/attempts/{attempt_id}/detail",
                headers=self._auth_headers(),
            )
        self.assertEqual(detail_response.status_code, 403)


if __name__ == "__main__":
    unittest.main()
