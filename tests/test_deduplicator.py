"""
Unit tests for content deduplication and canonical URL hashing.
"""

from src.pipeline.deduplicator import ContentDeduplicator


def test_canonical_url_strips_tracking():
    raw_url = "https://techcrunch.com/2026/09/10/new-ai-startup/?utm_source=twitter&utm_medium=social&ref=producthunt#comments"
    expected = "https://techcrunch.com/2026/09/10/new-ai-startup"
    canonical = ContentDeduplicator.canonicalize_url(raw_url)
    assert canonical == expected


def test_canonical_url_preserves_clean_query():
    raw_url = "https://example.com/jobs?category=ai&sort=latest"
    canonical = ContentDeduplicator.canonicalize_url(raw_url)
    assert "category=ai" in canonical
    assert "sort=latest" in canonical


def test_dedup_hash_stable():
    url1 = "https://techcrunch.com/article-one?utm_source=newsletter"
    url2 = "https://techcrunch.com/article-one/"

    hash1 = ContentDeduplicator.compute_item_hash("TechCrunch AI", url1, "Sample Title")
    hash2 = ContentDeduplicator.compute_item_hash("TechCrunch AI", url2, "Sample Title")

    # Both resolve to the exact same canonical URL and therefore identical hashes
    assert hash1 == hash2


def test_fallback_hash_when_no_url():
    hash1 = ContentDeduplicator.compute_item_hash("Jobicy", "", "Senior AI Engineer", "2026-09-10")
    hash2 = ContentDeduplicator.compute_item_hash("Jobicy", "", "  SENIOR AI ENGINEER  ", "2026-09-10T14:20:00Z")

    assert hash1 == hash2
