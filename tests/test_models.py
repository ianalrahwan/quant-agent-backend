import json

from models.common import JobResponse, JobStatus, ScannerSignals
from models.events import CheckpointEvent, DoneEvent, PhaseEvent, StreamEvent


def test_scanner_signals():
    signals = ScannerSignals(
        iv_percentile=0.85,
        skew_kurtosis=0.6,
        dealer_gamma=-0.3,
        term_structure=0.9,
        vanna=0.7,
        charm=0.4,
        composite=0.72,
    )
    assert signals.composite == 0.72


def test_job_response():
    resp = JobResponse(job_id="job-123")
    assert resp.job_id == "job-123"


def test_job_status():
    status = JobStatus(job_id="job-123", status="running", symbol="AAPL")
    assert status.status == "running"


def test_phase_event_serializes():
    event = PhaseEvent(phase="vol_surface", status="complete", data={"regime": "backwardation"})
    sse = event.to_sse()
    assert sse.event == "phase"
    payload = json.loads(sse.data)
    assert payload["phase"] == "vol_surface"
    assert payload["data"]["regime"] == "backwardation"


def test_checkpoint_event_serializes():
    event = CheckpointEvent(checkpoint="vol_surface_review", message="Continue?")
    sse = event.to_sse()
    assert sse.event == "checkpoint"
    payload = json.loads(sse.data)
    assert payload["checkpoint"] == "vol_surface_review"


def test_stream_event_serializes():
    event = StreamEvent(phase="synthesis", token="The")
    sse = event.to_sse()
    assert sse.event == "stream"
    payload = json.loads(sse.data)
    assert payload["token"] == "The"


def test_done_event_serializes():
    event = DoneEvent(job_id="job-123", total_time=47.2)
    sse = event.to_sse()
    assert sse.event == "done"
    payload = json.loads(sse.data)
    assert payload["total_time"] == 47.2


def test_log_event_serializes():
    from models.events import LogEvent

    event = LogEvent(message="Crawling earnings for AAPL...", phase="crawl_earnings")
    sse = event.to_sse()
    assert sse.event == "log"
    payload = json.loads(sse.data)
    assert payload["message"] == "Crawling earnings for AAPL..."
    assert payload["phase"] == "crawl_earnings"


def test_log_event_no_phase():
    from models.events import LogEvent

    event = LogEvent(message="Starting analysis...")
    sse = event.to_sse()
    payload = json.loads(sse.data)
    assert payload["message"] == "Starting analysis..."
    assert payload["phase"] is None
