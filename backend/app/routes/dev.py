"""Dev utility routes (reset DB, re-seed topics, etc.)"""

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import delete, select, text

from app.database import get_db
from app.models import Topic, PracticeSession, Recording
from app.seed_data import seed_topics, SEED_TOPICS

router = APIRouter(prefix="/api/dev", tags=["Dev Tools"])


@router.post("/reset-topics")
async def reset_and_reseed_topics(db: AsyncSession = Depends(get_db)):
    """
    Delete all existing topics and reseed with the latest topic bank.
    Use when you've added new topics to seed_data.py.
    """
    await db.execute(delete(Topic))
    await db.commit()
    await seed_topics(db)
    count_result = await db.execute(select(Topic))
    count = len(count_result.scalars().all())
    return {"message": f"Reseeded {count} topics successfully"}


@router.get("/topics/count")
async def topic_count(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Topic))
    topics = result.scalars().all()
    by_category = {}
    for t in topics:
        by_category.setdefault(t.category, 0)
        by_category[t.category] += 1
    return {"total": len(topics), "by_category": by_category}


@router.get("/sessions/count")
async def session_count(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(PracticeSession))
    sessions = result.scalars().all()
    return {
        "total": len(sessions),
        "completed": sum(1 for s in sessions if s.status == "completed"),
        "in_progress": sum(1 for s in sessions if s.status == "in_progress"),
    }
