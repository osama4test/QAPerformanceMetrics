import re


# ======================================================
# Test Depth Engine
# ======================================================

def calculate_test_depth(test_text):
    """
    Calculates test depth score based on:

    - Negative scenarios
    - Boundary testing
    - Validation coverage
    - Integration/API testing
    - Data handling
    - Step complexity

    Returns score between 0 and 100.
    """

    if not test_text:
        return 0

    text = test_text.lower()

    # --------------------------------------------------
    # Scenario Categories
    # --------------------------------------------------

    categories = {
        "negative": ["invalid", "error", "fail", "exception", "incorrect"],
        "boundary": ["max", "min", "limit", "boundary", "edge"],
        "empty_null": ["empty", "null", "blank"],
        "validation": ["required", "mandatory", "validation"],
        "integration": ["api", "service", "database", "backend"],
        "data_handling": ["save", "update", "delete", "insert"]
    }

    score = 0
    category_hits = 0

    # --------------------------------------------------
    # Category Diversity Scoring
    # --------------------------------------------------

    for words in categories.values():
        if any(re.search(rf"\b{re.escape(word)}\b", text) for word in words):
            category_hits += 1

    # Each category contributes 15 points
    score += category_hits * 15

    # --------------------------------------------------
    # Step Complexity Scoring
    # --------------------------------------------------

    step_matches = re.findall(r"\bstep\b|\b\d+\.", text)
    step_count = len(step_matches)

    if step_count >= 10:
        score += 20
    elif step_count >= 5:
        score += 10
    elif step_count >= 3:
        score += 5

    # --------------------------------------------------
    # Length Heuristic (very short tests are shallow)
    # --------------------------------------------------

    word_count = len(text.split())

    if word_count < 30:
        score *= 0.6  # shallow test penalty
    elif word_count > 150:
        score += 10  # detailed test bonus

    # --------------------------------------------------
    # Final Cap
    # --------------------------------------------------

    return min(round(score, 2), 100)
