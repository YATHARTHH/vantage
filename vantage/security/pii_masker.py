"""In-Flight Rule-Based PII & Secret Redaction Engine.

Executes BEFORE buffering or persistent database storage.
Uses regex rules + Luhn algorithm checksum validation for credit cards.
Never retains or logs raw sensitive values.
"""
from __future__ import annotations

import re
from typing import Any, Dict, List, Tuple
from vantage.ingest.normalizer import CanonicalVantageSpan


def luhn_checksum(card_number: str) -> bool:
    """Validates credit card numbers using the Luhn checksum algorithm."""
    digits = [int(c) for c in card_number if c.isdigit()]
    if len(digits) < 13 or len(digits) > 19:
        return False
    checksum = 0
    reverse_digits = digits[::-1]
    for i, digit in enumerate(reverse_digits):
        if i % 2 == 1:
            doubled = digit * 2
            checksum += doubled - 9 if doubled > 9 else doubled
        else:
            checksum += digit
    return checksum % 10 == 0


# Regex patterns for rule-based redaction
SSN_REGEX = re.compile(r"\b\d{3}-\d{2}-\d{4}\b")
EMAIL_REGEX = re.compile(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b")
API_KEY_REGEX = re.compile(
    r"\b(?:sk-[a-zA-Z0-9]{32,}|vg_live_[a-zA-Z0-9_-]{32,}|ghp_[a-zA-Z0-9]{36}|AKIA[0-9A-Z]{16}|Bearer\s+[a-zA-Z0-9._-]{32,})\b"
)
GENERIC_CARD_REGEX = re.compile(r"\b(?:\d[ -]*?){13,19}\b")


class PIIMasker:
    """Rule-based PII and secret redaction scanner."""

    @classmethod
    def scrub_text(cls, text: str) -> Tuple[str, List[str]]:
        """Scrubs PII and sensitive secrets from a string. Returns (scrubbed_text, detected_types)."""
        if not text:
            return text, []

        detected_types: set[str] = set()
        scrubbed = text

        # 1. SSN Scrubbing
        if SSN_REGEX.search(scrubbed):
            scrubbed = SSN_REGEX.sub("[REDACTED_SSN]", scrubbed)
            detected_types.add("SSN")

        # 2. API Key / Secret Scrubbing
        if API_KEY_REGEX.search(scrubbed):
            scrubbed = API_KEY_REGEX.sub("[REDACTED_API_KEY]", scrubbed)
            detected_types.add("API_KEY")

        # 3. Email Scrubbing
        if EMAIL_REGEX.search(scrubbed):
            scrubbed = EMAIL_REGEX.sub("[REDACTED_EMAIL]", scrubbed)
            detected_types.add("EMAIL")

        # 4. Credit Card Scrubbing with Luhn Verification
        cards_found = GENERIC_CARD_REGEX.findall(scrubbed)
        for candidate in cards_found:
            clean_digits = re.sub(r"\D", "", candidate)
            if luhn_checksum(clean_digits):
                scrubbed = scrubbed.replace(candidate, "[REDACTED_CREDIT_CARD]")
                detected_types.add("CREDIT_CARD")

        return scrubbed, sorted(list(detected_types))

    @classmethod
    def scrub_span(cls, span: CanonicalVantageSpan) -> CanonicalVantageSpan:
        """Scrubs sensitive data across all fields of a CanonicalVantageSpan in-place/copy."""
        all_detected: set[str] = set()

        # Scrub text fields
        text_fields = ["prompt", "completion", "system_prompt", "tool_input", "tool_output", "error_message"]
        for field in text_fields:
            val = getattr(span, field, None)
            if val and isinstance(val, str):
                scrubbed_val, detected = cls.scrub_text(val)
                if detected:
                    setattr(span, field, scrubbed_val)
                    all_detected.update(detected)

        # Scrub metadata attributes
        if span.attributes and isinstance(span.attributes, dict):
            new_attrs: Dict[str, Any] = {}
            for k, v in span.attributes.items():
                if isinstance(v, str):
                    scrubbed_v, detected = cls.scrub_text(v)
                    new_attrs[k] = scrubbed_v
                    all_detected.update(detected)
                else:
                    new_attrs[k] = v
            span.attributes = new_attrs

        if all_detected:
            span.pii_scrubbed = True
            span.pii_types = sorted(list(set(span.pii_types + list(all_detected))))

        return span
