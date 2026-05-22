import os
from datetime import datetime, timezone

from sqlalchemy import Column, Integer, Float, String, Boolean, DateTime, JSON, Text
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from sqlalchemy.orm import DeclarativeBase

DATABASE_URL = os.environ.get(
    "DATABASE_URL",
    "postgresql+asyncpg://releaseguard:releaseguard@localhost:5432/releaseguard"
)

engine = create_async_engine(DATABASE_URL)
async_session = async_sessionmaker(engine, expire_on_commit=False)


class Base(DeclarativeBase):
    pass


class Evaluation(Base):
    __tablename__ = "evaluations"

    id = Column(Integer, primary_key=True, autoincrement=True)
    repo = Column(String(255), nullable=False, index=True)
    pr_number = Column(Integer, nullable=False)
    sha = Column(String(40), nullable=False)
    pr_title = Column(String(500))
    risk_score = Column(Float, nullable=False)
    risk_level = Column(String(20), nullable=False)
    recommendation = Column(String(100), nullable=False)
    plugin_results = Column(JSON, nullable=False)  # serialized list of plugin results
    summary = Column(Text)
    evaluated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))


async def init_db():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


async def store_evaluation(
    repo: str,
    pr_number: int,
    sha: str,
    pr_title: str,
    risk_score: float,
    risk_level: str,
    recommendation: str,
    plugin_results: list,
    summary: str,
) -> int:
    """Store evaluation and return its ID."""
    record = Evaluation(
        repo=repo,
        pr_number=pr_number,
        sha=sha,
        pr_title=pr_title,
        risk_score=risk_score,
        risk_level=risk_level,
        recommendation=recommendation,
        plugin_results=plugin_results,
        summary=summary,
    )
    async with async_session() as session:
        session.add(record)
        await session.commit()
        await session.refresh(record)
        return record.id
