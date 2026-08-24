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
from openai import OpenAI, OpenAIError

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

    Checks GROQ_API_KEY, OPENCODE_API_KEY, and OPENAI_API_KEY in order.
    Each variable may hold a single key or a comma-separated list
    (e.g. "key1,key2,key3") for automatic failover when one key is
    rate-limited or revoked.
    """
    for env_var in ("GROQ_API_KEY", "OPENCODE_API_KEY", "OPENAI_API_KEY"):
        raw = os.environ.get(env_var, "").strip()
        keys = [k.strip() for k in raw.split(",") if k.strip()]
        if keys:
            return keys
    return []


def _get_base_url(api_key: str = "") -> str:
    """Determine the base URL for the LLM client based on the active key / provider."""
    if api_key.startswith("gsk_") or (os.environ.get("GROQ_API_KEY") and not api_key.startswith("sk-")):
        return os.environ.get("GROQ_BASE_URL", "").strip() or "https://api.groq.com/openai/v1"

    if os.environ.get("OPENCODE_BASE_URL", "").strip():
        return os.environ["OPENCODE_BASE_URL"].strip()

    if os.environ.get("OPENAI_BASE_URL", "").strip():
        return os.environ["OPENAI_BASE_URL"].strip()

    return "https://opencode.ai/zen/v1"


def _get_default_model(base_url: str) -> str:
    """Determine the default model name based on configured model or base URL."""
    if "groq.com" in base_url:
        groq_model = os.environ.get("GROQ_MODEL_NAME", "").strip()
        if groq_model:
            return groq_model
        configured = os.environ.get("LLM_MODEL_NAME", "").strip()
        if configured and any(name in configured.lower() for name in ("gpt-oss", "qwen", "llama", "mixtral", "gemma", "deepseek-r1")):
            return configured
        return "openai/gpt-oss-120b"

    if os.environ.get("LLM_MODEL_NAME"):
        return os.environ["LLM_MODEL_NAME"].strip()

    return "deepseek-v4-flash-free"


def _build_client(api_key: str) -> OpenAI:
    base_url = _get_base_url(api_key)
    timeout = float(os.environ.get("LLM_TIMEOUT", "30.0"))
    return OpenAI(api_key=api_key, base_url=base_url, timeout=timeout)


def _get_client() -> OpenAI:
    global _client
    keys = _get_api_keys()
    if not keys:
        raise RuntimeError(
            "No LLM API key configured. Set GROQ_API_KEY (or OPENCODE_API_KEY / "
            "OPENAI_API_KEY) in your environment or .env file (see .env.example)."
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
            configured keys are rotated on auth/rate-limit/API failures.

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

    last_error = None
    while True:
        openai_client = client if client is not None else _get_client()
        base_url = str(getattr(openai_client, "base_url", ""))
        model = _get_default_model(base_url)
        try:
            kwargs = {
                "model": model,
                "max_tokens": 1000,
                "messages": [{"role": "user", "content": prompt}],
            }
            if "groq.com" in base_url or "openai.com" in base_url:
                kwargs["response_format"] = {"type": "json_object"}

            response = openai_client.chat.completions.create(**kwargs)
            text = response.choices[0].message.content
            return _apply_confidence_rule(_parse_llm_json(text), parsed.get("raw_text", ""))
        except OpenAIError as exc:
            last_error = exc
            if client is not None:
                raise RuntimeError(f"LLM request failed: {exc}") from exc
            if not _rotate_key():
                break

    _reset_key_index()
    raise RuntimeError(
        f"All configured LLM API keys failed (last error: {last_error})"
    ) from last_error


def _generate_sop_command(category: str, raw_text: str = "") -> str | None:
    """Generate an actionable standard operating procedure (SOP) command."""
    if category == "unclassified":
        return None

    # Extract common telecom identifiers if present
    order_match = re.search(r"\b(ORD-\d+)\b", raw_text, re.IGNORECASE)
    order_id = order_match.group(1).upper() if order_match else "$ORDER_ID"

    node_match = re.search(r"\b(DSLAM-[A-Za-z0-9_-]+|OLT-[A-Za-z0-9_-]+|BNG-[A-Za-z0-9_-]+|LMG-[A-Za-z0-9_-]+)\b", raw_text, re.IGNORECASE)
    node_id = node_match.group(1).upper() if node_match else "$NODE_ID"

    ticket_match = re.search(r"\b(TCK-\d+|ticket_ref=[A-Za-z0-9_-]+)\b", raw_text, re.IGNORECASE)
    ticket_id = ticket_match.group(1).replace("ticket_ref=", "").upper() if ticket_match else "$TICKET_ID"

    if category == "next-tache-error":
        return f"o2a-engine-cli --order-id {order_id} --reset-tache-sequence --force-prereq-check"
    elif category == "state-transition-block":
        return f"crm-bridge-ctl --resync --order {order_id} --clear-state-lock --reset-wait-timer"
    elif category == "provisioning-fault":
        return f"dslam-provisioner --node {node_id} --sync-firmware --validate-geo-params"
    elif category == "api-integration-error":
        return f"isap-gateway-ctl --flush-connection-pool --replay-payload --ticket {ticket_id}"
    return None


def _parse_llm_json(text: str) -> dict:
    """Strip markdown fences and thinking tags if present and parse JSON."""
    cleaned = text.strip()
    cleaned = re.sub(r"<think>.*?</think>", "", cleaned, flags=re.DOTALL).strip()
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


def _apply_confidence_rule(result: dict, raw_text: str = "") -> dict:
    """Enforce the business rule as a safety net, even if the model didn't.

    <70% confidence must always surface as unclassified with a reason —
    this is not something we trust the model to self-police (patterns.md:
    unclassified is a valid output, never a silently hidden one).

    Returns a NEW dict (patterns.md: functions that return a dict must not
    mutate the one they were given). The input is never modified.

    Guarantees (regardless of what the LLM returned):
      - low confidence (<70) forces category=unclassified
      - the unclassified_reason always explains the below-threshold note
      - category=unclassified always carries a non-empty reason
      - classified categories carry an actionable sop_command
    """
    updated = dict(result)
    category = updated.get("category")
    confidence = updated.get("confidence")

    if category not in VALID_CATEGORIES:
        updated["category"] = "unclassified"
        updated["unclassified_reason"] = (
            updated.get("unclassified_reason")
            or f"Model returned unrecognised category: {category!r}"
        )
        category = "unclassified"

    if isinstance(confidence, (int, float)) and confidence < CONFIDENCE_THRESHOLD:
        if category != "unclassified":
            updated["category"] = "unclassified"
        threshold_note = (
            f"Confidence {confidence} is below the {CONFIDENCE_THRESHOLD}% threshold."
        )
        reason = updated.get("unclassified_reason") or ""
        if not reason:
            updated["unclassified_reason"] = threshold_note
        elif "below" not in reason.lower():
            updated["unclassified_reason"] = f"{threshold_note} {reason}"

    if updated["category"] == "unclassified" and not updated.get("unclassified_reason"):
        updated["unclassified_reason"] = (
            "No taxonomy category confidently matched; flag for human review."
        )

    if updated["category"] != "unclassified":
        updated["unclassified_reason"] = None
        updated["sop_command"] = _generate_sop_command(updated["category"], raw_text)
    else:
        updated["sop_command"] = None

    return updated
