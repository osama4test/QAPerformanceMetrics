import re


# ======================================================
# Keyword Dictionaries (Expandable)
# ======================================================

STORY_TYPE_KEYWORDS = {
    "UI": [
        "screen", "button", "display", "view",
        "layout", "form", "page", "dropdown"
    ],
    "API": [
        "api", "endpoint", "request", "response",
        "payload", "status code", "http"
    ],
    "BUSINESS_LOGIC": [
        "update", "calculate", "synchronizer",
        "trigger", "assign", "due date",
        "retest", "alternate", "complete"
    ],
    "DATA": [
        "database", "record", "write",
        "save", "update record", "delete"
    ],
    "PERMISSION": [
        "role", "access", "authorization",
        "permission", "security"
    ],
    "PERFORMANCE": [
        "performance", "load", "speed",
        "response time", "timeout"
    ]
}


# ======================================================
# Helper
# ======================================================

def normalize(text):
    text = text.lower()
    text = re.sub(r"[^a-z0-9\s]", " ", text)
    return text


# ======================================================
# Story Type Classifier
# ======================================================

def classify_story_type(title, description, ac_list):
    """
    Returns the dominant story type.
    """

    combined_text = normalize(
        f"{title} {description} {' '.join(ac_list)}"
    )

    scores = {}

    for story_type, keywords in STORY_TYPE_KEYWORDS.items():
        score = 0
        for kw in keywords:
            if kw in combined_text:
                score += 1
        scores[story_type] = score

    # Choose highest scoring type
    dominant_type = max(scores, key=scores.get)

    # If no match at all → fallback
    if scores[dominant_type] == 0:
        dominant_type = "GENERIC"

    return dominant_type


# ======================================================
# Expected Scenario Generator
# ======================================================

def build_expected_scenarios(story_type):
    """
    Based on story type,
    define what scenario types should exist.
    """

    scenario_map = {

        "UI": [
            "UI rendering validation",
            "Field validation",
            "Negative input validation",
            "Boundary value validation"
        ],

        "API": [
            "Positive API response validation",
            "Negative API response validation",
            "Payload validation",
            "Status code validation"
        ],

        "BUSINESS_LOGIC": [
            "Trigger condition validation",
            "State transition validation",
            "Data integrity validation",
            "Negative logic validation",
            "Edge case validation"
        ],

        "DATA": [
            "Database write validation",
            "Data persistence validation",
            "Rollback validation"
        ],

        "PERMISSION": [
            "Authorized access validation",
            "Unauthorized access validation",
            "Role-based scenario validation"
        ],

        "PERFORMANCE": [
            "Load validation",
            "Timeout validation",
            "Response time validation"
        ],

        "GENERIC": [
            "Positive scenario validation",
            "Negative scenario validation"
        ]
    }

    return scenario_map.get(story_type, [])


# ======================================================
# Main Context Builder
# ======================================================

def build_story_context(title, description, ac_list):
    """
    Returns structured context profile.
    """

    story_type = classify_story_type(
        title,
        description,
        ac_list
    )

    expected_scenarios = build_expected_scenarios(story_type)

    return {
        "story_type": story_type,
        "expected_scenarios": expected_scenarios
    }
