# Business Logic — Root Cause Taxonomy

## Categories

### 1. `next-tache-error`

Backend calculation exception during order processing. The error occurs inside a compute step (price engine, tax calc, billing batch) rather than at an integration boundary.

**Signal keywords:** `NullPointerException`, `ArithmeticException`, `CalculationException`, `OrderCalculationException`, `PriceEngine`, `RuntimeException` in order/billing context.

**Distinguishing features:**
- Stack trace points to internal Java/service code (e.g. `com.example.OrderProcessor`)
- Error is thrown *during* a calculation, not when calling an external system
- Often involves numeric operations (`/ by zero`, `invalid tax rate`)

**Example log lines:**
```
NullPointerException at com.example.OrderProcessor.process(OrderProcessor.java:142)
java.lang.ArithmeticException: / by zero in billing calc
CalculationException: NextTache compute failed for order ORD-789
java.lang.IllegalArgumentException: Invalid tax rate in order processing
OrderCalculationException: PriceEngine threw RuntimeException during batch
```

---

### 2. `state-transition-block`

CRM-to-OSS handoff stuck. The order cannot progress through its state machine — typically a masterless order (no assigned owner) or a collaboration-wait timeout between CRM and provisioning systems.

**Signal keywords:** `Masterless order`, `collab-wait`, `StateTransitionBlock`, `state machine halted`, `PENDING_ACTIVATION`, `WorkflowEngine`, `missing required state transition`.

**Distinguishing features:**
- Order is stuck in a known state (e.g. `PENDING_ACTIVATION`) for an extended period
- References to CRM-to-OSS handoff or workflow orchestration
- Timeout or wait conditions between services, not a calculation failure

**Example log lines:**
```
Masterless order detected: order ORD-456 missing required state transition
CRM-to-OSS handoff stuck: collab-wait timeout for subscriber 99887
StateTransitionBlock: Order stuck in PENDING_ACTIVATION for 48 hours
WorkflowEngine: state machine halted — missing transition from PROVISIONED to ACTIVE
CollaborationWaitFailure: CRM cannot reach provisioning service for order ORD-111
```

---

### 3. `provisioning-fault`

Node assignment failure at the physical/network layer (DSLAM, LMG, BNG, OLT). The service cannot be provisioned because the target network element rejects the request, is unavailable, or has no capacity.

**Signal keywords:** `DSLAM`, `LMG`, `BNG`, `OLT`, `node assignment failed`, `port unavailable`, `capacity exceeded`, `ProvisioningFault`, `PPPoE session`.

**Distinguishing features:**
- References specific network hardware (DSLAM slot, OLT port, BNG node)
- Failure is at the network provisioning layer, not in business logic
- Often includes subscriber ID or port/slot identifiers

**Example log lines:**
```
DSLAM-Provisioner: Failed to assign BNG node for subscriber 88123
OLT port 3/0/12 unavailable — cannot provision VDSL profile
LMG error: node assignment failed for fiber subscriber 55667
ProvisioningFault: DSLAM slot 12 reject — port capacity exceeded
BNG connection timeout for subscriber PPPoE session 44332
```

---

### 4. `api-integration-error`

REST/SOAP payload mismatch at the interface layer. The error originates from a call to an external system (ISAP, OFM, or other OSS/BSS integration) where the request or response is malformed or rejected.

**Signal keywords:** `SoapFaultException`, `REST API error`, `OFM interface error`, `ApiIntegrationError`, `HTTP 502`, `payload mismatch`, `ISAP`, `malformed`.

**Distinguishing features:**
- Error references an external system or API endpoint (ISAP, OFM)
- HTTP status codes (400, 502) or SOAP faults
- Payload structure issues, not calculation or network problems

**Example log lines:**
```
SoapFaultException: ISAP returned fault for request activateOrder
REST API error: POST /api/v1/orders returned 400 — Invalid payload structure
OFM interface error: payload mismatch in order activation request
ApiIntegrationError: SOAP envelope malformed at line 23
HTTP 502 Bad Gateway from downstream ISAP service during order sync
```

---

### 5. `unclassified`

None of the above categories confidently match. Flag for human review — never force-fit.

**When to use:**
- Log contains no error signals (informational messages, successful operations)
- Error exists but does not match any category's signal keywords or patterns
- Confidence score would be below 70%

**Example log lines:**
```
System running normally — no errors detected in last 24 hours
Info: batch job completed successfully with 1500 records processed
Disk usage at 45% — within normal operating parameters
Scheduled maintenance window confirmed for Saturday 02:00-06:00
User login successful from IP 192.168.1.100 at 14:32:11
```

---

## Confidence rule

Model must output confidence score. <70% → category = `unclassified`, do not guess.

## Decision flowchart

```
Log entry
  ├─ Contains error/exception?
  │   ├─ NO → unclassified (informational, no error)
  │   └─ YES ↓
  ├─ References network hardware (DSLAM/LMG/BNG/OLT)?
  │   ├─ YES → provisioning-fault
  │   └─ NO ↓
  ├─ References external API/system (ISAP/OFM, HTTP/SOAP fault)?
  │   ├─ YES → api-integration-error
  │   └─ NO ↓
  ├─ Order stuck in state machine / CRM-to-OSS handoff?
  │   ├─ YES → state-transition-block
  │   └─ NO ↓
  ├─ Calculation/exception in order processing code?
  │   ├─ YES → next-tache-error
  │   └─ NO ↓
  └─ unclassified (no confident match)
```
