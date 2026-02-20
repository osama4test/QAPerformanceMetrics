import os
import json
import logging
from openai import OpenAI
from dotenv import load_dotenv

load_dotenv()

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))


def run_ai_review(story_payload: dict) -> dict:
    """
    Calls OpenAI to analyze potential governance / validation blind spots.
    Returns structured JSON insight.
    """

    prompt = f"""
You are a QA Governance Auditor.

Analyze the following user story and test context.

Return ONLY JSON in this format:

{{
  "requirement_ambiguity": true/false,
  "missing_validation_dimensions": ["list of missing types"],
  "governance_penalty_suggestion": integer,
  "coverage_penalty_suggestion": integer,
  "confidence": float (0-1)
}}

Story Data:
{json.dumps(story_payload, indent=2)}
"""

    try:
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {
                    "role": "system",
                    "content": "You are a strict enterprise QA auditor."
                },
                {
                    "role": "user",
                    "content": prompt
                }
            ],
            temperature=0
        )

        content = response.choices[0].message.content

    except Exception as e:
        logging.error(f"[AI API ERROR] {e}")
        return _fallback_response()

    # ==================================================
    # Parse AI Response
    # ==================================================

    try:
        ai_insight = json.loads(content)

        # 🔥 Defensive normalization
        ai_insight = _normalize_ai_response(ai_insight)

        # 🔍 Log structured insight
        logging.info(
            "[AI INSIGHT RAW] "
            f"Ambiguity: {ai_insight.get('requirement_ambiguity')} | "
            f"Missing: {ai_insight.get('missing_validation_dimensions')} | "
            f"Gov Penalty: {ai_insight.get('governance_penalty_suggestion')} | "
            f"Cov Penalty: {ai_insight.get('coverage_penalty_suggestion')} | "
            f"Confidence: {ai_insight.get('confidence')}"
        )

        return ai_insight

    except Exception:
        logging.warning(
            "[AI PARSE ERROR] Could not parse AI response. "
            "Using safe fallback."
        )
        return _fallback_response()


# ======================================================
# Helpers
# ======================================================

def _fallback_response() -> dict:
    """
    Safe fallback if AI fails.
    """
    return {
        "requirement_ambiguity": False,
        "missing_validation_dimensions": [],
        "governance_penalty_suggestion": 0,
        "coverage_penalty_suggestion": 0,
        "confidence": 0
    }


def _normalize_ai_response(ai_insight: dict) -> dict:
    """
    Ensures AI output is safe and bounded.
    Prevents over-penalization or malformed data.
    """

    # Ensure required keys exist
    required_keys = [
        "requirement_ambiguity",
        "missing_validation_dimensions",
        "governance_penalty_suggestion",
        "coverage_penalty_suggestion",
        "confidence"
    ]

    for key in required_keys:
        if key not in ai_insight:
            ai_insight[key] = _fallback_response()[key]

    # Clamp penalties to safe range
    ai_insight["governance_penalty_suggestion"] = max(
        0,
        min(ai_insight.get("governance_penalty_suggestion", 0), 25)
    )

    ai_insight["coverage_penalty_suggestion"] = max(
        0,
        min(ai_insight.get("coverage_penalty_suggestion", 0), 25)
    )

    # Clamp confidence 0–1
    ai_insight["confidence"] = max(
        0.0,
        min(float(ai_insight.get("confidence", 0)), 1.0)
    )

    return ai_insight
