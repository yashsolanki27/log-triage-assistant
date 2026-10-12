"""Log parser — extracts error line from raw log text.

Input: raw pasted log text (single entry, possibly multi-line stack/context)
Output: cleaned {raw_text, extracted_error_line, is_fallback} dict

No classification logic here — extraction only.
"""

import re


def parse_log(raw_text: str) -> dict:
    """Parse raw log text and extract the primary error line.

    Args:
        raw_text: Raw pasted log text (single entry, possibly multi-line).
            Must be valid Unicode text (log input is assumed to be UTF-8
            encoded). Input containing NUL bytes (\x00) — a sign of binary
            or garbled data — is rejected.

    Returns:
        Dict with keys: raw_text (cleaned), extracted_error_line, is_fallback.
        ``is_fallback`` is True when no diagnostic error/exception marker was
        found and the extractor fell back to the first non-empty line; callers
        can use this to add a low-confidence hint to the triage result.

    Raises:
        ValueError: If raw_text is empty, contains no content,
            or contains binary data (NUL bytes).
    """
    if not raw_text or not raw_text.strip():
        raise ValueError("raw_text must be non-empty")

    if "\x00" in raw_text:
        raise ValueError("raw_text contains binary data (NUL bytes)")

    cleaned = raw_text.strip()
    error_line, is_fallback = _extract_error_line(cleaned)

    return {
        "raw_text": cleaned,
        "extracted_error_line": error_line,
        "is_fallback": is_fallback,
    }


def _extract_error_line(text: str) -> tuple[str, bool]:
    """Extract the most informative error line from log text.

    Priority order:
    1. Lines containing exception class names (ending in Exception/Error)
    2. Lines with ERROR/FATAL/CRITICAL level markers (uppercase log levels)
    3. Lines with 'error' or 'fail' keywords (case-insensitive)
    4. First non-empty line (fallback — is_fallback=True)

    Returns:
        (line, is_fallback) — is_fallback is True only for Priority 4
        so callers can distinguish a confident extraction from a guess.
    """
    lines = [line.strip() for line in text.splitlines() if line.strip()]

    if not lines:
        return text.strip(), True

    # Priority 1: Exception class names (Java/C# style) — most diagnostic
    for line in lines:
        if re.search(r"\b\w+(Exception|Error)\b", line):
            return line, False

    # Priority 2: ERROR/FATAL/CRITICAL markers (uppercase log levels)
    for line in lines:
        if re.search(r"\b(ERROR|FATAL|CRITICAL)\b", line):
            return line, False

    # Priority 3: error/fail keywords (case-insensitive, less specific)
    for line in lines:
        if re.search(r"\b(error|fail(?:ed|ure)?)\b", line, re.IGNORECASE):
            return line, False

    # Priority 4: fallback to first non-empty line — no diagnostic marker found
    return lines[0], True
