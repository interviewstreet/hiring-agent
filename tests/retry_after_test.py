"""Tests for Retry-After header parsing in OpenAICompatibleProvider (#386).

The HTTP spec allows Retry-After as either a numeric delay in seconds or an
HTTP-date string.  The provider must handle both without crashing.
"""

import sys
from pathlib import Path
from datetime import datetime, timezone, timedelta

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from models import OpenAICompatibleProvider


def test_numeric_retry_after():
    result = OpenAICompatibleProvider._parse_retry_after("120")
    assert result == 120.0


def test_numeric_retry_after_float():
    result = OpenAICompatibleProvider._parse_retry_after("30.5")
    assert result == 30.5


def test_http_date_retry_after():
    future = datetime.now(timezone.utc) + timedelta(seconds=60)
    http_date = future.strftime("%a, %d %b %Y %H:%M:%S GMT")
    result = OpenAICompatibleProvider._parse_retry_after(http_date)
    assert result is not None
    assert 55 <= result <= 65


def test_http_date_in_past_returns_zero():
    past = datetime.now(timezone.utc) - timedelta(seconds=10)
    http_date = past.strftime("%a, %d %b %Y %H:%M:%S GMT")
    result = OpenAICompatibleProvider._parse_retry_after(http_date)
    assert result == 0


def test_invalid_value_returns_none():
    result = OpenAICompatibleProvider._parse_retry_after("not-a-date-or-number")
    assert result is None


def test_empty_string_returns_none():
    result = OpenAICompatibleProvider._parse_retry_after("")
    assert result is None
