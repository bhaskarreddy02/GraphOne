"""
Unit tests for date normalization and 24-hour freshness validation
"""

import pytest
from datetime import datetime, timezone, timedelta
from src.crawler.date_normalizer import DateNormalizer


def test_relative_date_freshness():
    # 2 hours ago must be fresh
    iso_date, is_fresh = DateNormalizer.normalize_to_iso("2 hours ago")
    assert iso_date is not None
    assert is_fresh is True

    # 45 minutes ago must be fresh
    iso_date, is_fresh = DateNormalizer.normalize_to_iso("45 mins ago")
    assert is_fresh is True

    # 5 days ago must NOT be fresh
    iso_date, is_fresh = DateNormalizer.normalize_to_iso("5 days ago")
    assert iso_date is not None
    assert is_fresh is False


def test_iso_freshness():
    now = datetime.now(timezone.utc)
    fresh_iso = (now - timedelta(hours=3)).isoformat()
    old_iso = (now - timedelta(hours=48)).isoformat()

    _, is_fresh = DateNormalizer.normalize_to_iso(fresh_iso)
    assert is_fresh is True

    _, is_old = DateNormalizer.normalize_to_iso(old_iso)
    assert is_old is False


def test_rfc2822_date():
    raw = "Thu, 10 Sep 2026 10:00:00 +0000"
    dt = DateNormalizer.parse_date(raw)
    assert dt is not None
    assert dt.year == 2026
