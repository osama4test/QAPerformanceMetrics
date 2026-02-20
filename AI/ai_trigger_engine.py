def should_trigger_ai_review(
    ac_count: int,
    total_required: int,
    validation_strength: float,
    coverage: float,
    governance_score: float
) -> tuple[bool, str | None]:

    # Rule 1: Blind spot
    if total_required == 0 and ac_count > 0:
        return True, "rule_engine_blind_spot"

    # Rule 2: Inflated coverage illusion
    if coverage > 60 and validation_strength == 0:
        return True, "inflated_validation_confidence"

    # Rule 3: Governance contradiction
    if governance_score == 100 and ac_count <= 1:
        return True, "governance_suspicion"

    return False, None
