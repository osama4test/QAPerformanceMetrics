import re


# ======================================================
# Test Depth Engine
# ======================================================

def calculate_test_depth(test_text):
    """
    Calculates test depth score based on:

    - Scenario diversity
    - Boundary coverage
    - Validation rigor
    - Integration/API awareness
    - Data handling depth
    - Step complexity
    - Test richness

    Returns score between 0 and 100.
    """

    if not test_text:
        return 0

    text = test_text.lower()

    # --------------------------------------------------
    # Scenario Categories (refined keywords)
    # --------------------------------------------------

    categories = {
        "negative": ["invalid", "error", "fail", "exception", "incorrect"],
        "boundary": ["maximum", "minimum", "boundary", "limit", "range"],
        "empty_null": ["empty", "null", "blank"],
        "validation": ["required", "mandatory", "validation", "validate"],
        "integration": ["api", "endpoint", "service", "database", "backend"],
        "data_handling": ["save", "update", "delete", "insert", "persist"]
    }

    score = 0
    category_hits = 0

    # --------------------------------------------------
    # Category Diversity Scoring
    # --------------------------------------------------

    for words in categories.values():
        if any(re.search(rf"\b{re.escape(word)}\b", text) for word in words):
            category_hits += 1

    # Max category contribution = 75 (not 90)
    score += min(category_hits * 15, 75)

    # --------------------------------------------------
    # Step Complexity Scoring
    # --------------------------------------------------

    step_matches = re.findall(r"\bstep\b|\b\d+\.", text)
    step_count = len(step_matches)

    if step_count >= 10:
        score += 20
    elif step_count >= 6:
        score += 12
    elif step_count >= 3:
        score += 6

    # --------------------------------------------------
    # Length Heuristic
    # --------------------------------------------------

    word_count = len(text.split())

    # Strong shallow penalty
    if word_count < 25:
        score *= 0.5
    elif word_count < 40:
        score *= 0.7
    elif word_count > 200:
        score += 10

    # --------------------------------------------------
    # Final Clamp
    # --------------------------------------------------

    return min(round(score, 2), 100)