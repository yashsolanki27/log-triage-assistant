"""Single source of truth for all sample logs.

Each entry has:
  - title:     short human-readable label
  - category:  one of the five classifier categories
  - tag:       original error tag from the source system
  - log:       the raw log text to paste into the classifier
"""

# ---------------------------------------------------------------------------
# Category definitions (matches src/classifier.py taxonomy)
# ---------------------------------------------------------------------------
CATEGORIES = {
    "next-tache-error": {
        "label": "Task sequencing",
        "color": "blue",
        "description": "Task started before its prerequisite completed",
    },
    "state-transition-block": {
        "label": "Stuck order",
        "color": "orange",
        "description": "Order or subscriber cannot advance state",
    },
    "provisioning-fault": {
        "label": "Config / node failure",
        "color": "red",
        "description": "Provisioning or configuration rejected",
    },
    "api-integration-error": {
        "label": "API failure",
        "color": "violet",
        "description": "REST or SOAP integration failed",
    },
    "unclassified": {
        "label": "Needs review",
        "color": "gray",
        "description": "Does not match a known pattern",
    },
}

# ---------------------------------------------------------------------------
# All sample logs — merged from Excel + resume-based scenarios
# ---------------------------------------------------------------------------
SAMPLE_LOGS = [
    # =====================================================================
    # next-tache-error  (task sequencing)
    # =====================================================================
    {
        "title": "O2A order skipped prerequisite task",
        "category": "next-tache-error",
        "tag": "next-tache-error",
        "log": (
            "2026-07-11 06:48:00 ERROR [OrderEngine] "
            "Order ORD-79943 Next Tache error: task ACTIVATE_BROADBAND "
            "started before prerequisite VALIDATE_CUST_PROFILE completed. "
            "Tache sequence broken at step 3/7. Order halted in O2A "
            "pipeline. Subscriber: 98XXXXXXXX. Module: BBNW."
        ),
    },
    {
        "title": "O2A order activation skipped prerequisite (variant)",
        "category": "next-tache-error",
        "tag": "next-tache-error",
        "log": (
            "2026-07-12 01:36:00 ERROR [OrderEngine] "
            "Order ORD-37641 Next Tache error: task ACTIVATE_BROADBAND "
            "started before prerequisite VALIDATE_CUST_PROFILE completed. "
            "Tache sequence broken at step 3/7. Order halted in O2A "
            "pipeline. Subscriber: 98XXXXXXXX. Module: BBNW."
        ),
    },

    # =====================================================================
    # state-transition-block  (stuck orders)
    # =====================================================================
    {
        "title": "Collaborative wait timeout on O2A order",
        "category": "state-transition-block",
        "tag": "collab-wait-timeout",
        "log": (
            "2026-07-10 10:43:00 CRITICAL [OrderEngine] "
            "order_id=ORD-79222 collaborative_wait_time=45s exceeded "
            "threshold(30s). Retry triggered automatically. Module: O2A."
        ),
    },
    {
        "title": "Collaborative wait timeout (variant)",
        "category": "state-transition-block",
        "tag": "collab-wait-timeout",
        "log": (
            "2026-07-12 21:28:00 ERROR [OrderEngine] "
            "order_id=ORD-99997 collaborative_wait_time=45s exceeded "
            "threshold(30s). Retry triggered automatically. Module: O2A."
        ),
    },
    {
        "title": "Collaborative wait timeout (critical)",
        "category": "state-transition-block",
        "tag": "collab-wait-timeout",
        "log": (
            "2026-07-13 03:14:00 CRITICAL [OrderEngine] "
            "order_id=ORD-95310 collaborative_wait_time=45s exceeded "
            "threshold(30s). Retry triggered automatically. Module: O2A."
        ),
    },
    {
        "title": "Order refire loop detected in O2A pipeline",
        "category": "state-transition-block",
        "tag": "order-refire-loop",
        "log": (
            "2026-07-11 00:36:00 ERROR [OrderEngine] "
            "order_id=ORD-88042 refire_count=6 exceeded threshold(5). "
            "Loop detected between tasks ACTIVATE and VALIDATE. "
            "Escalated to L3. Module: O2A."
        ),
    },
    {
        "title": "Order refire loop (variant)",
        "category": "state-transition-block",
        "tag": "order-refire-loop",
        "log": (
            "2026-07-11 12:26:00 ERROR [OrderEngine] "
            "order_id=ORD-87224 refire_count=6 exceeded threshold(5). "
            "Loop detected between tasks ACTIVATE and VALIDATE. "
            "Escalated to L3. Module: O2A."
        ),
    },
    {
        "title": "Order refire loop (warn)",
        "category": "state-transition-block",
        "tag": "order-refire-loop",
        "log": (
            "2026-07-11 23:32:00 WARN [OrderEngine] "
            "order_id=ORD-63592 refire_count=6 exceeded threshold(5). "
            "Loop detected between tasks ACTIVATE and VALIDATE. "
            "Escalated to L3. Module: O2A."
        ),
    },
    {
        "title": "Masterless order blocking CRM-to-OSS sync",
        "category": "state-transition-block",
        "tag": "masterless-order",
        "log": (
            "2026-07-12 07:15:00 CRITICAL [CRM-OSS-Bridge] "
            "Order ORD-43288 masterless conflict detected. "
            "CRM state=ACTIVE, OSS state=PENDING. State transition "
            "blocked at handshake. Retry queue depth=14. Module: O2A."
        ),
    },
    {
        "title": "Masterless order conflict (variant)",
        "category": "state-transition-block",
        "tag": "masterless-order",
        "log": (
            "2026-07-13 13:39:00 ERROR [CRM-OSS-Bridge] "
            "Order ORD-25072 masterless conflict detected. "
            "CRM state=ACTIVE, OSS state=PENDING. State transition "
            "blocked at handshake. Retry queue depth=14. Module: O2A."
        ),
    },

    # =====================================================================
    # provisioning-fault  (config / node failures)
    # =====================================================================
    {
        "title": "DSLAM firmware mismatch blocking activation",
        "category": "provisioning-fault",
        "tag": "firmware-mismatch",
        "log": (
            "2026-07-10 11:50:00 CRITICAL [OFM-NodeConfig] "
            "node_id=DSLAM-44402 expected_fw=v4.2 actual_fw=v4.0. "
            "Provisioning rejected: schema incompatibility. "
            "Region: Pune. Module: OFM."
        ),
    },
    {
        "title": "DSLAM firmware mismatch (variant 1)",
        "category": "provisioning-fault",
        "tag": "firmware-mismatch",
        "log": (
            "2026-07-11 16:45:00 ERROR [OFM-NodeConfig] "
            "node_id=DSLAM-81602 expected_fw=v4.2 actual_fw=v4.0. "
            "Provisioning rejected: schema incompatibility. "
            "Region: Pune. Module: OFM."
        ),
    },
    {
        "title": "DSLAM firmware mismatch (variant 2)",
        "category": "provisioning-fault",
        "tag": "firmware-mismatch",
        "log": (
            "2026-07-12 09:29:00 ERROR [OFM-NodeConfig] "
            "node_id=DSLAM-37166 expected_fw=v4.2 actual_fw=v4.0. "
            "Provisioning rejected: schema incompatibility. "
            "Region: Pune. Module: OFM."
        ),
    },
    {
        "title": "DSLAM firmware mismatch (critical)",
        "category": "provisioning-fault",
        "tag": "firmware-mismatch",
        "log": (
            "2026-07-12 19:32:00 CRITICAL [OFM-NodeConfig] "
            "node_id=DSLAM-98907 expected_fw=v4.2 actual_fw=v4.0. "
            "Provisioning rejected: schema incompatibility. "
            "Region: Pune. Module: OFM."
        ),
    },
    {
        "title": "Null spatial parameter blocking provisioning",
        "category": "provisioning-fault",
        "tag": "null-spatial-param",
        "log": (
            "2026-07-10 14:04:00 WARN [OrderEngine] "
            "service_instance_id=SVC-38585 spatial_parameter=NULL. "
            "Provisioning check failed at geo-validation step. "
            "Node assignment blocked. Module: FTTH."
        ),
    },
    {
        "title": "Null spatial parameter (variant 1)",
        "category": "provisioning-fault",
        "tag": "null-spatial-param",
        "log": (
            "2026-07-11 14:55:00 ERROR [OrderEngine] "
            "service_instance_id=SVC-58129 spatial_parameter=NULL. "
            "Provisioning check failed at geo-validation step. "
            "Node assignment blocked. Module: FTTH."
        ),
    },
    {
        "title": "Null spatial parameter (variant 2)",
        "category": "provisioning-fault",
        "tag": "null-spatial-param",
        "log": (
            "2026-07-12 20:02:00 ERROR [OrderEngine] "
            "service_instance_id=SVC-47950 spatial_parameter=NULL. "
            "Provisioning check failed at geo-validation step. "
            "Node assignment blocked. Module: FTTH."
        ),
    },

    # =====================================================================
    # api-integration-error  (REST / SOAP / sync failures)
    # =====================================================================
    {
        "title": "Malformed SOAP envelope at ISAP gateway",
        "category": "api-integration-error",
        "tag": "malformed-soap-envelope",
        "log": (
            "2026-07-10 18:56:00 ERROR [ISAP-Gateway] "
            "SOAP envelope missing namespace declaration. Payload "
            "rejected at schema validation. ticket_ref=TCK-21966. "
            "Module: ISAP."
        ),
    },
    {
        "title": "Malformed SOAP envelope (variant)",
        "category": "api-integration-error",
        "tag": "malformed-soap-envelope",
        "log": (
            "2026-07-11 15:32:00 ERROR [ISAP-Gateway] "
            "SOAP envelope missing namespace declaration. Payload "
            "rejected at schema validation. ticket_ref=TCK-20071. "
            "Module: ISAP."
        ),
    },
    {
        "title": "Malformed SOAP envelope (critical)",
        "category": "api-integration-error",
        "tag": "malformed-soap-envelope",
        "log": (
            "2026-07-11 20:06:00 CRITICAL [ISAP-Gateway] "
            "SOAP envelope missing namespace declaration. Payload "
            "rejected at schema validation. ticket_ref=TCK-75022. "
            "Module: ISAP."
        ),
    },
    {
        "title": "Malformed SOAP (variant 2)",
        "category": "api-integration-error",
        "tag": "malformed-soap-envelope",
        "log": (
            "2026-07-12 14:40:00 ERROR [ISAP-Gateway] "
            "SOAP envelope missing namespace declaration. Payload "
            "rejected at schema validation. ticket_ref=TCK-20061. "
            "Module: ISAP."
        ),
    },
    {
        "title": "SOAP interface timeout at ISAP gateway",
        "category": "api-integration-error",
        "tag": "soap-timeout",
        "log": (
            "2026-07-13 09:59:00 ERROR [ISAP-Gateway] "
            "SOAP request to OFM_Portal timed out after 30000ms. "
            "endpoint=/provision/v2. Retry_count=3. Payload size=4.2KB. "
            "Module: ISAP."
        ),
    },
    {
        "title": "MySQL query timeout on service instance table",
        "category": "api-integration-error",
        "tag": "db-timeout",
        "log": (
            "2026-07-10 16:41:00 ERROR [ServiceDB] "
            "Query timeout after 30000ms on table service_instance. "
            "Rows_affected=0. service_instance_id=SVC-98045. "
            "Connection pool exhausted (48/50 active). Module: DSCM."
        ),
    },
    {
        "title": "MySQL query timeout (variant 1)",
        "category": "api-integration-error",
        "tag": "db-timeout",
        "log": (
            "2026-07-10 19:31:00 ERROR [ServiceDB] "
            "Query timeout after 30000ms on table service_instance. "
            "Rows_affected=0. service_instance_id=SVC-44930. "
            "Connection pool exhausted (48/50 active). Module: DSCM."
        ),
    },
    {
        "title": "MySQL query timeout (variant 2)",
        "category": "api-integration-error",
        "tag": "db-timeout",
        "log": (
            "2026-07-11 22:50:00 ERROR [ServiceDB] "
            "Query timeout after 30000ms on table service_instance. "
            "Rows_affected=0. service_instance_id=SVC-55360. "
            "Connection pool exhausted (48/50 active). Module: DSCM."
        ),
    },
    {
        "title": "MySQL query timeout (variant 3)",
        "category": "api-integration-error",
        "tag": "db-timeout",
        "log": (
            "2026-07-13 01:59:00 ERROR [ServiceDB] "
            "Query timeout after 30000ms on table service_instance. "
            "Rows_affected=0. service_instance_id=SVC-47359. "
            "Connection pool exhausted (48/50 active). Module: DSCM."
        ),
    },
    {
        "title": "Azure AD sync token expired",
        "category": "api-integration-error",
        "tag": "ad-sync-token-expired",
        "log": (
            "2026-07-10 22:24:00 ERROR [AzureADSync] "
            "user_id=y.solanki@fgs.nl token expired at sync cycle "
            "#80808. retry_count=3. Group sync halted for 142 "
            "downstream objects. Module: M365."
        ),
    },
    {
        "title": "Azure AD sync token expired (variant)",
        "category": "api-integration-error",
        "tag": "ad-sync-token-expired",
        "log": (
            "2026-07-11 03:39:00 WARN [AzureADSync] "
            "user_id=y.solanki@fgs.nl token expired at sync cycle "
            "#85506. retry_count=3. Group sync halted for 142 "
            "downstream objects. Module: M365."
        ),
    },
    {
        "title": "Azure AD sync token expired (variant 2)",
        "category": "api-integration-error",
        "tag": "ad-sync-token-expired",
        "log": (
            "2026-07-12 04:56:00 ERROR [AzureADSync] "
            "user_id=y.solanki@fgs.nl token expired at sync cycle "
            "#21435. retry_count=3. Group sync halted for 142 "
            "downstream objects. Module: M365."
        ),
    },
    {
        "title": "Azure AD sync token expired (warn)",
        "category": "api-integration-error",
        "tag": "ad-sync-token-expired",
        "log": (
            "2026-07-13 02:22:00 WARN [AzureADSync] "
            "user_id=y.solanki@fgs.nl token expired at sync cycle "
            "#68719. retry_count=3. Group sync halted for 142 "
            "downstream objects. Module: M365."
        ),
    },
    {
        "title": "MFA enrollment failed — session token expired",
        "category": "api-integration-error",
        "tag": "mfa-session-expired",
        "log": (
            "2026-07-11 12:53:00 ERROR [AzureADSync] "
            "user_id=USR-93812 MFA enrollment failed. "
            "reason=session_token_expired. Retry window closed after "
            "300s. Module: MFA."
        ),
    },
    {
        "title": "MFA enrollment failed (variant)",
        "category": "api-integration-error",
        "tag": "mfa-session-expired",
        "log": (
            "2026-07-13 06:30:00 ERROR [AzureADSync] "
            "user_id=USR-44877 MFA enrollment failed. "
            "reason=session_token_expired. Retry window closed after "
            "300s. Module: MFA."
        ),
    },
    {
        "title": "Cross-vendor payload schema mismatch",
        "category": "api-integration-error",
        "tag": "payload-schema-mismatch",
        "log": (
            "2026-07-11 08:52:00 ERROR [ProductCatalog] "
            "vendor=Huawei expected_schema=v3 received_schema=v2. "
            "Activation rejected at CPQ validation gate. "
            "order_id=ORD-53291. Module: CPQ."
        ),
    },
    {
        "title": "Cross-vendor payload schema mismatch (warn)",
        "category": "api-integration-error",
        "tag": "payload-schema-mismatch",
        "log": (
            "2026-07-12 18:25:00 WARN [ProductCatalog] "
            "vendor=Huawei expected_schema=v3 received_schema=v2. "
            "Activation rejected at CPQ validation gate. "
            "order_id=ORD-22573. Module: CPQ."
        ),
    },
    {
        "title": "Cross-vendor payload schema mismatch (critical)",
        "category": "api-integration-error",
        "tag": "payload-schema-mismatch",
        "log": (
            "2026-07-13 15:00:00 CRITICAL [ProductCatalog] "
            "vendor=Huawei expected_schema=v3 received_schema=v2. "
            "Activation rejected at CPQ validation gate. "
            "order_id=ORD-53683. Module: CPQ."
        ),
    },

    # =====================================================================
    # unclassified  (misc / needs review)
    # =====================================================================
    {
        "title": "M365 license pool exhausted",
        "category": "unclassified",
        "tag": "license-pool-exhausted",
        "log": (
            "2026-07-12 12:33:00 CRITICAL [M365-LicenseSync] "
            "sku=E3 available=0 requested_by=USR-35270. License "
            "assignment queued, sync delayed 40min. Module: M365."
        ),
    },
    {
        "title": "M365 license pool exhausted (variant)",
        "category": "unclassified",
        "tag": "license-pool-exhausted",
        "log": (
            "2026-07-13 18:50:00 CRITICAL [M365-LicenseSync] "
            "sku=E3 available=0 requested_by=USR-58461. License "
            "assignment queued, sync delayed 40min. Module: M365."
        ),
    },
    {
        "title": "Duplicate RBAC profile detected",
        "category": "unclassified",
        "tag": "duplicate-profile",
        "log": (
            "2026-07-13 05:12:00 ERROR [AccessManager] "
            "user_id=USR-40202 has 2 active profiles with conflicting "
            "RBAC roles. Login session conflict raised. "
            "Region: South Zone. Module: RBAC."
        ),
    },
    {
        "title": "Azure AD group sync partial failure",
        "category": "unclassified",
        "tag": "group-sync-partial-fail",
        "log": (
            "2026-07-13 12:53:00 ERROR [AzureADSync] "
            "groups_synced=140/142. 2 groups failed: "
            "reason=object_not_found. batch_id=BATCH-75241. "
            "Module: Azure AD."
        ),
    },
]
