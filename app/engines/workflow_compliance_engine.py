def evaluate_compliance(
    state: str,
    tests_authored: bool,
    tests_reviewed: bool,
    test_states: list,
    tc_count: int,
    state_history: list,
    review_lifecycle_detected: bool,
    review_toggle_time,
    earliest_test_created_time,
    passed_qa_time
):

    violations = []
    severe_violation = False

    # ==================================================
    # NORMALIZATION
    # ==================================================

    state = (state or "").strip().lower()
    test_states = [(s or "").strip().lower() for s in test_states]
    states = [(s or "").strip().lower() for s in (state_history or [])]

    # ==================================================
    # 🔴 CRITICAL STRUCTURAL (ZERO COVERAGE) RULES
    # ==================================================

    if (
        state == "passed qa"
        and passed_qa_time
        and earliest_test_created_time
        and passed_qa_time < earliest_test_created_time
    ):
        violations.append(
            "Violation - Test Cases Created After Story Was Passed QA"
        )
        severe_violation = True

    if (
        tests_reviewed
        and review_toggle_time
        and earliest_test_created_time
        and review_toggle_time < earliest_test_created_time
    ):
        violations.append(
            "Violation - Review Toggle Enabled Before Test Cases Were Created"
        )
        severe_violation = True

    if tests_authored and tc_count == 0:
        violations.append(
            "Violation - Tests Authored Toggle Enabled But No Test Cases Exist"
        )
        severe_violation = True

    # ==================================================
    # 🟡 TEST GOVERNANCE RULES
    # ==================================================

    if not tests_authored and tc_count > 0:
        violations.append(
            "Violation - Test Cases Exist But Tests Authored Toggle Is OFF"
        )

    if not tests_authored and tc_count > 0:
        if any(s != "design" for s in test_states):
            violations.append(
                "Violation - Test Cases Modified Before Tests Authored Toggle Enabled"
            )

    if tests_authored and not tests_reviewed and tc_count > 0:
        if any(s != "needs review" for s in test_states):
            violations.append(
                "Violation - Tests Authored But Not In 'Needs Review' State"
            )

    # ==================================================
    # 🟡 REVIEW LIFECYCLE DISCIPLINE
    # ==================================================

    if tests_reviewed and tc_count > 0:

        if not review_lifecycle_detected:

            if any(s == "ready" for s in test_states):
                violations.append(
                    "Violation - Test Case Skipped Review Phase (Moved Directly To Ready)"
                )
            else:
                violations.append(
                    "Violation - Review Toggle Enabled Without Any Test Case Entering 'Needs Review' State"
                )
                severe_violation = True

    # ==================================================
    # 🟡 PASSED QA VALIDATION
    # ==================================================

    if state == "passed qa":

        if tc_count == 0:
            violations.append(
                "Violation - Story Passed QA Without Any Test Cases"
            )
            severe_violation = True

        if not tests_authored:
            violations.append(
                "Violation - Story Passed QA Without Tests Authored Toggle Enabled"
            )

        if not tests_reviewed:
            violations.append(
                "Violation - Story Passed QA Without Tests Reviewed Toggle Enabled"
            )

        if any(s == "needs review" for s in test_states):
            violations.append(
                "Violation - Test Case Still In 'Needs Review' At Passed QA"
            )

        if tc_count > 0 and any(s != "ready" for s in test_states):
            violations.append(
                "Violation - Story Passed QA But Not All Test Cases Are In 'Ready' State"
            )

    # ==================================================
    # 🟡 WORKFLOW GOVERNANCE RULES (Refactored Clean)
    # ==================================================

    if states:

        # --------------------------------------------------
        # PASSED QA VALIDATION (Existence + Sequence Layered)
        # --------------------------------------------------
        if state == "passed qa":

            # WF-1: Never entered QA In Progress at all
            if "qa in progress" not in states:
                violations.append(
                    "Violation - QA Skipped 'QA In Progress' State Before Passing"
                )

            else:
                # WF-2: Passed QA did not immediately follow QA execution
                if len(states) >= 2 and states[-2] != "qa in progress":
                    violations.append(
                        "Violation - Passed QA Without Active QA Execution"
                    )

        # --------------------------------------------------
        # WF-3: Rework → QA In Progress (Dev missed RFQA)
        # --------------------------------------------------
        for i in range(len(states) - 1):
            if states[i] == "rework" and states[i + 1] == "qa in progress":
                violations.append(
                    "Violation - Dev Skipped 'Ready For QA' After Rework (QA Had To Start Without Proper Handoff)"
                )

        # --------------------------------------------------
        # WF-4: QA transition validation
        # --------------------------------------------------
        for i in range(len(states) - 1):

            if states[i + 1] == "qa in progress":

                previous_state = states[i]

                # 🔴 TRUE severe case (QA started too early)
                if previous_state in ["design", "merged", "new"]:
                    violations.append(
                        "Violation - QA Started Before Dev Handoff"
                    )
                    severe_violation = True

                # 🟡 Story reopened after passing
                elif previous_state == "passed qa":
                    violations.append(
                        "Violation - Story Reopened After Passed QA"
                    )

                # 🚫 Rework case intentionally NOT handled here
                # (Already handled above to prevent duplication)

    # ==================================================
    # FINAL OUTPUT
    # ==================================================

    if not violations:
        return "Compliant", False

    return " | ".join(violations), severe_violation