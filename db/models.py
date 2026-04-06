from datetime import datetime
from uuid import UUID, uuid4

from pgvector.sqlalchemy import Vector
from sqlalchemy import JSON, DateTime, Float, Integer, String, Text, func
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    pass


class Document(Base):
    __tablename__ = "documents"

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    source_type: Mapped[str] = mapped_column(String(50))
    ticker: Mapped[str] = mapped_column(String(10), index=True)
    published_at: Mapped[datetime] = mapped_column(DateTime)
    title: Mapped[str] = mapped_column(String(500))
    url: Mapped[str] = mapped_column(String(2000))
    raw_text: Mapped[str] = mapped_column(Text)


class Chunk(Base):
    __tablename__ = "chunks"

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    document_id: Mapped[UUID] = mapped_column(index=True)
    chunk_text: Mapped[str] = mapped_column(Text)
    embedding = mapped_column(Vector(1024))
    chunk_index: Mapped[int] = mapped_column(Integer)


class SourceRun(Base):
    __tablename__ = "source_runs"

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    run_id: Mapped[str] = mapped_column(String(100), index=True)
    source_type: Mapped[str] = mapped_column(String(50))
    status: Mapped[str] = mapped_column(String(20))
    documents_found: Mapped[int] = mapped_column(Integer, default=0)
    errors: Mapped[str | None] = mapped_column(Text, nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)


class Job(Base):
    __tablename__ = "jobs"

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    job_id: Mapped[str] = mapped_column(String(100), unique=True, index=True)
    symbol: Mapped[str] = mapped_column(String(10))
    status: Mapped[str] = mapped_column(String(20), default="pending")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)


class CachedAnalysis(Base):
    """Pre-computed analysis results for instant loading."""

    __tablename__ = "cached_analyses"

    symbol: Mapped[str] = mapped_column(String(10), primary_key=True)
    scanner_signals: Mapped[dict] = mapped_column(JSON, nullable=False)
    narrative: Mapped[str] = mapped_column(Text, nullable=False, default="")
    trade_recs: Mapped[list] = mapped_column(JSON, nullable=False, default=list)
    vol_surface: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    phases_log: Mapped[list] = mapped_column(JSON, nullable=False, default=list)
    total_time: Mapped[float | None] = mapped_column(Float, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )


class ScannerResult(Base):
    """Pre-computed scanner scores for instant page load."""

    __tablename__ = "scanner_results"

    symbol: Mapped[str] = mapped_column(String(10), primary_key=True)
    scores: Mapped[dict] = mapped_column(JSON, nullable=False)
    composite: Mapped[float] = mapped_column(Float, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )
