"""Unit tests for Rule-Based PII & Secret Redaction Engine."""
import pytest
from vantage.security.pii_masker import PIIMasker, luhn_checksum
from vantage.ingest.normalizer import CanonicalVantageSpan


def test_luhn_checksum_validation():
    # Valid credit card numbers
    assert luhn_checksum("4532015112830366") is True
    assert luhn_checksum("4532-0151-1283-0366") is True
    
    # Invalid card-like 16-digit numbers
    assert luhn_checksum("1234567812345678") is False
    assert luhn_checksum("0000000000000000") is True  # 0 checksum
    assert luhn_checksum("1111111111111111") is False


def test_pii_scrub_ssn_email_api_key():
    text = "User email is user@company.com with SSN 123-45-6789 and API Key vg_live_abcdef12345678901234567890123456"
    scrubbed, detected = PIIMasker.scrub_text(text)

    assert "[REDACTED_EMAIL]" in scrubbed
    assert "[REDACTED_SSN]" in scrubbed
    assert "[REDACTED_API_KEY]" in scrubbed
    assert "user@company.com" not in scrubbed
    assert "123-45-6789" not in scrubbed
    assert "EMAIL" in detected
    assert "SSN" in detected
    assert "API_KEY" in detected


def test_scrub_canonical_span_metadata_flag():
    span = CanonicalVantageSpan(
        span_id="span-123",
        trace_id="trace-123",
        name="test_span",
        start_time="2026-09-03T12:00:00Z",
        end_time="2026-09-03T12:00:01Z",
        prompt="Please contact test@example.com for secret sk-1234567890abcdef1234567890abcdef",
        attributes={"user_note": "SSN 987-65-4321 included"},
    )

    scrubbed_span = PIIMasker.scrub_span(span)

    assert scrubbed_span.pii_scrubbed is True
    assert "EMAIL" in scrubbed_span.pii_types
    assert "API_KEY" in scrubbed_span.pii_types
    assert "SSN" in scrubbed_span.pii_types
    assert "[REDACTED_EMAIL]" in scrubbed_span.prompt
    assert "[REDACTED_SSN]" in scrubbed_span.attributes["user_note"]
