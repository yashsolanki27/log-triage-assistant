# Business Logic — Root Cause Taxonomy

## Categories

### 1. `next-tache-error`

Backend calculation exception in order processing. A task in the O2A
order pipeline either started before its prerequisite completed (a broken
"tache"/task sequence) or threw a compute-level exception inside the order
engine (price engine, billing calc, etc.) rather than at an integration
boundary.

**Signal keywords:** `Next Tache error`, `Tache sequence broken`,
`started before prerequisite`, `task`, `prerequisite`, `OrderEngine`,
`O2A pipeline`, `CalculationException`, `ArithmeticException`,
`NullPointerException` (in an order/billing context).

**Distinguishing features:**
- Module is `OrderEngine` / O2A — the failure is *inside* order processing,
  not when calling an external system.
- Explicit task sequencing language: `task X started before prerequisite Y
  completed`, `Tache sequence broken at step N/M`, `Order halted in O2A
  pipeline`.
- Compute exceptions in order code (`/ by zero`, invalid billing calc).

**Example log lines:**
```
ERROR [OrderEngine] Order ORD-79943 Next Tache error: task ACTIVATE_BROADBAND started before prerequisite VALIDATE_CUST_PROFILE completed. Tache sequence broken at step 3/7.
java.lang.NullPointerException: Cannot invoke method getStatus() on null object
java.lang.ArithmeticException: / by zero in billing calc
OrderCalculationException: PriceEngine threw RuntimeException during batch
```

---

### 2. `state-transition-block`

CRM-to-OSS handoff stuck. The order/subscriber cannot advance through its
state machine — a masterless order (CRM and OSS disagree on state), a
collaboration-wait timeout between systems, a refire/retry loop, or an order
stuck in one state with no valid transition.

**Signal keywords:** `collaborative_wait_time`, `exceeded threshold`,
`refire_count`, `retry triggered`, `masterless`, `CRM state=`,
`OSS state=`, `state transition blocked`, `stuck in state`,
`No valid transition found`, `CollaborationWaitFailure`, `WorkflowEngine`.

**Distinguishing features:**
- Module is `OrderEngine`, `CRM-OSS-Bridge`, or `WorkflowEngine`.
- A timeout counter or loop counter exceeded its threshold
  (`collaborative_wait_time=45s exceeded threshold(30s)`,
  `refire_count=6 exceeded threshold(5)`).
- State mismatch across the CRM/OSS boundary (`CRM state=ACTIVE,
  OSS state=PENDING`).
- Not a calculation failure and not an external API payload problem.

**Example log lines:**
```
CRITICAL [OrderEngine] order_id=ORD-79222 collaborative_wait_time=45s exceeded threshold(30s). Retry triggered automatically. Module: O2A.
ERROR [OrderEngine] order_id=ORD-88042 refire_count=6 exceeded threshold(5). Loop detected between tasks ACTIVATE and VALIDATE.
CRITICAL [CRM-OSS-Bridge] Order ORD-43288 masterless conflict detected. CRM state=ACTIVE, OSS state=PENDING. State transition blocked at handshake.
WARN [WorkflowEngine] Order ORD-82301 stuck in state PARTIAL_COMPLETED for 36h. No valid transition found for event PROVISION_OK.
```

---

### 3. `provisioning-fault`

DSLAM/LMG/BNG/OLT node assignment failure. The service cannot be provisioned
because the target network element rejects the request — a firmware/schema
mismatch on the node, a missing parameter (e.g. spatial/geo data) blocking
assignment, or a configuration gate rejecting the activation.

**Signal keywords:** `DSLAM`, `LMG`, `BNG`, `OLT`, `node_id=`,
`expected_fw`, `actual_fw`, `Provisioning rejected`, `schema incompatibility`,
`spatial_parameter`, `geo-validation`, `Node assignment blocked`,
`OFM-NodeConfig`, `port unavailable`.

**Distinguishing features:**
- Module is `OFM-NodeConfig`, `OrderEngine` (provisioning step), or
  references FTTH/BBNW node config.
- References specific network hardware/firmware
  (`node_id=DSLAM-44402 expected_fw=v4.2 actual_fw=v4.0`).
- A required parameter is null/missing and blocks geo/node assignment
  (`spatial_parameter=NULL`, `Provisioning check failed at geo-validation`).
- Failure is at the network provisioning layer, not in business logic and
  not at a REST/SOAP integration boundary.

**Example log lines:**
```
CRITICAL [OFM-NodeConfig] node_id=DSLAM-44402 expected_fw=v4.2 actual_fw=v4.0. Provisioning rejected: schema incompatibility. Module: OFM.
WARN [OrderEngine] service_instance_id=SVC-38585 spatial_parameter=NULL. Provisioning check failed at geo-validation step. Node assignment blocked. Module: FTTH.
DSLAM-Provisioner: Failed to assign BNG node for subscriber 88123
```

---

### 4. `api-integration-error`

REST/SOAP payload mismatch at the interface layer. The failure originates in a
call to an external system — ISAP/OFM gateway, DB/service pool, Azure AD sync —
where the payload is malformed, the schema version mismatches, a token is
expired, or the external call times out.

**Signal keywords:** `SOAP envelope`, `namespace declaration`,
`Payload rejected`, `schema validation`, `ISAP-Gateway`, `SoapFaultException`,
`timed out`, `Query timeout`, `Connection pool exhausted`, `token expired`,
`sync cycle`, `expected_schema`, `received_schema`, `MFA enrollment`,
`endpoint=`.

**Distinguishing features:**
- Module is an integration/gateway name: `ISAP-Gateway`, `ServiceDB`,
  `AzureADSync`, `ProductCatalog`/CPQ.
- Explicit interface-layer language: SOAP/REST faults, schema validation,
  `expected_schema vs received_schema`, payload/namespace errors.
- External-timeout counters (`Query timeout after 30000ms`, `SOAP request
  timed out`, `retry_count=`).
- Not a node-assignment failure (that is provisioning-fault) and not an
  in-pipeline order-processing error (that is next-tache-error).

**Example log lines:**
```
ERROR [ISAP-Gateway] SOAP envelope missing namespace declaration. Payload rejected at schema validation. ticket_ref=TCK-21966. Module: ISAP.
ERROR [ServiceDB] Query timeout after 30000ms on table service_instance. Connection pool exhausted (48/50 active). Module: DSCM.
ERROR [AzureADSync] user_id=y.solanki@fgs.nl token expired at sync cycle #80808. retry_count=3. Module: M365.
ERROR [ProductCatalog] vendor=Huawei expected_schema=v3 received_schema=v2. Activation rejected at CPQ validation gate. Module: CPQ.
```

---

### 5. `unclassified`

None of the above categories confidently match. Flag for human review — never
force-fit.

**When to use:**
- Log contains no error signals (informational messages, successful
  operations, health pings, routine maintenance).
- An error/warning exists but does not match any category's signal keywords
  or distinguishing features (e.g. license-pool exhaustion, RBAC profile
  conflicts, backup warnings).
- Confidence score would be below 70%.

**Example log lines:**
```
INFO [LoadBalancer] Health ping received from node lb-01, response 2ms. Backend pool at 61% capacity. Nothing actionable.
WARN [BackupAgent] nightly backup of NMS database completed with 3 warnings: 2 tables checkpointed slowly, 1 index rebuilt. No action required.
CRITICAL [M365-LicenseSync] sku=E3 available=0 requested_by=USR-35270. License assignment queued, sync delayed 40min.
ERROR [AccessManager] user_id=USR-40202 has 2 active profiles with conflicting RBAC roles. Login session conflict raised.
```

---

## Decision flowchart

```
Log entry
  ├─ Contains error/exception/warning?
  │   ├─ NO (informational/health/success) → unclassified
  │   └─ YES ↓
  ├─ Order pipeline task sequencing / order-engine compute exception?
  │   ├─ YES → next-tache-error
  │   └─ NO ↓
  ├─ Order/subscriber stuck in a state, collab-wait, masterless, refire loop?
  │   ├─ YES → state-transition-block
  │   └─ NO ↓
  ├─ Network node assignment rejection (DSLAM/LMG/BNG/OLT firmware/schema/param)?
  │   ├─ YES → provisioning-fault
  │   └─ NO ↓
  ├─ External API/SOAP/DB/AAD sync failure (payload, schema, token, timeout)?
  │   ├─ YES → api-integration-error
  │   └─ NO ↓
  └─ unclassified (no confident match, flag for human review)
```

## unclassified_reason contract

- `unclassified` results MUST always carry a non-empty `unclassified_reason`
  explaining why the log was not assigned a taxonomy category (for human review).
- Every other category MUST carry `unclassified_reason = null`.
- Enforced at the API boundary by a `model_validator` on `TriageResult`
  (src/api.py), not just at the classifier layer — the contract is
  self-enforcing even if a caller bypasses classification.

## Confidence rule

Model must output confidence score. <70% → category = unclassified, do not guess.

---

## Standard Operating Procedure (SOP) Runbook Commands

For valid classifications, the classifier automatically matches and outputs an actionable enterprise telecom CLI command (`sop_command`), binding extracted entities (`$ORDER_ID`, `$NODE_ID`, `$TICKET_ID`):

| Category | SOP Runbook Command Template | Target System |
| :--- | :--- | :--- |
| `next-tache-error` | `o2a-engine-cli --order-id {order_id} --reset-tache-sequence --force-prereq-check` | OrderEngine O2A Orchestrator |
| `state-transition-block` | `crm-bridge-ctl --resync --order {order_id} --clear-state-lock --reset-wait-timer` | CRM-OSS State Transition Gateway |
| `provisioning-fault` | `dslam-provisioner --node {node_id} --sync-firmware --validate-geo-params` | Network Element Provisioner |
| `api-integration-error` | `isap-gateway-ctl --flush-connection-pool --replay-payload --ticket {ticket_id}` | ISAP / External API Proxy |
| `unclassified` | `null` | N/A (Manual Human Review) |
