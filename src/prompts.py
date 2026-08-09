"""Classification prompt template for log triage.

All LLM prompts live here — never inline in classifier.py (patterns.md rule).
References: docs/business-logic.md taxonomy.
"""

CLASSIFICATION_PROMPT = """\
You are an OSS/BSS log triage engine. Analyse the log excerpt below and classify it.

## Root Cause Taxonomy (docs/business-logic.md)

1. next-tache-error — backend calc exception in order processing
   Signals: "Next Tache error", "Tache sequence broken", "started before prerequisite", OrderEngine/O2A
   Example: "Order ORD-79943 Next Tache error: task ACTIVATE_BROADBAND started before prerequisite VALIDATE_CUST_PROFILE completed. Tache sequence broken at step 3/7."
2. state-transition-block — CRM-to-OSS handoff stuck (masterless order, collab-wait failure)
   Signals: collaborative_wait_time exceeded threshold, refire_count, masterless, CRM state vs OSS state, stuck in state
   Example: "order_id=ORD-79222 collaborative_wait_time=45s exceeded threshold(30s)"
3. provisioning-fault — DSLAM/LMG/BNG/OLT node assignment failure
   Signals: DSLAM/LMG/BNG/OLT, node_id, expected_fw vs actual_fw, Provisioning rejected, spatial_parameter NULL
   Example: "node_id=DSLAM-44402 expected_fw=v4.2 actual_fw=v4.0. Provisioning rejected: schema incompatibility."
4. api-integration-error — REST/SOAP payload mismatch at interface layer (ISAP/OFM style)
   Signals: SOAP envelope, Payload rejected, schema validation, token expired, Query timeout, expected_schema vs received_schema
   Example: "SOAP envelope missing namespace declaration. Payload rejected at schema validation."
5. unclassified — none of the above confidently match; flag for human review, never force-fit
   Use when: no error signals (informational/health/success), or no category's signals match
   Example: "Health ping received from node lb-01, response 2ms. Backend pool at 61% capacity. Nothing actionable."

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
