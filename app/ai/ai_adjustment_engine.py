from typing import Tuple, Dict, Any

AI_CONFIDENCE_THRESHOLD = 0.60


def apply_ai_adjustments(
    governance_score: float,
    coverage: float,
    ai_insight: Dict[str, Any]
) -> Tuple[float, float]:
    """
    Applies AI-based adjustments using structured caps,
    not arbitrary subtraction.

    Returns:
        (adjusted_governance_score, adjusted_coverage)
    """

    if not ai_insight:
        return governance_score, coverage

    confidence = ai_insight.get("confidence", 0)

    # Only apply if AI confidence strong enough
    if confidence < AI_CONFIDENCE_THRESHOLD:
        return governance_score, coverage

    # --------------------------------------------------
    # 1️⃣ Requirement Ambiguity → Cap Governance
    # --------------------------------------------------

    if ai_insight.get("requirement_ambiguity"):
        governance_score = min(governance_score, 70)

    # --------------------------------------------------
    # 2️⃣ Missing Validation Dimensions → Cap Coverage
    # --------------------------------------------------

    missing_dims = ai_insight.get("missing_validation_dimensions", [])

    if len(missing_dims) >= 2:
        coverage = min(coverage, 75)
    elif len(missing_dims) == 1:
        coverage = min(coverage, 85)

    # --------------------------------------------------
    # Safety Guard
    # --------------------------------------------------

    governance_score = max(min(governance_score, 100), 0)
    coverage = max(min(coverage, 100), 0)

    return round(governance_score, 2), round(coverage, 2)
