import os
import tempfile
import unittest

from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.config import settings
from app.models import Base, PracticeSession, Topic, User
from app.routes import exam as exam_module
from app.routes import part2 as part2_module
from app.routes.exam import router as exam_router
from app.routes.part2 import router as part2_router
from app.seed_data import (
    CURRENT_PART2_SEASON,
    LEGACY_PART2_SEASON,
    SEED_TOPICS,
    seed_topics,
)


class FakeUser:
    id = 1
    username = "tester"


class TopicBankSyncTests(unittest.TestCase):
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
        self._run_async(self._create_user())

        app = FastAPI()
        app.include_router(part2_router)
        app.include_router(exam_router)
        app.dependency_overrides = {
            part2_module.get_current_user: lambda: FakeUser(),
            exam_module.get_current_user: lambda: FakeUser(),
            part2_module.get_db: self._override_get_db,
            exam_module.get_db: self._override_get_db,
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

    def test_seed_topics_syncs_current_season_without_breaking_history(self):
        obsolete_topic_id = self._run_async(self._seed_topics_for_sync())

        self._run_async(self._run_seed_topics())

        summary = self._run_async(self._fetch_topic_summary(obsolete_topic_id))
        self.assertEqual(summary["current_count"], len(SEED_TOPICS))
        self.assertIn(
            "Describe a famous person you would like to meet.",
            summary["current_titles"],
        )
        self.assertNotIn("Temporary current season topic", summary["current_titles"])
        self.assertEqual(summary["legacy_old_season_count"], 1)
        self.assertEqual(summary["preserved_history_season"], LEGACY_PART2_SEASON)

    def test_part2_routes_only_return_current_season_topics(self):
        ids = self._run_async(self._seed_topics_for_routes())

        response = self.client.get("/api/part2/topics", headers=self._auth_headers())
        self.assertEqual(response.status_code, 200)
        titles = [item["title"] for item in response.json()]
        self.assertEqual(titles, ["Current season topic"])

        response = self.client.get(
            "/api/part2/free-practice-topics", headers=self._auth_headers()
        )
        self.assertEqual(response.status_code, 200)
        official_titles = [item["title"] for item in response.json()["official_topics"]]
        self.assertEqual(official_titles, ["Current season topic"])

        response = self.client.post(
            "/api/part2/sessions",
            json={"topic_id": ids["legacy_id"]},
            headers=self._auth_headers(),
        )
        self.assertEqual(response.status_code, 404)

        response = self.client.post(
            "/api/part2/sessions",
            json={"topic_id": ids["current_id"]},
            headers=self._auth_headers(),
        )
        self.assertEqual(response.status_code, 200)

    def test_exam_start_rejects_legacy_topic_ids(self):
        ids = self._run_async(self._seed_topics_for_routes())

        response = self.client.post(
            "/api/exam/start",
            json={"topic_id": ids["legacy_id"]},
            headers=self._auth_headers(),
        )
        self.assertEqual(response.status_code, 404)

        response = self.client.post(
            "/api/exam/start",
            json={"topic_id": ids["current_id"]},
            headers=self._auth_headers(),
        )
        self.assertEqual(response.status_code, 200)

    async def _run_seed_topics(self):
        async with self.session_factory() as session:
            await seed_topics(session)

    async def _seed_topics_for_sync(self) -> int:
        async with self.session_factory() as session:
            legacy_topic = Topic(
                title="Describe a place you visited that was very crowded",
                points=["Where it was", "When you went there", "Why it was crowded"],
                category="places",
                season="2025-Q1",
            )
            obsolete_topic = Topic(
                title="Current season topic with history",
                points=["Who", "When", "Why"],
                category="general",
                season=CURRENT_PART2_SEASON,
            )
            removable_topic = Topic(
                title="Temporary current season topic",
                points=["Who", "When", "Why"],
                category="general",
                season=CURRENT_PART2_SEASON,
            )
            session.add_all([legacy_topic, obsolete_topic, removable_topic])
            await session.flush()
            session.add(
                PracticeSession(
                    user_id=FakeUser.id,
                    topic_id=obsolete_topic.id,
                    status="completed",
                )
            )
            await session.commit()
            return obsolete_topic.id

    async def _fetch_topic_summary(self, obsolete_topic_id: int) -> dict:
        async with self.session_factory() as session:
            current_result = await session.execute(
                select(Topic).where(Topic.season == CURRENT_PART2_SEASON)
            )
            current_topics = current_result.scalars().all()

            legacy_result = await session.execute(
                select(Topic).where(
                    Topic.title == "Describe a place you visited that was very crowded",
                    Topic.season == "2025-Q1",
                )
            )
            preserved_topic = await session.get(Topic, obsolete_topic_id)

            return {
                "current_count": len(current_topics),
                "current_titles": {topic.title for topic in current_topics},
                "legacy_old_season_count": len(legacy_result.scalars().all()),
                "preserved_history_season": preserved_topic.season if preserved_topic else None,
            }

    async def _seed_topics_for_routes(self) -> dict:
        async with self.session_factory() as session:
            legacy_topic = Topic(
                title="Legacy topic",
                points=["Where", "When", "Why"],
                category="places",
                season="2025-Q1",
            )
            current_topic = Topic(
                title="Current season topic",
                points=["Who", "When", "Why"],
                category="people",
                season=CURRENT_PART2_SEASON,
            )
            session.add_all([legacy_topic, current_topic])
            await session.flush()
            await session.commit()
            return {"legacy_id": legacy_topic.id, "current_id": current_topic.id}


if __name__ == "__main__":
    unittest.main()
