def build_risk_review_plan(case: dict) -> dict:
    """
    Build a lightweight tool-calling style workflow plan.

    This is not a fully autonomous agent. It is a deterministic planner that
    selects review tools based on case attributes, risk indicators, and domain.
    """

    domain = case.get("domain", "unknown")
    transaction = case.get("transaction", {})
    customer_profile = case.get("customer_profile", {})

    tools = [
        {
            "tool": "parse_case_input",
            "reason": "Read structured customer profile, transaction details, and claim context."
        },
        {
            "tool": "retrieve_policy_context",
            "reason": "Fetch relevant policy rules from the ChromaDB vector store before decisioning."
        },
        {
            "tool": "run_llm_decision_agent",
            "reason": "Generate structured decision, risk score, risk signals, policy evidence, and reasoning."
        },
        {
            "tool": "calibrate_risk_band",
            "reason": "Map risk score into low, medium, or high risk band."
        },
        {
            "tool": "save_audit_memory",
            "reason": "Persist AI decision, retrieved evidence, latency, and reviewer feedback for traceability."
        }
    ]

    alert_reasons = []

    if domain == "finance":
        amount = transaction.get("amount", 0)
        rapid_transactions = transaction.get("rapid_transactions", False)
        geo_risk = transaction.get("geo_risk", False)
        account_age_days = customer_profile.get("account_age_days", 9999)

        if amount >= 5000:
            alert_reasons.append("high-value financial transaction")
        if rapid_transactions:
            alert_reasons.append("rapid transaction pattern")
        if geo_risk:
            alert_reasons.append("geographic risk indicator")
        if account_age_days <= 30:
            alert_reasons.append("new account risk")

    elif domain == "ecommerce":
        item_price = transaction.get("item_price", 0)
        delivery_days_ago = transaction.get("delivery_days_ago", 0)
        evidence_provided = case.get("evidence_provided", True)
        num_past_refunds = customer_profile.get("num_past_refunds_60d", 0)
        account_age_days = customer_profile.get("account_age_days", 9999)

        if item_price >= 300:
            alert_reasons.append("high-value refund request")
        if not evidence_provided:
            alert_reasons.append("missing or weak evidence")
        if num_past_refunds >= 3:
            alert_reasons.append("frequent recent refund behavior")
        if account_age_days <= 30:
            alert_reasons.append("new account risk")
        if delivery_days_ago > 30:
            alert_reasons.append("outside standard return window")

    needs_proactive_alert = len(alert_reasons) > 0
    needs_human_review = len(alert_reasons) >= 2

    if needs_proactive_alert:
        tools.append(
            {
                "tool": "generate_proactive_alert",
                "reason": "Surface elevated risk indicators before the reviewer makes a final decision."
            }
        )

    if needs_human_review:
        tools.append(
            {
                "tool": "request_human_review",
                "reason": "Route the case to a human reviewer because multiple risk indicators are present."
            }
        )
    else:
        tools.append(
            {
                "tool": "threshold_route_case",
                "reason": "Use the calibrated risk score to determine auto-approve, secondary review, or escalation."
            }
        )

    return {
        "domain": domain,
        "planned_tools": tools,
        "risk_indicators_detected": alert_reasons,
        "needs_proactive_alert": needs_proactive_alert,
        "needs_human_review": needs_human_review
    }