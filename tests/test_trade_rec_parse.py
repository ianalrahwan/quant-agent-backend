"""Tests for _strip_code_fences in trade_rec module."""

import json

from graphs.trader.nodes.trade_rec import _strip_code_fences

SAMPLE_JSON = '[{"strategy": "calendar_spread", "direction": "long"}]'


def test_strip_json_code_fence():
    """JSON wrapped in ```json ... ``` fences strips correctly and parses."""
    wrapped = f"```json\n{SAMPLE_JSON}\n```"
    result = _strip_code_fences(wrapped)
    assert result == SAMPLE_JSON
    parsed = json.loads(result)
    assert parsed[0]["strategy"] == "calendar_spread"


def test_plain_json_unchanged():
    """Plain JSON with no fences is unchanged and parses."""
    result = _strip_code_fences(SAMPLE_JSON)
    assert result == SAMPLE_JSON
    parsed = json.loads(result)
    assert parsed[0]["strategy"] == "calendar_spread"


def test_strip_bare_code_fence():
    """JSON wrapped in ``` ... ``` (no language tag) strips correctly and parses."""
    wrapped = f"```\n{SAMPLE_JSON}\n```"
    result = _strip_code_fences(wrapped)
    assert result == SAMPLE_JSON
    parsed = json.loads(result)
    assert parsed[0]["strategy"] == "calendar_spread"
