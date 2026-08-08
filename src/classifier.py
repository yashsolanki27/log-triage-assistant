"""Log classifier — calls the LLM with the prompts.py template and returns
a structured triage result.

Input: parser output ({raw_text, extracted_error_line})
Output: {category, root_cause_summary, confidence, suggested_action, unclassified_reason}

Confidence <70% -> force category=unclassified, populate unclassified_reason.
No prompt text lives here — see src/prompts.py (patterns.md rule).
"""

import json
import os
import re

from openai import OpenAI

from src.prompts import build_classification_prompt

VALID_CATEGORIES = {
    "next-tache-error",
    "state-transition-block",
    "provisioning-fault",
    "api-integration-error",
    "unclassified",
}

CONFIDENCE_THRESHOLD = 70

_client = None


def _get_client() -> OpenAI:
    global _client
    if _client is None:
        api_key = os.environ.get("OPENCODE_API_KEY") or os.environ.get("OPENAI_API_KEY")
        base_url = os.environ.get("OPENCODE_BASE_URL", "https://opencode.ai/zen/v1")
        if not api_key:
            raise RuntimeError(
                "OPENCODE_API_KEY is not set. Export it or add it to a .env file "
                "before starting the API (see .env.example)."
            )
        _client = OpenAI(api_key=api_key, base_url=base_url)
    return _client


def classify_log(parsed: dict) -> dict:
    """Classify a parsed log entry via the LLM.

    Args:
        parsed: Output of src.parser.parse_log — dict with raw_text,
            extracted_error_line.

    Returns:
        Dict with keys: category, root_cause_summary, confidence,
        suggested_action, unclassified_reason.

    Raises:
        ValueError: If parsed is missing required keys.
        RuntimeError: If the LLM response cannot be parsed as valid JSON.
    """
    if not parsed or not parsed.get("raw_text"):
        raise ValueError("parsed must contain non-empty raw_text")

    prompt = build_classification_prompt(parsed["raw_text"])

    client = _get_client()
    model = os.environ.get("LLM_MODEL_NAME", "deepseek-v4-flash-free")
    response = client.chat.completions.create(
        model=model,
        max_tokens=1000,
        messages=[{"role": "user", "content": prompt}],
    )

    text = response.choices[0].message.content

    result = _parse_llm_json(text)
    return _apply_confidence_rule(result)


def _parse_llm_json(text: str) -> dict:
    """Strip markdown fences if present and parse JSON, with a clear error."""
    cleaned = text.strip()
    cleaned = re.sub(r"^```(?:json)?\s*", "", cleaned)
    cleaned = re.sub(r"\s*```$", "", cleaned)

    try:
        data = json.loads(cleaned)
    except json.JSONDecodeError as exc:
        raise RuntimeError(f"LLM returned non-JSON response: {text!r}") from exc

    required = {"category", "root_cause_summary", "confidence", "suggested_action"}
    missing = required - data.keys()
    if missing:
        raise RuntimeError(f"LLM response missing required fields: {missing}")

    data.setdefault("unclassified_reason", None)
    return data


def _apply_confidence_rule(result: dict) -> dict:
    """Enforce the business rule as a safety net, even if the model didn't.

    <70% confidence must always surface as unclassified with a reason —
    this is not something we trust the model to self-police (patterns.md:
    unclassified is a valid output, never a silently hidden one).
    """
    category = result.get("category")
    confidence = result.get("confidence")

    if category not in VALID_CATEGORIES:
        result["category"] = "unclassified"
        result["unclassified_reason"] = (
            result.get("unclassified_reason")
            or f"Model returned unrecognised category: {category!r}"
        )
        category = "unclassified"

    if isinstance(confidence, (int, float)) and confidence < CONFIDENCE_THRESHOLD:
        if category != "unclassified":
            result["category"] = "unclassified"
        if not result.get("unclassified_reason"):
            result["unclassified_reason"] = (
                f"Confidence {confidence} is below the {CONFIDENCE_THRESHOLD}% threshold."
            )

    if result["category"] != "unclassified":
        result["unclassified_reason"] = None

    return result
