import sys
import logging
import sqlite3
from typing import Dict, Any
from datetime import datetime

# ✅ Correct package imports
from app.core.devops_client import (
    get_story_ids,
    get_work_item,
    get_work_items_batch,
    get_work_item_updates
)

from app.engines.coverage import (
    extract_ac,
    evaluate_ac_coverage,
    evaluate_ac_quality
)

from app.engines.workflow_compliance_engine import evaluate_compliance

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


# 🔥 FINAL FIXED VERSION
def extract_state_history(work_item_id: int, current_state: str):
    """
    Extract ordered & normalized state history.
    - Chronological
    - Lowercase
    - No duplicate consecutive states
    """
    try:
        updates = get_work_item_updates(work_item_id)

        # Sort oldest first
        updates = sorted(updates, key=lambda x: x.get("id", 0))

        states = []

        for update in updates:
            fields = update.get("fields", {})
            state_change = fields.get("System.State")
            if state_change and "newValue" in state_change:
                normalized = state_change["newValue"].strip().lower()
                states.append(normalized)

        # Normalize current state
        current_normalized = current_state.strip().lower()

        if not states or states[-1] != current_normalized:
            states.append(current_normalized)

        # Remove consecutive duplicates
        cleaned = []
        for s in states:
            if not cleaned or cleaned[-1] != s:
                cleaned.append(s)

        return cleaned

    except Exception as e:
        logging.warning(f"Failed to extract state history for {work_item_id}: {e}")
        return [current_state.strip().lower()]


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
# Story Processing
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

    # Normalize story state
    state = fields.get("System.State", "").strip().lower()

    tests_authored = fields.get("Custom.TestsAuthored", False)
    tests_reviewed = fields.get("Custom.TestsReviewed", False)

    title = fields.get("System.Title", "")
    ac_text = fields.get("Microsoft.VSTS.Common.AcceptanceCriteria", "")
    ac_list = extract_ac(ac_text)

    # =====================================================
    # Capture Only "TestedBy" Test Cases
    # =====================================================

    test_ids = []

    for r in story.get("relations", []):
        rel_type = r.get("rel", "")
        if "TestedBy" in rel_type:
            try:
                work_item_id = int(r["url"].split("/")[-1])
                test_ids.append(work_item_id)
            except:
                pass

    tests = get_work_items_batch(test_ids) if test_ids else []

    # Ensure ONLY Test Case type
    tests = [
        t for t in tests
        if t.get("fields", {}).get("System.WorkItemType", "").strip().lower() == "test case"
    ]

    tc_count = len(tests)

    test_states = [
        t.get("fields", {}).get("System.State", "").strip().lower()
        for t in tests
    ]

    # =====================================================
    # 🔍 Balanced Review Lifecycle + Chronological Detection
    # =====================================================

    review_lifecycle_detected = False
    review_toggle_time = None
    earliest_test_created_time = None
    passed_qa_time = None

    # ------------------------------------------
    # 1️⃣ Capture story update timestamps
    # ------------------------------------------

    try:
        story_updates = get_work_item_updates(sid)

        for update in story_updates:

            fields_changed = update.get("fields", {})
            revised = update.get("revisedDate")

            if not revised:
                continue

            revised_dt = datetime.fromisoformat(
                revised.replace("Z", "+00:00")
            )

            # Capture review toggle time
            review_change = fields_changed.get("Custom.TestsReviewed")
            if review_change and review_change.get("newValue") is True:
                review_toggle_time = revised_dt

            # Capture Passed QA time
            state_change = fields_changed.get("System.State")
            if state_change and state_change.get("newValue"):
                if state_change["newValue"].strip().lower() == "passed qa":
                    passed_qa_time = revised_dt

    except Exception:
        pass

    # ------------------------------------------
    # 2️⃣ Capture test lifecycle + creation times
    # ------------------------------------------

    if tc_count > 0:

        for t in tests:

            # Capture earliest test creation time
            created_str = t.get("fields", {}).get("System.CreatedDate")

            if created_str:
                created_dt = datetime.fromisoformat(
                    created_str.replace("Z", "+00:00")
                )

                if (
                    earliest_test_created_time is None
                    or created_dt < earliest_test_created_time
                ):
                    earliest_test_created_time = created_dt

            test_id = t.get("id")

            try:
                updates = get_work_item_updates(test_id)

                for update in updates:
                    fields_update = update.get("fields", {})
                    state_change = fields_update.get("System.State")

                    if state_change and "newValue" in state_change:
                        if (
                            state_change["newValue"]
                            .strip()
                            .lower() == "needs review"
                        ):
                            review_lifecycle_detected = True

            except Exception:
                continue

    # =====================================================
    # Workflow State History (Story Level)
    # =====================================================

    state_history = extract_state_history(sid, state)

    # =====================================================
    # Compliance Engine (Updated Signature)
    # =====================================================

    compliance_status, severe_violation = evaluate_compliance(
        state,
        tests_authored,
        tests_reviewed,
        test_states,
        tc_count,
        state_history,
        review_lifecycle_detected,
        review_toggle_time,
        earliest_test_created_time,
        passed_qa_time
    )

    # =====================================================
    # Coverage & Scenario Mapping
    # =====================================================

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

    # =====================================================
    # Governance Score
    # =====================================================

    ac_quality_score, _ = evaluate_ac_quality(ac_list)

    gov_data = calculate_governance_score(
        ac_list,
        ac_quality_score,
        tc_count,
        structural_coverage,
        validation_coverage,
        fields
    )

    governance_score = gov_data["governance_score"]

    # =====================================================
    # QA Execution Score
    # =====================================================

    execution_data = calculate_qa_execution_score(
        coverage,
        validation_coverage,
        test_depth_score
    )

    execution_score = execution_data["execution_score"]
    risk_level = execution_data["risk_level"]

    # =====================================================
    # Severe Violation Override
    # =====================================================

    if severe_violation:
        coverage = 0
        validation_coverage = 0
        test_depth_score = 0
        execution_score = 0
        risk_level = "Critical"

    # =====================================================
    # Final Output
    # =====================================================

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
def run_qa_analysis(query_id: str, progress_callback=None):

    init_db()

    # 🔹 Initial progress state
    if progress_callback:
        progress_callback(0, 0, 0)

    # =====================================================
    # Fetch Story IDs
    # =====================================================
    story_ids = get_story_ids(query_id)

    if not story_ids:
        if progress_callback:
            progress_callback(100, 0, 0)
        return {"status": "No Data"}

    total = len(story_ids)

    # =====================================================
    # Detect Sprint
    # =====================================================
    first_story = get_work_item(story_ids[0])
    sprint_name = detect_sprint_from_story(first_story)

    # =====================================================
    # Duplicate Run Protection
    # =====================================================
    if already_ran_today(sprint_name):
        if progress_callback:
            progress_callback(100, total, total)
        return {
            "status": "Skipped",
            "message": "Already executed today.",
            "sprint": sprint_name
        }

    rows = []

    # =====================================================
    # Process Stories with Real Progress
    # =====================================================
    for index, sid in enumerate(story_ids, start=1):

        result = process_story(sid, sprint_name)
        if result:
            rows.append(result)

        # 🔥 Real-time progress update
        if progress_callback:
            percent = int((index / total) * 100)
            progress_callback(percent, index, total)

    # =====================================================
    # No Valid Rows Case
    # =====================================================
    if not rows:
        if progress_callback:
            progress_callback(100, total, total)
        return {"status": "No Data"}

    # =====================================================
    # Save Results
    # =====================================================
    save_report(rows)
    append_history(sprint_name, rows)
    save_story_details(rows)

    # 🔹 Ensure final 100%
    if progress_callback:
        progress_callback(100, total, total)

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