import sys
import logging
import sqlite3
from typing import Dict, Any
from datetime import datetime

# ✅ Correct package imports
from app.core.devops_client import (
    get_story_ids,
    get_work_item,
    get_work_items_batch
)

from app.engines.coverage import (
    extract_ac,
    evaluate_ac_coverage,
    evaluate_ac_quality
)

from app.storage.report import save_report
from app.engines.test_depth_engine import calculate_test_depth
from app.engines.performance_engine import calculate_qa_execution_score
from app.engines.governance_engine import calculate_governance_score
from app.engines.scenario_gap_engine import detect_contextual_gaps
from app.analytics.history_engine import append_history

from app.storage.database import init_db, DB_NAME


# ======================================================
# Configuration
# ======================================================

STRUCTURAL_WEIGHT = 0.7
VALIDATION_WEIGHT = 0.3

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s"
)


# ======================================================
# Sprint Detection
# ======================================================

def detect_sprint_from_story(story: Dict[str, Any]) -> str:
    iteration_path = story.get("fields", {}).get("System.IterationPath", "")
    if not iteration_path:
        return "Unknown_Sprint"
    return iteration_path.split("\\")[-1]


# ======================================================
# Duplicate Run Protection
# ======================================================

def already_ran_today(sprint_name: str) -> bool:
    try:
        conn = sqlite3.connect(DB_NAME)
        cursor = conn.cursor()

        today = datetime.now().date().isoformat()

        cursor.execute("""
            SELECT COUNT(*)
            FROM qa_history
            WHERE sprint = ?
            AND DATE(run_date) = ?
        """, (sprint_name, today))

        count = cursor.fetchone()[0]
        conn.close()

        return count > 0
    except Exception:
        return False


# ======================================================
# Helpers
# ======================================================

def build_test_text(test: Dict[str, Any]) -> str:
    fields = test.get("fields", {})
    return f"""
TITLE: {fields.get("System.Title", "")}
STEPS: {fields.get("Microsoft.VSTS.TCM.Steps", "")}
EXPECTED: {fields.get("Microsoft.VSTS.TCM.ExpectedResult", "")}
"""


def validate_inputs():
    if len(sys.argv) < 2:
        print("Usage: python main.py <QUERY_GUID>")
        sys.exit(1)
    return sys.argv[1]


def save_story_details(rows):
    if not rows:
        return

    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()

    for row in rows:
        cursor.execute("""
            INSERT INTO story_details (
                sprint, story_id, title, qa,
                coverage, scenario_coverage,
                test_depth, governance,
                ac_quality, qa_performance,
                risk, compliance
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(story_id, sprint)
            DO UPDATE SET
                title=excluded.title,
                qa=excluded.qa,
                coverage=excluded.coverage,
                scenario_coverage=excluded.scenario_coverage,
                test_depth=excluded.test_depth,
                governance=excluded.governance,
                ac_quality=excluded.ac_quality,
                qa_performance=excluded.qa_performance,
                risk=excluded.risk,
                compliance=excluded.compliance,
                created_at=CURRENT_TIMESTAMP
        """, (
            row["Sprint"],
            row["Story ID"],
            row["Title"],
            row["QA"],
            row["Coverage %"],
            row["Scenario Coverage %"],
            row["Test Depth Score"],
            row["Governance Score"],
            row["AC Quality Score"],
            row["QA Performance Score"],
            row["Risk"],
            row["Compliance Status"]
        ))

    conn.commit()
    conn.close()


# ======================================================
# Story Processing (UPDATED COMPLIANCE ONLY)
# ======================================================

def process_story(sid: int, sprint_name: str):

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
    state = fields.get("System.State", "")
    tests_authored = fields.get("Custom.TestsAuthored", False)
    tests_reviewed = fields.get("Custom.TestsReviewed", False)

    title = fields.get("System.Title", "")
    ac_text = fields.get("Microsoft.VSTS.Common.AcceptanceCriteria", "")
    ac_list = extract_ac(ac_text)

    test_ids = [
        int(r["url"].split("/")[-1])
        for r in story.get("relations", [])
        if "TestedBy" in r.get("rel", "")
    ]

    tests = get_work_items_batch(test_ids) if test_ids else []
    tc_count = len(tests)

    # Extract test states
    test_states = [
        t.get("fields", {}).get("System.State", "")
        for t in tests
    ]

    # ==================================================
    # AC Quality (unchanged)
    # ==================================================

    ac_quality_score, _ = evaluate_ac_quality(ac_list)

    # ==================================================
    # UPDATED COMPLIANCE RULES
    # ==================================================

    compliance_status = "Compliant"
    severe_violation = False

    # Rule 1: Toggle true but no test cases
    if tests_authored and tc_count == 0:
        compliance_status = "Violation - Toggle On but No Tests"
        severe_violation = True

    # Rule 2: Tests exist but toggle off
    elif not tests_authored and tc_count > 0:
        compliance_status = "Violation - Tests Exist but Toggle Off"

    # Rule 3: If Tests Authored = True → tests must be Needs Review or Ready
    elif tests_authored and any(
        s not in ["Needs Review", "Ready"] for s in test_states
    ):
        compliance_status = "Violation - Invalid Test Case State"

    # Rule 4: If Tests Reviewed = True → all tests must be Ready
    elif tests_reviewed and any(s != "Ready" for s in test_states):
        compliance_status = "Violation - Reviewed But Tests Not Ready"

    # Rule 5: Passed QA strict enforcement
    if state == "Passed QA":
        if not (tests_authored and tests_reviewed and tc_count > 0):
            compliance_status = "Violation - Passed QA Without Proper Test Governance"
            severe_violation = True
        elif any(s != "Ready" for s in test_states):
            compliance_status = "Violation - Passed QA But Tests Not Ready"
            severe_violation = True

    # ==================================================
    # Coverage + Scenario (unchanged)
    # ==================================================

    test_texts = [build_test_text(t) for t in tests]
    combined_test_text = "\n\n".join(test_texts)

    structural_coverage, _ = evaluate_ac_coverage(ac_list, combined_test_text)
    gap_data = detect_contextual_gaps(ac_list, test_texts)
    validation_coverage = gap_data.get("scenario_coverage", 0)

    coverage = round(
        structural_coverage * STRUCTURAL_WEIGHT +
        validation_coverage * VALIDATION_WEIGHT,
        2
    )

    test_depth_score = calculate_test_depth(combined_test_text)

    # ==================================================
    # Governance (unchanged)
    # ==================================================

    gov_data = calculate_governance_score(
        ac_list,
        ac_quality_score,
        tc_count,
        structural_coverage,
        validation_coverage,
        fields
    )

    governance_score = gov_data["governance_score"]

    # ==================================================
    # Execution Score (unchanged)
    # ==================================================

    execution_data = calculate_qa_execution_score(
        coverage,
        validation_coverage,
        test_depth_score
    )

    execution_score = execution_data["execution_score"]
    risk_level = execution_data["risk_level"]

    # ==================================================
    # Severe Violation Handling (unchanged)
    # ==================================================

    if severe_violation:
        coverage = 0
        validation_coverage = 0
        test_depth_score = 0
        execution_score = 0
        risk_level = "Critical"

    # ==================================================
    # Final Output
    # ==================================================

    return {
        "Sprint": sprint_name,
        "Story ID": sid,
        "Title": title,
        "QA": qa,
        "Coverage %": round(coverage, 2),
        "Scenario Coverage %": round(validation_coverage, 2),
        "Test Depth Score": round(test_depth_score, 2),
        "Governance Score": round(governance_score, 2),
        "AC Quality Score": round(ac_quality_score, 2),
        "QA Performance Score": round(execution_score, 2),
        "Risk": risk_level,
        "Compliance Status": compliance_status,
    }


# ======================================================
# SAFE ENTRY FUNCTION (UNCHANGED)
# ======================================================

def run_qa_analysis(query_id: str):

    init_db()

    story_ids = get_story_ids(query_id)
    if not story_ids:
        return {"status": "No Data"}

    first_story = get_work_item(story_ids[0])
    sprint_name = detect_sprint_from_story(first_story)

    if already_ran_today(sprint_name):
        return {
            "status": "Skipped",
            "message": "Already executed today.",
            "sprint": sprint_name
        }

    rows = []

    for sid in story_ids:
        result = process_story(sid, sprint_name)
        if result:
            rows.append(result)

    if not rows:
        return {"status": "No Data"}

    save_report(rows)
    append_history(sprint_name, rows)
    save_story_details(rows)

    return {
        "status": "Success",
        "stories_processed": len(rows),
        "sprint": sprint_name
    }


def main():
    query_id = validate_inputs()
    run_qa_analysis(query_id)


if __name__ == "__main__":
    main()