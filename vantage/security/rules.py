import re
from dataclasses import dataclass
from vantage.security.models import SecurityThreatType


@dataclass
class SecurityRule:
    rule_id: str
    threat_type: SecurityThreatType
    weight: float
    pattern: re.Pattern
    evidence_descriptor: str


# Weighted Rules for OWASP LLM01 Threat Categories
SECURITY_RULES: list[SecurityRule] = [
    # 1. Instruction Override
    SecurityRule(
        rule_id="override_001",
        threat_type=SecurityThreatType.INSTRUCTION_OVERRIDE,
        weight=0.35,
        pattern=re.compile(r"ignore\s+(?:all\s+)?(?:previous|prior|above)\s+instructions?", re.IGNORECASE),
        evidence_descriptor="instruction_override_phrase"
    ),
    SecurityRule(
        rule_id="override_002",
        threat_type=SecurityThreatType.INSTRUCTION_OVERRIDE,
        weight=0.35,
        pattern=re.compile(r"disregard\s+(?:all\s+)?(?:previous|system|prompt)\s+(?:rules|instructions)", re.IGNORECASE),
        evidence_descriptor="disregard_system_rules"
    ),
    SecurityRule(
        rule_id="override_003",
        threat_type=SecurityThreatType.INSTRUCTION_OVERRIDE,
        weight=0.30,
        pattern=re.compile(r"forget\s+(?:your|all)\s+(?:rules|instructions|constraints)", re.IGNORECASE),
        evidence_descriptor="forget_constraints_request"
    ),

    # 2. Prompt Leak & System Extraction
    SecurityRule(
        rule_id="leak_001",
        threat_type=SecurityThreatType.PROMPT_LEAK,
        weight=0.30,
        pattern=re.compile(r"(?:print|output|display|show|repeat)\s+(?:your\s+)?(?:system|initial)\s+(?:prompt|instructions)", re.IGNORECASE),
        evidence_descriptor="system_prompt_extraction_request"
    ),
    SecurityRule(
        rule_id="leak_002",
        threat_type=SecurityThreatType.PROMPT_LEAK,
        weight=0.30,
        pattern=re.compile(r"what\s+(?:are|were)\s+your\s+original\s+instructions", re.IGNORECASE),
        evidence_descriptor="original_instructions_query"
    ),

    # 3. Role-play Bypass / Persona Jailbreak
    SecurityRule(
        rule_id="roleplay_001",
        threat_type=SecurityThreatType.ROLEPLAY_BYPASS,
        weight=0.30,
        pattern=re.compile(r"\bdan\s+mode\b|do\s+anything\s+now|developer\s+mode\s+enabled", re.IGNORECASE),
        evidence_descriptor="dan_persona_bypass"
    ),
    SecurityRule(
        rule_id="roleplay_002",
        threat_type=SecurityThreatType.ROLEPLAY_BYPASS,
        weight=0.25,
        pattern=re.compile(r"you\s+are\s+now\s+unfiltered|without\s+(?:any\s+)?ethical\s+restrictions", re.IGNORECASE),
        evidence_descriptor="unfiltered_persona_override"
    ),

    # 4. Indirect Injection (External Untrusted Content Injection)
    SecurityRule(
        rule_id="indirect_001",
        threat_type=SecurityThreatType.INDIRECT_INJECTION,
        weight=0.30,
        pattern=re.compile(r"\[system\s*:\s*override\]|\<system_instruction_override\>", re.IGNORECASE),
        evidence_descriptor="indirect_markup_injection"
    ),

    # 5. Tool Manipulation
    SecurityRule(
        rule_id="tool_001",
        threat_type=SecurityThreatType.TOOL_MANIPULATION,
        weight=0.40,
        pattern=re.compile(r"call\s+tool\s+with\s+param|exec(?:ute)?\s+command\s*\(|drop\s+table\b", re.IGNORECASE),
        evidence_descriptor="arbitrary_tool_manipulation"
    ),
]
