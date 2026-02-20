# ======================================================
# Governance Pillar Adjustment Model (AI-Aware Layer)
# ======================================================

from typing import Dict, Any


# ======================================================
# Configuration
# ======================================================

AI_CONFIDENCE_THRESHOLD = 0.60

# Pillar weights must match governance_engine.py
CLARITY_WEIGHT = 0.25
VALIDATION_WEIGHT = 0.30
TRACEABILITY_WEIGHT = 0.25
DOCUMENTATION_WEIGHT = 0.20


# ======================================================
# Recalculate Governance From Pillars
# ======================================================

def recompute_governance_from_pillars(pillars: Dict[str, float]) -> float:
    """
    Recomputes governance score using pillar weights.
    """

    governance_score = (
        pillars["clarity"] * CLARITY_WEIGHT +
        pillars["validation"] * VALIDATION_WEIGHT +
        pillars["traceability"] * TRACEABILITY_WEIGHT +
        pillars["documentation"] * DOCUMENTATION_WEIGHT
    )

    return round(min(governance_score, 100), 2)


# ======================================================
# Apply AI Override To Pillars
# ======================================================

def apply_ai_override(
    base_pillars: Dict[str, float],
    ai_insight: Dict[str, Any]
) -> Dict[str, Any]:
    """
    Applies AI audit adjustments to governance pillars.

    AI does NOT subtract arbitrary points.
    It caps pillars based on structural weakness detection.
    """

    if not ai_insight:
        return {
            "adjusted_pillars": base_pillars,
            "adjusted_governance": recompute_governance_from_pillars(base_pillars),
            "ai_applied": False
        }

    confidence = ai_insight.get("confidence", 0)

    # Do not apply AI if confidence too low
    if confidence < AI_CONFIDENCE_THRESHOLD:
        return {
            "adjusted_pillars": base_pillars,
            "adjusted_governance": recompute_governance_from_pillars(base_pillars),
            "ai_applied": False
        }

    adjusted = base_pillars.copy()

    # --------------------------------------------------
    # 1️⃣ Requirement Ambiguity → Cap Clarity
    # --------------------------------------------------

    if ai_insight.get("requirement_ambiguity"):
        adjusted["clarity"] = min(adjusted["clarity"], 60)

    # --------------------------------------------------
    # 2️⃣ Missing Validation Dimensions → Cap Validation
    # --------------------------------------------------

    missing_dims = ai_insight.get("missing_validation_dimensions", [])

    if len(missing_dims) >= 2:
        adjusted["validation"] = min(adjusted["validation"], 65)
    elif len(missing_dims) == 1:
        adjusted["validation"] = min(adjusted["validation"], 75)

    # --------------------------------------------------
    # 3️⃣ Weak Documentation Signal
    # --------------------------------------------------

    if ai_insight.get("requirement_ambiguity") and adjusted["documentation"] == 100:
        adjusted["documentation"] = 70

    # --------------------------------------------------
    # Final Governance Recalculation
    # --------------------------------------------------

    adjusted_governance = recompute_governance_from_pillars(adjusted)

    return {
        "adjusted_pillars": adjusted,
        "adjusted_governance": adjusted_governance,
        "ai_applied": True
    }
