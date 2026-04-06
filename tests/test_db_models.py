from datetime import datetime
from uuid import uuid4

from db.models import CachedAnalysis, Chunk, Document, Job, SourceRun


def test_document_model_fields():
    doc = Document(
        id=uuid4(),
        source_type="earnings",
        ticker="AAPL",
        published_at=datetime(2026, 4, 1),
        title="AAPL Q1 2026 Earnings Call",
        url="https://example.com/aapl-q1",
        raw_text="Revenue grew 12% year over year...",
    )
    assert doc.source_type == "earnings"
    assert doc.ticker == "AAPL"
    assert doc.title == "AAPL Q1 2026 Earnings Call"


def test_chunk_model_fields():
    doc_id = uuid4()
    chunk = Chunk(
        id=uuid4(),
        document_id=doc_id,
        chunk_text="Revenue grew 12% year over year",
        embedding=[0.1] * 1024,
        chunk_index=0,
    )
    assert chunk.document_id == doc_id
    assert chunk.chunk_index == 0
    assert len(chunk.embedding) == 1024


def test_source_run_model_fields():
    run = SourceRun(
        id=uuid4(),
        run_id="discovery-run-001",
        source_type="news",
        status="completed",
        documents_found=5,
        errors=None,
        completed_at=datetime(2026, 4, 5, 12, 0, 0),
    )
    assert run.status == "completed"
    assert run.documents_found == 5


def test_job_model_fields():
    job = Job(
        id=uuid4(),
        job_id="job-abc-123",
        symbol="TSLA",
        status="running",
        created_at=datetime(2026, 4, 5, 12, 0, 0),
    )
    assert job.symbol == "TSLA"
    assert job.status == "running"


def test_cached_analysis_model_fields():
    ca = CachedAnalysis(
        symbol="SPY",
        scanner_signals={"iv_percentile": 0.72},
        narrative="Elevated vol regime.",
        trade_recs=[{"strategy": "iron_condor"}],
        vol_surface={"skew": -0.08},
        phases_log=[{"phase": "scanner", "time": 1.1}],
        total_time=4.2,
    )
    assert ca.symbol == "SPY"
    assert ca.scanner_signals["iv_percentile"] == 0.72
    assert ca.narrative == "Elevated vol regime."
    assert len(ca.trade_recs) == 1
    assert ca.total_time == 4.2
