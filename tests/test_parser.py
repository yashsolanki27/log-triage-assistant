"""Tests for src/parser.py — Unit 1 parser."""

import pytest
from src.parser import parse_log, _extract_error_line


# --- Sample logs with known expected extractions ---

LOG_JAVA_EXCEPTION = """\
2024-03-15 10:23:45 ERROR [order-service] - Processing failed
java.lang.NullPointerException: Cannot invoke method getStatus() on null object
    at com.example.OrderProcessor.process(OrderProcessor.java:142)
    at com.example.BatchRunner.run(BatchRunner.java:87)
"""

LOG_API_ERROR = """\
[2024-03-15T10:23:45Z] POST /api/v1/orders 500
Payload: {"orderId": "ORD-12345", "action": "activate"}
Response: {"error": "SoapFaultException: ISAP returned fault", "code": 500}
"""

LOG_PROVISIONING = """\
2024-03-15 10:23:45 INFO  DSLAM-Provisioner - Starting node assignment
2024-03-15 10:23:46 WARN  DSLAM-Provisioner - OLT port 3/0/12 unavailable
2024-03-15 10:23:47 ERROR DSLAM-Provisioner - Failed to assign BNG node for subscriber 88123
"""


# --- Unit 1 tests: parser strips noise, keeps error line ---

def test_parse_java_exception():
    result = parse_log(LOG_JAVA_EXCEPTION)
    assert result["raw_text"].startswith("2024-03-15 10:23:45 ERROR")
    assert "NullPointerException" in result["extracted_error_line"]
    assert result["extracted_error_line"].startswith("java.lang.NullPointerException")
    assert result["is_fallback"] is False


def test_parse_api_error():
    result = parse_log(LOG_API_ERROR)
    assert "SoapFaultException" in result["extracted_error_line"]
    assert result["is_fallback"] is False


def test_parse_provisioning_fault():
    result = parse_log(LOG_PROVISIONING)
    assert "Failed to assign BNG node" in result["extracted_error_line"]
    assert result["is_fallback"] is False


# --- Edge cases ---

def test_empty_log_raises():
    with pytest.raises(ValueError, match="non-empty"):
        parse_log("")


def test_whitespace_only_log_raises():
    with pytest.raises(ValueError, match="non-empty"):
        parse_log("   \n  \t  ")


def test_nul_bytes_raises():
    with pytest.raises(ValueError, match="binary data"):
        parse_log("ERROR something\x00went wrong")


def test_nul_bytes_only_raises():
    with pytest.raises(ValueError, match="binary data"):
        parse_log("\x00\x00\x00")


def test_single_line_log():
    result = parse_log("ERROR something went wrong")
    assert result["extracted_error_line"] == "ERROR something went wrong"
    assert result["raw_text"] == "ERROR something went wrong"
    assert result["is_fallback"] is False


def test_raw_text_is_cleaned():
    result = parse_log("  \n  ERROR test  \n  ")
    assert result["raw_text"] == "ERROR test"


def test_no_error_markers_uses_first_line():
    result = parse_log("line one\nline two\nline three")
    assert result["extracted_error_line"] == "line one"
    assert result["is_fallback"] is True


# --- is_fallback regression tests (tech-debt item 1) ---

def test_parse_returns_is_fallback_false_for_exception():
    """Priority 1 extraction must NOT set is_fallback."""
    result = parse_log("NullPointerException at com.example.Foo:42")
    assert result["is_fallback"] is False


def test_parse_returns_is_fallback_false_for_error_marker():
    """Priority 2 extraction must NOT set is_fallback."""
    result = parse_log("routine startup\nERROR connection refused")
    assert result["is_fallback"] is False


def test_parse_returns_is_fallback_false_for_keyword():
    """Priority 3 extraction must NOT set is_fallback."""
    result = parse_log("node synced\nactivation failed at step 3")
    assert result["is_fallback"] is False


def test_parse_returns_is_fallback_true_when_no_error_line():
    """Priority 4 fallback must set is_fallback=True."""
    result = parse_log("INFO session started\nDEBUG cache hit\nTRACE flushed")
    assert result["extracted_error_line"] == "INFO session started"
    assert result["is_fallback"] is True


# --- _extract_error_line priority tests ---

def test_priority_exception_over_error_marker():
    log = "SomeException thrown\nERROR critical failure here"
    line, fallback = _extract_error_line(log)
    assert line == "SomeException thrown"
    assert fallback is False


def test_priority_exception_over_keyword():
    log = "check the error log\nNullPointerException at line 5"
    line, fallback = _extract_error_line(log)
    assert line == "NullPointerException at line 5"
    assert fallback is False


def test_priority_fatal_marker():
    log = "routine INFO line\nFATAL connection pool exhausted"
    line, fallback = _extract_error_line(log)
    assert line == "FATAL connection pool exhausted"
    assert fallback is False


def test_priority_critical_marker():
    log = "routine INFO line\nCRITICAL disk write failure on /data"
    line, fallback = _extract_error_line(log)
    assert line == "CRITICAL disk write failure on /data"
    assert fallback is False


def test_priority_fatal_over_keyword():
    log = "FATAL node unreachable\ncheck the error log for details"
    line, fallback = _extract_error_line(log)
    assert line == "FATAL node unreachable"
    assert fallback is False


def test_priority_exception_over_fatal():
    log = "FATAL batch aborted\ncom.order.OrderException: sequencing violated"
    line, fallback = _extract_error_line(log)
    assert line == "com.order.OrderException: sequencing violated"
    assert fallback is False
