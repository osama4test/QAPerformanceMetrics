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
# Utility
# ======================================================

def clamp(value: float) -> float:
    return max(0, min(value or 0, 100))


# ======================================================
# Recalculate Governance From Pillars
# ======================================================

def recompute_governance_from_pillars(pillars: Dict[str, float]) -> float:
    """
    Recomputes governance score using pillar weights.
    Safe against missing or invalid pillar values.
    """

    clarity = clamp(pillars.get("clarity", 0))
    validation = clamp(pillars.get("validation", 0))
    traceability = clamp(pillars.get("traceability", 0))
    documentation = clamp(pillars.get("documentation", 0))

    governance_score = (
        clarity * CLARITY_WEIGHT +
        validation * VALIDATION_WEIGHT +
        traceability * TRACEABILITY_WEIGHT +
        documentation * DOCUMENTATION_WEIGHT
    )

    return round(clamp(governance_score), 2)


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

    # Safety: Ensure base structure exists
    if not isinstance(base_pillars, dict):
        return {
            "adjusted_pillars": {},
            "adjusted_governance": 0,
            "ai_applied": False
        }

    # Normalize pillars safely
    adjusted = {
        "clarity": clamp(base_pillars.get("clarity", 0)),
        "validation": clamp(base_pillars.get("validation", 0)),
        "traceability": clamp(base_pillars.get("traceability", 0)),
        "documentation": clamp(base_pillars.get("documentation", 0))
    }

    # No AI insight → return base
    if not ai_insight or not isinstance(ai_insight, dict):
        return {
            "adjusted_pillars": adjusted,
            "adjusted_governance": recompute_governance_from_pillars(adjusted),
            "ai_applied": False
        }

    confidence = ai_insight.get("confidence", 0) or 0

    # Confidence gate
    if confidence < AI_CONFIDENCE_THRESHOLD:
        return {
            "adjusted_pillars": adjusted,
            "adjusted_governance": recompute_governance_from_pillars(adjusted),
            "ai_applied": False
        }

    # --------------------------------------------------
    # 1️⃣ Requirement Ambiguity → Cap Clarity
    # --------------------------------------------------

    if ai_insight.get("requirement_ambiguity"):
        adjusted["clarity"] = min(adjusted["clarity"], 60)

    # --------------------------------------------------
    # 2️⃣ Missing Validation Dimensions → Cap Validation
    # --------------------------------------------------

    missing_dims = ai_insight.get("missing_validation_dimensions", []) or []

    if isinstance(missing_dims, list):
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