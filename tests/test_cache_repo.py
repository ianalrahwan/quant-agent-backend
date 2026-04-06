"""Tests for data.cache_repo CRUD functions."""

from datetime import datetime
from unittest.mock import AsyncMock, MagicMock

import pytest

from data.cache_repo import (
    delete_stale_analyses,
    get_cached_analysis,
    upsert_cached_analysis,
)
from db.models import CachedAnalysis


@pytest.fixture
def mock_session():
    session = AsyncMock()
    session.execute = AsyncMock()
    session.commit = AsyncMock()
    return session


@pytest.fixture
def sample_kwargs():
    return {
        "symbol": "AAPL",
        "scanner_signals": {"iv_percentile": 0.85},
        "narrative": "Vol is elevated.",
        "trade_recs": [{"strategy": "put_spread"}],
        "vol_surface": {"skew": -0.12},
        "phases_log": [{"phase": "scanner", "time": 1.2}],
        "total_time": 3.5,
    }


@pytest.mark.asyncio
async def test_upsert_calls_execute_and_commit(mock_session, sample_kwargs):
    await upsert_cached_analysis(mock_session, **sample_kwargs)
    mock_session.execute.assert_awaited_once()
    mock_session.commit.assert_awaited_once()


@pytest.mark.asyncio
async def test_get_cached_analysis_returns_row(mock_session):
    row = CachedAnalysis(
        symbol="AAPL",
        scanner_signals={"iv_percentile": 0.85},
        narrative="Vol is elevated.",
        trade_recs=[],
        phases_log=[],
    )
    result_mock = MagicMock()
    result_mock.scalar_one_or_none.return_value = row
    mock_session.execute.return_value = result_mock

    result = await get_cached_analysis(mock_session, "AAPL")
    assert result is not None
    assert result.symbol == "AAPL"
    mock_session.execute.assert_awaited_once()


@pytest.mark.asyncio
async def test_get_cached_analysis_returns_none(mock_session):
    result_mock = MagicMock()
    result_mock.scalar_one_or_none.return_value = None
    mock_session.execute.return_value = result_mock

    result = await get_cached_analysis(mock_session, "XYZ")
    assert result is None


@pytest.mark.asyncio
async def test_delete_stale_calls_execute_and_commit(mock_session):
    await delete_stale_analyses(mock_session, max_age_seconds=1800)
    mock_session.execute.assert_awaited_once()
    mock_session.commit.assert_awaited_once()
