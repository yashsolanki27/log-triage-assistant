"""Log parser — extracts error line from raw log text.

Input: raw pasted log text (single entry, possibly multi-line stack/context)
Output: cleaned {raw_text, extracted_error_line} dict

No classification logic here — extraction only.
"""

import re


def parse_log(raw_text: str) -> dict:
    """Parse raw log text and extract the primary error line.

    Args:
        raw_text: Raw pasted log text (single entry, possibly multi-line).

    Returns:
        Dict with keys: raw_text (cleaned), extracted_error_line.

    Raises:
        ValueError: If raw_text is empty or contains no content.
    """
    if not raw_text or not raw_text.strip():
        raise ValueError("raw_text must be non-empty")

    cleaned = raw_text.strip()
    error_line = _extract_error_line(cleaned)

    return {
        "raw_text": cleaned,
        "extracted_error_line": error_line,
    }


def _extract_error_line(text: str) -> str:
    """Extract the most informative error line from log text.

    Priority order:
    1. Lines containing exception class names (ending in Exception/Error)
    2. Lines with ERROR/FATAL/CRITICAL level markers (uppercase log levels)
    3. Lines with 'error' or 'fail' keywords (case-insensitive)
    4. First non-empty line (fallback)
    """
    lines = [line.strip() for line in text.splitlines() if line.strip()]

    if not lines:
        return text.strip()

    # Priority 1: Exception class names (Java/C# style) — most diagnostic
    for line in lines:
        if re.search(r"\b\w+(Exception|Error)\b", line):
            return line

    # Priority 2: ERROR/FATAL/CRITICAL markers (uppercase log levels)
    for line in lines:
        if re.search(r"\b(ERROR|FATAL|CRITICAL)\b", line):
            return line

    # Priority 3: error/fail keywords (case-insensitive, less specific)
    for line in lines:
        if re.search(r"\b(error|fail(?:ed|ure)?)\b", line, re.IGNORECASE):
            return line

    # Priority 4: fallback to first non-empty line
    return lines[0]
