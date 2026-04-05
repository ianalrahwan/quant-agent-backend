from pydantic import BaseModel


class ScannerSignals(BaseModel):
    """Scanner scores passed from the frontend."""

    iv_percentile: float
    skew_kurtosis: float
    dealer_gamma: float
    term_structure: float
    vanna: float
    charm: float
    composite: float


class JobResponse(BaseModel):
    """Returned when a job is created."""

    job_id: str


class JobStatus(BaseModel):
    """Current status of a job."""

    job_id: str
    status: str
    symbol: str
