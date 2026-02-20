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

    description = fields.get("System.Description", "")

    if not description:
        return 0

    desc_lower = description.lower()

    # 🔴 Image-only detection
    if "<img" in desc_lower and len(description.strip()) < 200:
        return 30

    # Strip HTML
    clean_text = re.sub(r"<[^>]+>", "", description).strip()

    if not clean_text:
        return 0

    # 🔴 Very short description
    if len(clean_text) < 40:
        return 40

    # 🟡 Medium description
    if len(clean_text) < 120:
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

    if ac_count == 0 or tc_count == 0:
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

    clarity = ac_quality_score

    # 🔴 Penalize single-line AC
    if ac_count == 1 and ac_quality_score < 80:
        clarity = min(clarity, 65)

    return clarity


# ======================================================
# Main Governance Calculator
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

    Returns:
    {
        "governance_score": float,
        "pillars": {
            "clarity": float,
            "validation": float,
            "traceability": float,
            "documentation": float
        }
    }
    """

    ac_count = len(ac_list)

    # --------------------------------------------------
    # Pillar 1: Requirement Clarity
    # --------------------------------------------------

    clarity_score = calculate_clarity_score(ac_list, ac_quality_score)

    # --------------------------------------------------
    # Pillar 2: Validation Completeness
    # --------------------------------------------------

    validation_score = validation_coverage

    # 🔴 If validation strength very low, cap validation pillar
    if validation_score > 80 and structural_coverage < 50:
        validation_score = min(validation_score, 70)

    # --------------------------------------------------
    # Pillar 3: Traceability
    # --------------------------------------------------

    traceability_score = calculate_traceability(ac_count, tc_count)

    # --------------------------------------------------
    # Pillar 4: Documentation Quality
    # --------------------------------------------------

    documentation_score = calculate_documentation_quality(fields)

    # --------------------------------------------------
    # Final Weighted Governance Score
    # --------------------------------------------------

    governance_score = (
        (clarity_score * CLARITY_WEIGHT) +
        (validation_score * VALIDATION_WEIGHT) +
        (traceability_score * TRACEABILITY_WEIGHT) +
        (documentation_score * DOCUMENTATION_WEIGHT)
    )

    governance_score = round(min(governance_score, 100), 2)

    return {
        "governance_score": governance_score,
        "pillars": {
            "clarity": round(clarity_score, 2),
            "validation": round(validation_score, 2),
            "traceability": round(traceability_score, 2),
            "documentation": round(documentation_score, 2)
        }
    }
