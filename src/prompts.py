"""Classification prompt template for log triage.

All LLM prompts live here — never inline in classifier.py (patterns.md rule).
References: docs/business-logic.md taxonomy.
"""

CLASSIFICATION_PROMPT = """\
You are an OSS/BSS log triage engine. Analyse the log excerpt below and classify it.

## Root Cause Taxonomy (docs/business-logic.md)

1. next-tache-error — backend calc exception in order processing
   Signals: NullPointerException, ArithmeticException, CalculationException in order/billing code
   Example: "java.lang.ArithmeticException: / by zero in billing calc"

2. state-transition-block — CRM-to-OSS handoff stuck (masterless order, collab-wait failure)
   Signals: Masterless order, collab-wait timeout, state machine halted, WorkflowEngine
   Example: "Masterless order detected: order ORD-456 missing required state transition"

3. provisioning-fault — DSLAM/LMG/BNG/OLT node assignment failure
   Signals: DSLAM, LMG, BNG, OLT, node assignment failed, port unavailable
   Example: "DSLAM-Provisioner: Failed to assign BNG node for subscriber 88123"

4. api-integration-error — REST/SOAP payload mismatch at interface layer (ISAP/OFM style)
   Signals: SoapFaultException, HTTP 4xx/5xx, ISAP/OFM fault, payload mismatch
   Example: "SoapFaultException: ISAP returned fault for request activateOrder"

5. unclassified — none of the above confidently match; flag for human review, never force-fit
   Use when: no error signals present, or error doesn't match any category above

## Rules

- Output exactly one category from the list above.
- Provide a confidence score 0-100.
- If confidence < 70%, set category to "unclassified" and explain why in unclassified_reason.
- Summarise the root cause in <= 2 sentences.
- Suggest one concrete next action.

## Log Excerpt

{log_text}

## Required JSON Output

Return ONLY valid JSON matching this schema:
{{
  "category": "<one of the taxonomy categories>",
  "root_cause_summary": "<1-2 sentence summary>",
  "confidence": <integer 0-100>,
  "suggested_action": "<next step>",
  "unclassified_reason": "<null if classified, else explain>"
}}
"""


def build_classification_prompt(log_text: str) -> str:
    """Render the classification prompt with the given log text."""
    if not log_text or not log_text.strip():
        raise ValueError("log_text must be non-empty")
    return CLASSIFICATION_PROMPT.format(log_text=log_text.strip())
