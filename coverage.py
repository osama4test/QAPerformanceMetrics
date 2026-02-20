import re
from typing import List, Tuple, Dict

# ======================================================
# Stopwords (ignore weak words during matching)
# ======================================================

STOPWORDS = {
    "the", "a", "an", "to", "of", "for", "in", "on",
    "and", "or", "is", "are", "be", "should", "must",
    "user", "system", "able", "can", "when", "then",
    "with", "by", "as", "at", "it"
}

# ======================================================
# High-Signal Keywords (Weighted Higher)
# ======================================================

HIGH_SIGNAL_TERMS = {
    "update", "delete", "insert", "sync",
    "due", "date", "trigger", "assign",
    "record", "complete", "error",
    "validation", "manual", "automatic",
    "offline", "api", "endpoint",
    "migration", "script", "schema",
    "metadata", "patch", "get"
}

# ======================================================
# AC Quality Intelligence Dictionaries
# ======================================================

VAGUE_TERMS = {
    "properly", "correctly", "appropriately",
    "works", "working", "handle",
    "efficiently", "successfully",
    "as expected", "accurately"
}

VALIDATION_VERBS = {
    "display", "return", "calculate", "update",
    "delete", "save", "prevent", "allow",
    "restrict", "validate", "trigger",
    "show", "appear", "fetch"
}

# ======================================================
# Scope Exclusion Detection
# ======================================================

SCOPE_EXCLUSION_TERMS = {
    "not covered",
    "out of scope",
    "will be skipped",
    "skipped",
    "planned for next",
    "future ticket",
    "future enhancement",
    "not included"
}

# ======================================================
# Technical / Migration Detection
# ======================================================

TECHNICAL_TERMS = {
    "migration",
    "script",
    "schema",
    "seed",
    "database",
    "backend",
    "stored procedure",
    "job",
    "data setup"
}

# ======================================================
# HTML cleaner
# ======================================================

def clean_html(text: str) -> str:
    return re.sub(r"<.*?>", "", text or "")

# ======================================================
# Extract Acceptance Criteria
# ======================================================

def extract_ac(ac_text: str) -> List[str]:

    if not ac_text:
        return []

    # HTML list
    items = re.findall(
        r"<li[^>]*>(.*?)</li>",
        ac_text,
        re.IGNORECASE | re.DOTALL
    )

    if items:
        return [
            clean_html(x).strip()
            for x in items
            if clean_html(x).strip()
        ]

    # Plain list
    lines = []

    for line in ac_text.split("\n"):
        line = clean_html(line).strip()

        if not line:
            continue

        line = re.sub(r"^\d+\.\s*", "", line)
        line = re.sub(r"^[-*•]\s*", "", line)

        lines.append(line)

    return lines

# ======================================================
# AC Intent Classification
# ======================================================

def classify_ac_intent(ac_text: str) -> str:

    lower_text = ac_text.lower()

    if any(term in lower_text for term in SCOPE_EXCLUSION_TERMS):
        return "Scope Exclusion"

    if any(term in lower_text for term in TECHNICAL_TERMS):
        return "Technical"

    return "Functional"

# ======================================================
# Text normalization
# ======================================================

def normalize_text(text: str) -> str:
    text = text.lower()
    text = re.sub(r"[^a-z0-9\s]", " ", text)
    return text

def tokenize(text: str) -> List[str]:
    words = normalize_text(text).split()
    return [w for w in words if w not in STOPWORDS]

# ======================================================
# Weighted Keyword Overlap
# ======================================================

def weighted_keyword_overlap(ac: str, test_text: str) -> float:

    ac_words = tokenize(ac)
    test_words = set(tokenize(test_text))

    if not ac_words:
        return 0

    total_weight = 0
    matched_weight = 0

    for word in ac_words:

        weight = 2 if word in HIGH_SIGNAL_TERMS else 1
        total_weight += weight

        if word in test_words:
            matched_weight += weight

    return matched_weight / total_weight if total_weight else 0

# ======================================================
# Behavioral Validation Scoring (For Technical AC)
# ======================================================

def behavioral_validation_score(test_text: str) -> float:

    text = test_text.lower()

    signals = {
        "get_api": "get" in text,
        "patch_api": "patch" in text,
        "update": "update" in text,
        "persistence": "reload" in text or "persistence" in text,
        "security": "unauthorized" in text or "forbidden" in text,
        "metadata": "metadata" in text or "column" in text,
        "validation": "validate" in text or "required" in text
    }

    return sum(signals.values()) / len(signals)

# ======================================================
# Coverage Classification
# ======================================================

def classify_score(percent: float) -> str:

    if percent >= 80:
        return "Strong"
    elif percent >= 50:
        return "Moderate"
    elif percent > 0:
        return "Weak"
    else:
        return "Missing"

# ======================================================
# Enterprise Coverage Evaluation
# ======================================================

def evaluate_ac_coverage(
    ac_list: List[str],
    test_text: str
) -> Tuple[float, List[Dict]]:

    if not ac_list:
        return 0, []

    results = []
    total_score = 0
    functional_count = 0

    for i, ac in enumerate(ac_list, 1):

        ac_type = classify_ac_intent(ac)

        # --------------------------------------------------
        # Scope Exclusion → excluded from scoring
        # --------------------------------------------------

        if ac_type == "Scope Exclusion":
            results.append({
                "ac_number": i,
                "score": None,
                "category": "Excluded",
                "type": ac_type,
                "text": ac
            })
            continue

        # --------------------------------------------------
        # Technical AC → behavior-based validation
        # --------------------------------------------------

        if ac_type == "Technical":

            score = behavioral_validation_score(test_text)
            percent = round(score * 100, 2)
            category = classify_score(percent)

            results.append({
                "ac_number": i,
                "score": percent,
                "category": category,
                "type": ac_type,
                "text": ac
            })

            total_score += score
            functional_count += 1
            continue

        # --------------------------------------------------
        # Functional AC → keyword overlap
        # --------------------------------------------------

        functional_count += 1

        score = weighted_keyword_overlap(ac, test_text)
        percent = round(score * 100, 2)
        category = classify_score(percent)

        results.append({
            "ac_number": i,
            "score": percent,
            "category": category,
            "type": ac_type,
            "text": ac
        })

        total_score += score

    if functional_count == 0:
        overall_coverage = 0
    else:
        overall_coverage = round(
            (total_score / functional_count) * 100,
            2
        )

    return overall_coverage, results

# ======================================================
# AC Quality Evaluation
# ======================================================

def evaluate_ac_quality(ac_list: List[str]) -> Tuple[float, List[Dict]]:

    if not ac_list:
        return 0, []

    total_score = 0
    details = []

    for i, ac in enumerate(ac_list, 1):

        ac_type = classify_ac_intent(ac)

        # Scope clarity rewarded
        if ac_type == "Scope Exclusion":
            score = 100
            details.append({
                "ac_number": i,
                "quality_score": score,
                "issues": ["Scope clarity defined (good governance)"],
                "type": ac_type
            })
            total_score += score
            continue

        score = 100
        findings = []

        tokens = tokenize(ac)
        word_count = len(tokens)

        if word_count < 5:
            score -= 20
            findings.append("Too short / possibly non-testable")

        vague_hits = [v for v in VAGUE_TERMS if v in ac.lower()]
        if vague_hits:
            score -= 15
            findings.append(f"Vague wording: {', '.join(vague_hits)}")

        if ac.lower().count(" and ") >= 2:
            score -= 15
            findings.append("Compound AC")

        if not any(v in ac.lower() for v in VALIDATION_VERBS):
            score -= 10
            findings.append("No clear validation verb")

        score = max(score, 0)
        total_score += score

        details.append({
            "ac_number": i,
            "quality_score": score,
            "issues": findings if findings else ["Well-defined"],
            "type": ac_type
        })

    overall_quality = round(total_score / len(ac_list), 2)

    return overall_quality, details

# ======================================================
# Debug Helper
# ======================================================

def get_ac_debug_scores(ac_list: List[str], test_text: str):

    results = []

    for i, ac in enumerate(ac_list, 1):
        score = weighted_keyword_overlap(ac, test_text)
        results.append((i, round(score * 100, 2)))

    return results
