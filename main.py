import sys
import logging
from typing import Dict, Any

from devops_client import (
    get_story_ids,
    get_work_item,
    get_work_items_batch
)

from coverage import (
    extract_ac,
    evaluate_ac_coverage,
    evaluate_ac_quality
)

from report import save_report
from test_depth_engine import calculate_test_depth
from performance_engine import calculate_qii
from governance_engine import calculate_governance_score
from scenario_gap_engine import detect_contextual_gaps
from history_engine import append_history
from trend_engine import calculate_trends

# 🔥 AI Layer
from AI.ai_trigger_engine import should_trigger_ai_review
from AI.ai_review_engine import run_ai_review
from AI.ai_adjustment_engine import apply_ai_adjustments


# ======================================================
# Configuration
# ======================================================

STRUCTURAL_WEIGHT = 0.7
VALIDATION_WEIGHT = 0.3


# ======================================================
# Logging Configuration
# ======================================================

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s"
)


# ======================================================
# Helpers
# ======================================================

def build_test_text(test: Dict[str, Any]) -> str:
    fields = test.get("fields", {})
    title = fields.get("System.Title", "")
    steps = fields.get("Microsoft.VSTS.TCM.Steps", "")
    expected = fields.get("Microsoft.VSTS.TCM.ExpectedResult", "")

    return f"""
TITLE: {title}
STEPS: {steps}
EXPECTED: {expected}
"""


def validate_inputs():
    if len(sys.argv) < 3:
        print("Usage: python main.py <QUERY_GUID> <SPRINT_NAME>")
        sys.exit(1)
    return sys.argv[1], sys.argv[2]


def log_story_summary(
    sid,
    qa,
    coverage,
    validation_strength,
    governance,
    qii,
    risk
):
    separator = "─" * 60

    print(f"\n{separator}")
    print(f"Story ID: {sid} | QA: {qa}")
    print(
        f"Coverage: {coverage:.2f}% | "
        f"Validation Strength: {validation_strength:.2f} | "
        f"Governance: {governance:.2f}"
    )
    print(f"QII: {qii:.2f} | Risk: {risk}")
    print(separator)


# ======================================================
# Structural Coverage
# ======================================================

def evaluate_structural_coverage(ac_list, ac_count, tc_count, test_text):
    structural_coverage = 0
    missing = []
    risk_reason = ""

    if ac_count == 0:
        risk_reason = "No Acceptance Criteria defined."

    elif tc_count == 0:
        risk_reason = "AC exist but no test cases linked."
        missing = list(range(1, ac_count + 1))

    else:
        structural_coverage, ac_results = evaluate_ac_coverage(ac_list, test_text)
        structural_coverage = structural_coverage or 0

        for result in ac_results:
            if result["category"] == "Missing":
                missing.append(result["ac_number"])

        if missing:
            risk_reason = "One or more AC completely uncovered."
        else:
            risk_reason = "AC validation evaluated."

    return structural_coverage, missing, risk_reason


# ======================================================
# Story Processing
# ======================================================

def process_story(sid: int, sprint_name: str) -> Dict[str, Any] | None:

    try:
        story = get_work_item(sid)
    except Exception as e:
        logging.error(f"Failed to fetch story {sid}: {e}")
        return None

    fields = story.get("fields", {})
    qa_obj = fields.get("Custom.TestedBy")

    if not qa_obj:
        return None

    qa = qa_obj.get("displayName") if isinstance(qa_obj, dict) else qa_obj

    title = fields.get("System.Title", "")
    description = fields.get("System.Description", "")
    ac_text = fields.get("Microsoft.VSTS.Common.AcceptanceCriteria", "")

    ac_list = extract_ac(ac_text)
    ac_count = len(ac_list)

    # ==================================================
    # AC Quality
    # ==================================================

    ac_quality_score, _ = evaluate_ac_quality(ac_list)
    ac_quality_score = ac_quality_score or 0

    # ==================================================
    # Linked Test Cases
    # ==================================================

    test_ids = [
        int(r["url"].split("/")[-1])
        for r in story.get("relations", [])
        if "TestedBy" in r.get("rel", "")
    ]

    tests = get_work_items_batch(test_ids) if test_ids else []
    tc_count = len(tests)

    test_texts = [build_test_text(t) for t in tests]
    combined_test_text = "\n\n".join(test_texts)

    # ==================================================
    # Structural Coverage
    # ==================================================

    structural_coverage, missing, risk_reason = evaluate_structural_coverage(
        ac_list, ac_count, tc_count, combined_test_text
    )

    # ==================================================
    # Validation Coverage
    # ==================================================

    gap_data = detect_contextual_gaps(ac_list, test_texts)

    validation_coverage = gap_data.get("scenario_coverage", 0)
    total_required = gap_data.get("total_required", 0)
    critical_scenario_gap = gap_data.get("critical_gap", False)

    # ==================================================
    # Unified Coverage
    # ==================================================

    coverage = (
        structural_coverage * STRUCTURAL_WEIGHT +
        validation_coverage * VALIDATION_WEIGHT
    )

    # ==================================================
    # Validation Strength
    # ==================================================

    validation_strength = calculate_test_depth(combined_test_text) or 0

    # ==================================================
    # Governance (Pillar-Based)
    # ==================================================

    gov_data = calculate_governance_score(
        ac_list=ac_list,
        ac_quality_score=ac_quality_score,
        tc_count=tc_count,
        structural_coverage=structural_coverage,
        validation_coverage=validation_coverage,
        fields=fields
    )

    governance_score = gov_data["governance_score"]

    # ==================================================
    # AI Trigger Layer
    # ==================================================

    trigger_ai, reason = should_trigger_ai_review(
        ac_count=ac_count,
        total_required=total_required,
        validation_strength=validation_strength,
        coverage=coverage,
        governance_score=governance_score
    )

    if trigger_ai:
        logging.warning(f"[AI REVIEW TRIGGERED] Story {sid} | Reason: {reason}")

        story_payload = {
            "title": title,
            "description": description,
            "acceptance_criteria": ac_list,
            "test_cases": test_texts,
            "coverage": coverage,
            "governance": governance_score
        }

        ai_insight = run_ai_review(story_payload)

        governance_score, coverage = apply_ai_adjustments(
            governance_score,
            coverage,
            ai_insight
        )

        logging.warning(
            f"[AI ADJUSTMENT APPLIED] Story {sid} | "
            f"New Governance: {governance_score:.2f} | "
            f"New Coverage: {coverage:.2f}"
        )

    # ==================================================
    # QII Calculation
    # ==================================================

    critical_gap = (
        coverage < 40 or
        critical_scenario_gap or
        len(missing) > 0
    )

    qii_data = calculate_qii(
        coverage=coverage,
        scenario_index=validation_coverage,
        test_depth=validation_strength,
        governance_score=governance_score,
        ac_quality_score=ac_quality_score,
        complexity_score=1.0,
        critical_gap=critical_gap
    )

    qa_performance_score = qii_data["qii"]
    final_risk = qii_data["risk_level"]
    breakdown = qii_data.get("breakdown", {})

    # ==================================================
    # Console Output
    # ==================================================

    log_story_summary(
        sid=sid,
        qa=qa,
        coverage=coverage,
        validation_strength=validation_strength,
        governance=governance_score,
        qii=qa_performance_score,
        risk=final_risk
    )

    # ==================================================
    # RETURN DATA (Dashboard-Compatible)
    # ==================================================

    return {
        "Sprint": sprint_name,
        "Story ID": sid,
        "Title": title,
        "QA": qa,

        "AC Quality Score": round(ac_quality_score, 2),
        "Coverage %": round(coverage, 2),
        "Validation Strength": round(validation_strength, 2),
        "Governance Score": round(governance_score, 2),
        "QA Performance Score": round(qa_performance_score, 2),
        "Risk": final_risk,

        # 🔥 QII Breakdown Restored
        "Coverage Contribution": breakdown.get("Coverage Contribution", 0),
        "Scenario Contribution": breakdown.get("Scenario Contribution", 0),
        "Test Depth Contribution": breakdown.get("Test Depth Contribution", 0),
        "Governance Contribution": breakdown.get("Governance Contribution", 0),
        "AC Quality Contribution": breakdown.get("AC Quality Contribution", 0),
    }


# ======================================================
# Main Execution
# ======================================================

def main():
    query_id, sprint_name = validate_inputs()

    logging.info("Fetching story IDs...")
    story_ids = get_story_ids(query_id)
    logging.info(f"Found {len(story_ids)} stories.")

    rows = []

    for sid in story_ids:
        result = process_story(sid, sprint_name)
        if result:
            rows.append(result)

    if not rows:
        logging.warning("No valid QA stories processed.")
        return

    save_report(rows)
    append_history(sprint_name, rows)

    trend_data = calculate_trends()
    if trend_data:
        print("\n📊 QA Performance Trends:")
        for t in trend_data:
            print(
                f"{t['QA']} | "
                f"Coverage Trend: {t['Coverage Trend']} | "
                f"Volatility: {t['Coverage Volatility']} | "
                f"Flag: {t['Performance Flag']}"
            )

    logging.info("QA Intelligence report generated successfully.")


if __name__ == "__main__":
    main()
