# ======================================================
# Governance Compliance Engine (Pillar-Based Model)
# ======================================================

from typing import Dict, List, Any
import re


# ======================================================
# Pillar Weights (Adjustable)
# ======================================================

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
# Helper: Documentation Quality
# ======================================================

def calculate_documentation_quality(fields: Dict[str, Any]) -> float:
    """
    Evaluates if story has meaningful description content.
    Penalizes:
    - Empty description
    - Image-only description
    - Very short description
    Returns 0–100
    """

    description = fields.get("System.Description", "") or ""

    if not description.strip():
        return 0

    desc_lower = description.lower()

    # 🔴 Image-only detection
    if "<img" in desc_lower and len(description.strip()) < 200:
        return 30

    # Strip HTML
    clean_text = re.sub(r"<[^>]+>", "", description).strip()

    if not clean_text:
        return 0

    text_length = len(clean_text)

    if text_length < 40:
        return 40

    if text_length < 120:
        return 70

    return 100


# ======================================================
# Helper: Traceability Score
# ======================================================

def calculate_traceability(ac_count: int, tc_count: int) -> float:
    """
    Measures AC-to-Test linkage quality.
    Returns 0–100
    """

    if ac_count <= 0 or tc_count <= 0:
        return 0

    ratio = tc_count / ac_count

    if ratio >= 1:
        return 100
    elif ratio >= 0.75:
        return 80
    elif ratio >= 0.5:
        return 60
    elif ratio > 0:
        return 40

    return 0


# ======================================================
# Helper: Requirement Clarity
# ======================================================

def calculate_clarity_score(ac_list: List[str], ac_quality_score: float) -> float:
    """
    Determines clarity based on:
    - AC existence
    - AC quality
    - Penalizes single weak AC
    Returns 0–100
    """

    ac_count = len(ac_list)

    if ac_count == 0:
        return 0

    clarity = clamp(ac_quality_score)

    # 🔴 Penalize single weak AC
    if ac_count == 1 and clarity < 80:
        clarity = min(clarity, 65)

    return clarity


# ======================================================
# Main Governance Calculator (UPDATED)
# ======================================================

def calculate_governance_score(
    ac_list: List[str],
    ac_quality_score: float,
    tc_count: int,
    structural_coverage: float,
    validation_coverage: float,
    fields: Dict[str, Any]
) -> Dict[str, Any]:
    """
    Pillar-Based Governance Model (0–100)

    ✔ Excludes Traceability if no test cases exist
    ✔ Redistributes weights proportionally
    ✔ Keeps Validation pillar active (QA accountability)

    Returns:
    {
        "governance_score": float,
        "pillars": {...},
        "weights_used": {...}
    }
    """

    ac_count = len(ac_list)

    structural_coverage = clamp(structural_coverage)
    validation_coverage = clamp(validation_coverage)

    # --------------------------------------------------
    # Pillar 1: Requirement Clarity
    # --------------------------------------------------

    clarity_score = calculate_clarity_score(ac_list, ac_quality_score)

    # --------------------------------------------------
    # Pillar 2: Validation Completeness (QA-controlled)
    # --------------------------------------------------

    validation_score = validation_coverage

    # 🔴 Prevent structural gaming
    if validation_score > 80 and structural_coverage < 50:
        validation_score = min(validation_score, 70)

    validation_score = clamp(validation_score)

    # --------------------------------------------------
    # Pillar 3: Traceability (QA-controlled)
    # --------------------------------------------------

    traceability_score = clamp(
        calculate_traceability(ac_count, tc_count)
    )

    # --------------------------------------------------
    # Pillar 4: Documentation Quality (Story-controlled)
    # --------------------------------------------------

    documentation_score = clamp(
        calculate_documentation_quality(fields)
    )

    # ==================================================
    # Dynamic Weight Adjustment (NEW LOGIC)
    # ==================================================

    if tc_count == 0:
        # 🚨 No test cases linked → Exclude traceability

        total_remaining_weight = (
            CLARITY_WEIGHT +
            VALIDATION_WEIGHT +
            DOCUMENTATION_WEIGHT
        )

        clarity_w = CLARITY_WEIGHT / total_remaining_weight
        validation_w = VALIDATION_WEIGHT / total_remaining_weight
        documentation_w = DOCUMENTATION_WEIGHT / total_remaining_weight

        governance_score = (
            clarity_score * clarity_w +
            validation_score * validation_w +
            documentation_score * documentation_w
        )

        weights_used = {
            "clarity": round(clarity_w, 4),
            "validation": round(validation_w, 4),
            "traceability": 0.0,
            "documentation": round(documentation_w, 4)
        }

    else:
        # ✅ Normal case → Use full 4-pillar model

        governance_score = (
            clarity_score * CLARITY_WEIGHT +
            validation_score * VALIDATION_WEIGHT +
            traceability_score * TRACEABILITY_WEIGHT +
            documentation_score * DOCUMENTATION_WEIGHT
        )

        weights_used = {
            "clarity": CLARITY_WEIGHT,
            "validation": VALIDATION_WEIGHT,
            "traceability": TRACEABILITY_WEIGHT,
            "documentation": DOCUMENTATION_WEIGHT
        }

    governance_score = round(clamp(governance_score), 2)

    return {
        "governance_score": governance_score,
        "pillars": {
            "clarity": round(clarity_score, 2),
            "validation": round(validation_score, 2),
            "traceability": round(traceability_score, 2),
            "documentation": round(documentation_score, 2)
        },
        "weights_used": weights_used
    }