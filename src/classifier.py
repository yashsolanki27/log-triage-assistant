"""Log classifier — calls LLM to classify parsed log errors.

Input: parser output dict with raw_text, extracted_error_line.
Output: {category, root_cause_summary, confidence, suggested_action, unclassified_reason}
Confidence <70% → force category=unclassified, populate unclassified_reason.

Patterns: one function, one responsibility. No silent fallback.
"""

import json
import os

import openai

from src.prompts import build_classification_prompt

VALID_CATEGORIES = [
    "next-tache-error",
    "state-transition-block",
    "provisioning-fault",
    "api-integration-error",
    "unclassified",
]

CONFIDENCE_THRESHOLD = 70
MODEL_NAME = os.environ.get("LLM_MODEL_NAME", "deepseek-v4-flash-free")


def classify_log(parsed_log: dict, client=None) -> dict:
    """Classify a parsed log entry using an LLM call.

    Args:
        parsed_log: Dict from parser.parse_log() with keys raw_text, extracted_error_line.
        client: Optional OpenAI client for testing. If None, uses OPENCODE_API_KEY.

    Returns:
        Dict with keys: category, root_cause_summary, confidence,
        suggested_action, unclassified_reason.

    Raises:
        ValueError: If parsed_log is missing required keys.
        RuntimeError: If LLM call fails or returns unparseable response.
    """
    _validate_input(parsed_log)

    prompt = build_classification_prompt(parsed_log["extracted_error_line"])
    raw_response = _call_llm(prompt, client=client)
    result = _parse_response(raw_response)

    result = _apply_confidence_rule(result)
    _validate_output(result)

    return result


def _validate_input(parsed_log: dict) -> None:
    """Ensure parser output has required keys."""
    missing = [k for k in ("raw_text", "extracted_error_line") if k not in parsed_log]
    if missing:
        raise ValueError(f"parsed_log missing keys: {missing}")


def _call_llm(prompt: str, client=None) -> str:
    """Call the OpenAI-compatible API and return the raw text response.

    Args:
        prompt: The formatted prompt to send.
        client: Optional OpenAI client for testing. If None, creates a new one.
    """
    if client is None:
        api_key = os.environ.get("OPENCODE_API_KEY")
        if not api_key:
            raise RuntimeError("OPENCODE_API_KEY environment variable not set")
        client = openai.OpenAI(
            base_url="https://opencode.ai/zen/v1",
            api_key=api_key,
        )

    message = client.chat.completions.create(
        model=MODEL_NAME,
        max_tokens=512,
        messages=[{"role": "user", "content": prompt}],
    )
    return message.choices[0].message.content


def _parse_response(raw_response: str) -> dict:
    """Extract and validate JSON from the LLM response text."""
    text = raw_response.strip()
    if text.startswith("```"):
        lines = text.splitlines()
        lines = lines[1:]
        if lines and lines[-1].strip() == "```":
            lines = lines[:-1]
        text = "\n".join(lines).strip()
    try:
        result = json.loads(text)
    except json.JSONDecodeError as exc:
        raise RuntimeError(f"LLM returned invalid JSON: {raw_response}") from exc

    required_keys = {
        "category",
        "root_cause_summary",
        "confidence",
        "suggested_action",
        "unclassified_reason",
    }
    missing = required_keys - result.keys()
    if missing:
        raise RuntimeError(f"LLM response missing keys: {missing}")

    return result


def _apply_confidence_rule(result: dict) -> dict:
    """Force unclassified if confidence is below threshold."""
    if result["confidence"] < CONFIDENCE_THRESHOLD:
        result["unclassified_reason"] = (
            f"Confidence {result['confidence']}% is below {CONFIDENCE_THRESHOLD}% threshold. "
            + (result.get("unclassified_reason") or "Low confidence in classification.")
        )
        result["category"] = "unclassified"
    return result


def _validate_output(result: dict) -> None:
    """Ensure final output conforms to expected schema."""
    if result["category"] not in VALID_CATEGORIES:
        raise RuntimeError(f"Invalid category: {result['category']}")

    if not isinstance(result["confidence"], int):
        raise RuntimeError(f"Confidence must be int, got {type(result['confidence'])}")

    if not (0 <= result["confidence"] <= 100):
        raise RuntimeError(f"Confidence must be 0-100, got {result['confidence']}")

    if result["category"] == "unclassified":
        reason = result.get("unclassified_reason")
        if not isinstance(reason, str) or not reason.strip():
            raise RuntimeError(
                "unclassified category requires a non-empty unclassified_reason string"
            )
