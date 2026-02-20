# ======================================================
# QA Intelligence Performance Engine
# (Governance-Mature + Coverage-Gated + Transparent)
# ======================================================

def calculate_qii(
    coverage,
    scenario_index,
    test_depth,
    governance_score,
    ac_quality_score,
    complexity_score=1.0,
    critical_gap=False
):
    """
    Enterprise QA Intelligence Index (QII)

    Inputs (0–100 scale):
        coverage              → AC weighted coverage %
        scenario_index        → Scenario coverage index %
        test_depth            → Test engineering depth %
        governance_score      → Governance compliance %
        ac_quality_score      → Acceptance Criteria quality %
        complexity_score      → Story complexity multiplier
        critical_gap          → Boolean flag for critical uncovered ACs

    Returns:
        {
            "qii": float,
            "base_score": float,
            "risk_level": str,
            "breakdown": dict
        }
    """

    # --------------------------------------------------
    # Safe Defaults
    # --------------------------------------------------

    coverage = coverage or 0
    scenario_index = scenario_index or 0
    test_depth = test_depth or 0
    governance_score = governance_score or 0
    ac_quality_score = ac_quality_score or 0
    complexity_score = complexity_score or 1.0

    # Clamp to 0–100
    coverage = max(0, min(coverage, 100))
    scenario_index = max(0, min(scenario_index, 100))
    test_depth = max(0, min(test_depth, 100))
    governance_score = max(0, min(governance_score, 100))
    ac_quality_score = max(0, min(ac_quality_score, 100))

    # --------------------------------------------------
    # 🚨 HARD FAILURE RULE
    # If AC exists but coverage = 0 → catastrophic execution failure
    # --------------------------------------------------

    if coverage == 0:
        return {
            "qii": 0,
            "base_score": 0,
            "risk_level": "Critical",
            "breakdown": {
                "Reason": "Zero validation coverage"
            }
        }

    # --------------------------------------------------
    # Balanced Enterprise Weight Model
    # --------------------------------------------------

    weights = {
        "coverage": 0.25,
        "scenario": 0.20,
        "depth": 0.15,
        "governance": 0.15,
        "ac_quality": 0.10
    }

    total_weight = sum(weights.values())

    coverage_contribution = coverage * weights["coverage"]
    scenario_contribution = scenario_index * weights["scenario"]
    depth_contribution = test_depth * weights["depth"]
    governance_contribution = governance_score * weights["governance"]
    ac_quality_contribution = ac_quality_score * weights["ac_quality"]

    weighted_sum = (
        coverage_contribution +
        scenario_contribution +
        depth_contribution +
        governance_contribution +
        ac_quality_contribution
    )

    base_score = weighted_sum / total_weight

    # --------------------------------------------------
    # Critical AC Gap Penalty
    # --------------------------------------------------

    penalty = 0
    if critical_gap:
        penalty = base_score * 0.15
        base_score *= 0.85

    # --------------------------------------------------
    # Complexity Multiplier
    # --------------------------------------------------

    adjusted_score = base_score * complexity_score

    # --------------------------------------------------
    # 🚨 COVERAGE CAP ENFORCEMENT
    # Prevents artificial inflation when coverage is weak
    # --------------------------------------------------

    cap_applied = None

    if coverage < 30:
        cap_applied = 45
    elif coverage < 40:
        cap_applied = 55
    elif coverage < 50:
        cap_applied = 65
    elif coverage < 60:
        cap_applied = 75

    if cap_applied is not None:
        adjusted_score = min(adjusted_score, cap_applied)

    # Final bounded score
    final_score = round(min(adjusted_score, 100), 2)

    # --------------------------------------------------
    # Leadership-Aligned Risk Classification
    # --------------------------------------------------

    if coverage < 40:
        risk_level = "Critical"

    elif coverage < 60:
        risk_level = "High"

    elif critical_gap:
        risk_level = "High"

    elif final_score < 60:
        risk_level = "Medium"

    else:
        risk_level = "Low"

    # --------------------------------------------------
    # Transparent Breakdown (For Dashboard)
    # --------------------------------------------------

    breakdown = {
        "Coverage Contribution": round(coverage_contribution, 2),
        "Scenario Contribution": round(scenario_contribution, 2),
        "Test Depth Contribution": round(depth_contribution, 2),
        "Governance Contribution": round(governance_contribution, 2),
        "AC Quality Contribution": round(ac_quality_contribution, 2),
        "Penalty Applied": round(penalty, 2),
        "Complexity Multiplier": complexity_score,
        "Coverage Cap Applied": cap_applied
    }

    return {
        "qii": final_score,
        "base_score": round(base_score, 2),
        "risk_level": risk_level,
        "breakdown": breakdown
    }
