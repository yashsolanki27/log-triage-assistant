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

from dotenv import load_dotenv
from openai import AuthenticationError, OpenAI, RateLimitError

from src.prompts import build_classification_prompt

load_dotenv()

VALID_CATEGORIES = {
    "next-tache-error",
    "state-transition-block",
    "provisioning-fault",
    "api-integration-error",
    "unclassified",
}

CONFIDENCE_THRESHOLD = 70

_client = None
_key_index = 0


def _get_api_keys() -> list[str]:
    """Ordered list of API keys to try.

    OPENCODE_API_KEY may hold a single key or a comma-separated list
    (e.g. "key1,key2,key3") for automatic failover when one key is
    rate-limited or revoked. Falls back to OPENAI_API_KEY if unset.
    """
    raw = os.environ.get("OPENCODE_API_KEY", "").strip()
    keys = [k.strip() for k in raw.split(",") if k.strip()]
    if not keys:
        fallback = os.environ.get("OPENAI_API_KEY", "").strip()
        if fallback:
            keys = [fallback]
    return keys


def _build_client(api_key: str) -> OpenAI:
    base_url = os.environ.get("OPENCODE_BASE_URL", "https://opencode.ai/zen/v1")
    return OpenAI(api_key=api_key, base_url=base_url)


def _get_client() -> OpenAI:
    global _client
    keys = _get_api_keys()
    if not keys:
        raise RuntimeError(
            "OPENCODE_API_KEY is not set. Export it or add it to a .env file "
            "before starting the API (see .env.example)."
        )
    if _client is None:
        _client = _build_client(keys[min(_key_index, len(keys) - 1)])
    return _client


def _rotate_key() -> bool:
    """Advance to the next configured API key.

    Returns True if there is a next key to try, False if every key has
    already been attempted.
    """
    global _client, _key_index
    keys = _get_api_keys()
    if _key_index >= len(keys) - 1:
        return False
    _key_index += 1
    _client = None  # force a client rebuild with the next key
    return True


def _reset_key_index() -> None:
    global _key_index, _client
    if _key_index != 0:
        _key_index = 0
        _client = None


def classify_log(parsed: dict, client: OpenAI | None = None) -> dict:
    """Classify a parsed log entry via the LLM.

    Args:
        parsed: Output of src.parser.parse_log — dict with raw_text,
            extracted_error_line.
        client: Optional OpenAI client to use (used by live tests to inject
            a real client). When omitted, the shared client is used and
            configured keys are rotated on auth/rate-limit failures.

    Returns:
        Dict with keys: category, root_cause_summary, confidence,
        suggested_action, unclassified_reason.

    Raises:
        ValueError: If parsed is missing required keys.
        RuntimeError: If the LLM response cannot be parsed as valid JSON,
            or every configured API key fails.
    """
    if not parsed or not parsed.get("raw_text"):
        raise ValueError("parsed must contain non-empty raw_text")

    prompt = build_classification_prompt(parsed["raw_text"])
    model = os.environ.get("LLM_MODEL_NAME", "deepseek-v4-flash-free")

    last_error = None
    while True:
        openai_client = client if client is not None else _get_client()
        try:
            response = openai_client.chat.completions.create(
                model=model,
                max_tokens=1000,
                messages=[{"role": "user", "content": prompt}],
            )
            text = response.choices[0].message.content
            return _apply_confidence_rule(_parse_llm_json(text))
        except (AuthenticationError, RateLimitError) as exc:
            last_error = exc
            if client is not None:
                raise RuntimeError(f"LLM request failed: {exc}") from exc
            if not _rotate_key():
                break

    _reset_key_index()
    raise RuntimeError(
        f"All configured LLM API keys failed (last error: {last_error})"
    ) from last_error


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

    Guarantees (regardless of what the LLM returned):
      - low confidence (<70) forces category=unclassified
      - the unclassified_reason always explains the below-threshold note
      - category=unclassified always carries a non-empty reason
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
        threshold_note = (
            f"Confidence {confidence} is below the {CONFIDENCE_THRESHOLD}% threshold."
        )
        reason = result.get("unclassified_reason") or ""
        if not reason:
            result["unclassified_reason"] = threshold_note
        elif "below" not in reason.lower():
            result["unclassified_reason"] = f"{threshold_note} {reason}"

    if result["category"] == "unclassified" and not result.get("unclassified_reason"):
        result["unclassified_reason"] = (
            "No taxonomy category confidently matched; flag for human review."
        )

    if result["category"] != "unclassified":
        result["unclassified_reason"] = None

    return result
