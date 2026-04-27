"""
Guardrails module for PawPal+ — validates AI output before it reaches the user.
Catches empty responses, low-confidence answers, and dangerous content patterns.
"""

import logging
import re
from typing import Dict, Tuple

logger = logging.getLogger("pawpal.guardrails")

# Patterns that must NEVER appear in pet care advice (safety-critical)
BLOCKED_PATTERNS = [
    r"\bibuprofen\b",
    r"\btylenol\b",
    r"\baspirin\b",
    r"\bacetaminophen\b",
    r"\bno\s+need\s+(?:to\s+see\s+)?a\s+vet\b",
    r"\byou\s+can\s+diagnose\b",

]

CONFIDENCE_THRESHOLD = 0.4
MIN_ANSWER_WORDS = 5


def validate_response(response: Dict) -> Tuple[bool, str, Dict]:
    """
    Run a multi-stage validation on an AI-generated response.

    Checks (in order):
      1. Not empty or too short
      2. Confidence above threshold
      3. No dangerous medication/safety patterns
      4. Warns if no retrieval context was used

    Args:
        response: dict with keys 'answer', 'confidence', 'retrieved_chunks'

    Returns:
        (is_valid: bool, status: str, updated_response: dict)
        status is one of: "ok", "low_confidence", "no_retrieval", or an error message.
    """
    answer = response.get("answer", "").strip()
    confidence = float(response.get("confidence", 0.0))
    chunks = int(response.get("retrieved_chunks", 0))

    # ── Check 1: Empty / too short ────────────────────────────────────────────
    if not answer or len(answer.split()) < MIN_ANSWER_WORDS:
        logger.warning("GUARDRAIL FAIL: Response too short (%d words).", len(answer.split()))
        return False, "Response was too short or empty. Please try rephrasing.", response

    # ── Check 2: Low confidence ───────────────────────────────────────────────
    if confidence < CONFIDENCE_THRESHOLD:
        logger.warning("GUARDRAIL WARN: Low confidence (%.2f) — adding disclaimer.", confidence)
        response["answer"] = (
            f"⚠️ Low-confidence answer (no matching documents found):\n\n{answer}\n\n"
            "_Please consult a licensed veterinarian for accurate advice._"
        )
        return True, "low_confidence", response

    # ── Check 3: Dangerous content ────────────────────────────────────────────
    lower = answer.lower()
    for pattern in BLOCKED_PATTERNS:
        if re.search(pattern, lower):
            logger.error("GUARDRAIL BLOCK: Dangerous pattern matched — '%s'", pattern)
            return (
                False,
                "This response was blocked by safety guardrails. Please consult a vet.",
                response,
            )

    # ── Check 4: No retrieval context ─────────────────────────────────────────
    if chunks == 0:
        logger.warning("GUARDRAIL WARN: Zero chunks retrieved — answer may not be grounded.")
        response["answer"] += (
            "\n\n⚠️ _Note: This answer was generated without matching documents "
            "from the knowledge base._"
        )
        return True, "no_retrieval", response

    logger.info("GUARDRAIL PASS — confidence=%.2f, chunks=%d", confidence, chunks)
    return True, "ok", response
