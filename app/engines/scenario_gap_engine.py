import re
from typing import List, Dict


# ======================================================
# Validation Rule Definitions
# ======================================================

VALIDATION_RULES = {
    "negative_validation": {
        "ac_keywords": ["must not", "should not", "invalid", "error", "required"],
        "test_keywords": ["invalid", "empty", "blank", "null", "error", "reject", "fail"]
    },
    "boundary_validation": {
        "ac_keywords": ["minimum", "maximum", "limit", "range", "length"],
        "test_keywords": ["min", "max", "boundary", "limit", "range"]
    },
    "status_code_validation": {
        "ac_keywords": ["status", "response", "http", "payload"],
        "test_keywords": ["200", "400", "401", "403", "404", "500", "status", "response code"]
    },
    "ui_rendering_validation": {
        "ac_keywords": ["display", "visible", "show", "render"],
        "test_keywords": ["visible", "displayed", "rendered"]
    }
}


# ======================================================
# Normalization Helpers
# ======================================================

def normalize_text(text: str) -> str:
    if not text:
        return ""
    text = text.lower()
    text = re.sub(r"[^a-z0-9\s]", " ", text)
    return text


def contains_keywords(text: str, keywords: List[str]) -> bool:
    """
    Word-boundary aware keyword matching
    Reduces false positives.
    """
    text = normalize_text(text)

    for keyword in keywords:
        pattern = rf"\b{re.escape(keyword)}\b"
        if re.search(pattern, text):
            return True

    return False


# ======================================================
# Suggestion Generator
# ======================================================

def generate_suggestion(validation_type: str, ac_text: str) -> str:

    if validation_type == "negative_validation":
        return f"Add negative test case for AC: '{ac_text}'"

    if validation_type == "boundary_validation":
        return f"Add boundary value test case for AC: '{ac_text}'"

    if validation_type == "status_code_validation":
        return f"Validate expected HTTP status codes for AC: '{ac_text}'"

    if validation_type == "ui_rendering_validation":
        return f"Validate UI visibility/rendering behavior for AC: '{ac_text}'"

    return f"Add validation coverage for AC: '{ac_text}'"


# ======================================================
# AC-Level Validation Analysis
# ======================================================

def analyze_ac_validations(
    ac_text: str,
    test_texts: List[str]
) -> Dict:

    required = []
    covered = []
    missing_details = []

    for rule_name, rule_data in VALIDATION_RULES.items():

        if contains_keywords(ac_text, rule_data["ac_keywords"]):

            required.append(rule_name)

            # Explicit guard for empty test list
            if not test_texts:
                is_covered = False
            else:
                is_covered = any(
                    contains_keywords(test_text, rule_data["test_keywords"])
                    for test_text in test_texts
                )

            if is_covered:
                covered.append(rule_name)
            else:
                missing_details.append({
                    "validation_type": rule_name,
                    "suggestion": generate_suggestion(rule_name, ac_text)
                })

    return {
        "required": required,
        "covered": covered,
        "missing": missing_details
    }


# ======================================================
# Story-Level Gap Detection
# ======================================================

def detect_contextual_gaps(
    ac_list: List[str],
    test_texts: List[str]
) -> Dict:

    total_required = 0
    total_covered = 0
    all_missing = []

    for index, ac in enumerate(ac_list, start=1):

        ac_result = analyze_ac_validations(ac, test_texts)

        required = ac_result["required"]
        covered = ac_result["covered"]
        missing = ac_result["missing"]

        total_required += len(required)
        total_covered += len(covered)

        for m in missing:
            all_missing.append({
                "ac_number": index,
                "ac_text": ac,
                "validation_type": m["validation_type"],
                "suggestion": m["suggestion"]
            })

    scenario_coverage = (
        (total_covered / total_required) * 100
        if total_required > 0 else 100
    )

    critical_gap = len(all_missing) > 0

    return {
        "scenario_coverage": round(scenario_coverage, 2),
        "total_required": total_required,
        "total_covered": total_covered,
        "missing_details": all_missing,
        "critical_gap": critical_gap
    }


# ======================================================
# Leadership-Friendly Summary Output
# ======================================================

def summarize_gaps(gap_data: Dict) -> List[str]:

    summaries = []

    for item in gap_data.get("missing_details", []):
        summaries.append(
            f"AC {item['ac_number']} Missing: "
            f"{item['validation_type']} | "
            f"{item['suggestion']}"
        )

    return summaries