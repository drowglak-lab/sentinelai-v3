import re
import logging

logger = logging.getLogger("sentinel_ai.security")

# Pre-compiled patterns for zero-latency execution
COMPILED_PATTERNS = {
    "IBAN": re.compile(r"[A-Z]{2}\d{2}[A-Z0-9]{11,30}"),
    "CARD": re.compile(r"\b(?:\d[ -]?){13,16}\b"),
    "EMAIL": re.compile(r"[\w\.-]+@[\w\.-]+\.[a-z]{2,}")
}

def scrub_pii(text: str) -> str:
    """
    High-performance PII Detection for FinTech.
    Designed for zero-blocking execution inside a PEP 734 subinterpreter.
    """
    if not text:
        return text

    # Phase 1: Fast deterministic masking
    for label, pattern in COMPILED_PATTERNS.items():
        text = pattern.sub(f"[{label}_REDACTED]", text)

    return text
