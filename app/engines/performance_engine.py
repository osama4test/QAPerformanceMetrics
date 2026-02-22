# ======================================================
# QA Execution Performance Engine
# (QA-Controlled + Clean + Accountable)
# ======================================================

def _to_number(value):
    try:
        return float(value)
    except (TypeError, ValueError):
        return 0.0


def _clamp(value):
    return max(0.0, min(value, 100.0))


def calculate_qa_execution_score(
    coverage,
    scenario_index,
    test_depth
):
    """
    QA Execution Score (0–100)

    Measures only QA-controlled dimensions:

        coverage        → Requirement validation strength %
        scenario_index  → Scenario validation completeness %
        test_depth      → Test engineering rigor %

    Formula:
        (Coverage × 0.6)
        + (Scenario Index × 0.25)
        + (Test Depth × 0.15)

    Returns:
        {
            "execution_score": float,
            "risk_level": str
        }
    """

    # --------------------------------------------------
    # Safe Numeric Conversion
    # --------------------------------------------------

    coverage = _clamp(_to_number(coverage))
    scenario_index = _clamp(_to_number(scenario_index))
    test_depth = _clamp(_to_number(test_depth))

    # --------------------------------------------------
    # 🚨 HARD FAILURE RULE
    # If coverage = 0 → catastrophic execution failure
    # --------------------------------------------------

    if coverage == 0:
        return {
            "execution_score": 0.0,
            "risk_level": "Critical"
        }

    # --------------------------------------------------
    # QA Execution Formula
    # --------------------------------------------------

    execution_score = (
        (coverage * 0.6) +
        (scenario_index * 0.25) +
        (test_depth * 0.15)
    )

    execution_score = round(_clamp(execution_score), 2)

    # --------------------------------------------------
    # Risk Classification (Execution-Focused)
    # --------------------------------------------------

    if coverage < 40:
        risk_level = "Critical"
    elif coverage < 60:
        risk_level = "High"
    elif execution_score < 60:
        risk_level = "Medium"
    else:
        risk_level = "Low"

    return {
        "execution_score": execution_score,
        "risk_level": risk_level
    }