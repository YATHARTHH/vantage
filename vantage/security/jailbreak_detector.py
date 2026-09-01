from vantage.domain.events import TelemetryEnvelope, LLMCallData, ToolCallData
from vantage.security.models import SecurityScanResult, SecurityThreatType, SecurityRiskLevel
from vantage.security.scanner import AbstractSecurityScanner
from vantage.security.normalizer import TextNormalizer
from vantage.security.decoder import PayloadDecoder
from vantage.security.rules import SECURITY_RULES


def extract_scan_text(envelope: TelemetryEnvelope) -> str | None:
    """
    Explicit scan input boundary:
    Extracts scan target text from LLMCallData.prompt_preview or ToolCallData.tool_input.
    Arbitrary metadata tags are NEVER scanned.
    """
    if isinstance(envelope.payload, LLMCallData):
        return envelope.payload.prompt_preview
    elif isinstance(envelope.payload, ToolCallData):
        return envelope.payload.tool_input
    return None


class JailbreakDetector(AbstractSecurityScanner):
    """
    Low-Latency Local Security Engine implementing AbstractSecurityScanner strategy.
    
    Pipeline Steps:
    1. Extract prompt text via extract_scan_text
    2. Normalize text using TextNormalizer
    3. Safely decode candidate payloads using PayloadDecoder
    4. Match against deterministic SECURITY_RULES
    5. Calculate weighted score: score = min(sum(weights), 1.0)
    6. Map score to risk level (LOW, MEDIUM, HIGH, CRITICAL)
    """
    def __init__(self, scanner_version: str = "v1.0.0"):
        self.scanner_version = scanner_version

    def scan_text(self, text: str) -> SecurityScanResult:
        if not text or not text.strip():
            return SecurityScanResult(scanner_version=self.scanner_version)

        # 1. Text Normalization
        normalized = TextNormalizer.normalize(text)
        texts_to_check = [normalized]

        # 2. Safe Payload Decoding (Base64 / URL)
        decoded_payloads = PayloadDecoder.decode_candidates(text)
        has_encoded_payload = False
        for decoded in decoded_payloads:
            norm_decoded = TextNormalizer.normalize(decoded)
            if norm_decoded and norm_decoded not in texts_to_check:
                texts_to_check.append(norm_decoded)
                has_encoded_payload = True

        matched_rule_ids: list[str] = []
        evidence_list: list[str] = []
        threat_types_set: set[SecurityThreatType] = set()
        accumulated_score: float = 0.0

        if has_encoded_payload:
            threat_types_set.add(SecurityThreatType.ENCODED_PAYLOAD)
            evidence_list.append("encoded_payload_detected")
            accumulated_score += 0.20

        # 3. Deterministic Rule Matching
        for rule in SECURITY_RULES:
            matched = False
            for target_str in texts_to_check:
                if rule.pattern.search(target_str):
                    matched = True
                    break
            
            if matched:
                matched_rule_ids.append(rule.rule_id)
                threat_types_set.add(rule.threat_type)
                if rule.evidence_descriptor not in evidence_list:
                    evidence_list.append(rule.evidence_descriptor)
                accumulated_score += rule.weight

        # 4. Multi-Match Bonus
        if len(matched_rule_ids) > 1:
            accumulated_score += 0.10

        final_score = round(min(accumulated_score, 1.0), 2)
        is_threat = final_score >= 0.25

        # 5. Risk Level Mapping Policy
        if final_score >= 0.75:
            risk_level = SecurityRiskLevel.CRITICAL
        elif final_score >= 0.50:
            risk_level = SecurityRiskLevel.HIGH
        elif final_score >= 0.25:
            risk_level = SecurityRiskLevel.MEDIUM
        else:
            risk_level = SecurityRiskLevel.LOW

        return SecurityScanResult(
            is_threat=is_threat,
            threat_types=list(threat_types_set),
            threat_score=final_score,
            risk_level=risk_level,
            matched_rules=matched_rule_ids,
            evidence=evidence_list,
            scanner_version=self.scanner_version,
        )

    def scan_envelope(self, envelope: TelemetryEnvelope) -> SecurityScanResult:
        prompt_text = extract_scan_text(envelope)
        if not prompt_text:
            return SecurityScanResult(scanner_version=self.scanner_version)
        return self.scan_text(prompt_text)
