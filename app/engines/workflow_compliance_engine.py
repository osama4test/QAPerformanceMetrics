# app/engines/workflow_compliance_engine.py

def evaluate_compliance(
    state: str,
    tests_authored: bool,
    tests_reviewed: bool,
    test_states: list,
    tc_count: int,
    state_history: list
):

    compliance_status = "Compliant"
    severe_violation = False

    # ==================================================
    # TEST GOVERNANCE RULES (Improved Lifecycle Model)
    # ==================================================

    # Rule 1: Toggle ON but no test cases
    if tests_authored and tc_count == 0:
        return "Violation - Toggle On but No Tests", True

    # Rule 2: Tests exist but toggle OFF
    if not tests_authored and tc_count > 0:
        return "Violation - Tests Exist but Toggle Off", False

    # Rule 3: Before authoring → must remain Design
    if not tests_authored:
        if any(s != "design" for s in test_states):
            return "Violation - Test Cases Modified Before Authoring Toggle", False

    # Rule 4: Authored but NOT reviewed → must be Needs Review
    if tests_authored and not tests_reviewed:
        if any(s != "needs review" for s in test_states):
            return "Violation - Tests Not In Needs Review State", False

    # Rule 5: Reviewed phase (before closure)
    if tests_reviewed and state != "passed qa":

        # Needs Review should no longer exist
        if any(s == "needs review" for s in test_states):
            return "Violation - Test Case Still Pending Review After Review Toggle", False

        # Only Design or Ready allowed
        if any(s not in ["design", "ready"] for s in test_states):
            return "Violation - Invalid Test State After Review", False

    # Rule 6: Passed QA strict enforcement
    if state == "passed qa":

        # Governance structure check
        if not (tests_authored and tests_reviewed and tc_count > 0):
            return "Violation - Passed QA Without Proper Test Governance", True

        # Lifecycle integrity check
        if any(s == "needs review" for s in test_states):
            return "Violation - Test Case Skipped Review Lifecycle", True

        # Final readiness check
        if any(s != "ready" for s in test_states):
            return "Violation - Passed QA But Tests Not Ready", True

    # ==================================================
    # WORKFLOW GOVERNANCE RULES
    # ==================================================

    # Defensive guard: If no history available, skip workflow checks
    if not state_history:
        return compliance_status, severe_violation

    states = state_history  # already lowercase from main.py

    # Rule WF-1: QA must have started
    if "qa in progress" not in states:
        return "Violation - QA Never Started", True

    # Rule WF-2: Passed QA must come from QA In Progress
    if state == "passed qa":
        if len(states) < 2 or states[-2] != "qa in progress":
            return "Violation - Passed QA Without QA In Progress", True

    # Rule WF-3: Rework must go back to Ready For QA
    for i in range(len(states) - 1):
        if states[i] == "rework" and states[i + 1] == "qa in progress":
            return "Violation - Rework Skipped Ready For QA", False

    # Rule WF-4: QA must start after Ready For QA
    for i in range(len(states) - 1):
        if states[i + 1] == "qa in progress" and states[i] != "ready for qa":
            return "Violation - QA Started Without Dev Handoff", True

    return compliance_status, severe_violation