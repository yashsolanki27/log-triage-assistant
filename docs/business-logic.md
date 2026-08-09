# Business Logic — Root Cause Taxonomy

## Categories

1. next-tache-error — backend calc exception in order processing
2. state-transition-block — CRM-to-OSS handoff stuck (masterless order, collab-wait failure)
3. provisioning-fault — DSLAM/LMG/BNG/OLT node assignment failure
4. api-integration-error — REST/SOAP payload mismatch at interface layer (ISAP/OFM style)
5. unclassified — none of above confidently match; flag for human review, never force-fit

## unclassified_reason contract

- `unclassified` results MUST always carry a non-empty `unclassified_reason`
  explaining why the log was not assigned a taxonomy category (for human review).
- Every other category MUST carry `unclassified_reason = null`.
- Enforced at the API boundary by a `model_validator` on `TriageResult`
  (src/api.py), not just at the classifier layer — the contract is
  self-enforcing even if a caller bypasses classification.

## Confidence rule

Model must output confidence score. <70% → category = unclassified, do not guess.
