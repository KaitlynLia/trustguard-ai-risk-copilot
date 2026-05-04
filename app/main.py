import sys
import json
import pandas as pd
import streamlit as st
from pathlib import Path

root_dir = Path(__file__).resolve().parent.parent

if str(root_dir) not in sys.path:
    sys.path.append(str(root_dir))

from src.vector_store import initialize_vector_store
from src.llm_agent import rag_decision_agent, agentic_decision_system
from src.evaluator import llm_judge, semantic_evaluator, risk_band, threshold_action


st.set_page_config(
    page_title="TrustGuard AI",
    layout="wide"
)

st.title("🛡️ TrustGuard AI: Risk Decision Copilot")
st.caption("Interactive AI decision support system for e-commerce and financial risk review")

case_path = root_dir / "data" / "cases" / "cases.json"

with open(case_path, "r") as f:
    cases = json.load(f)

try:
    initialize_vector_store(reset=False)
except Exception:
    initialize_vector_store(reset=True)


def run_pipeline(case, mode="RAG Agent"):
    if mode == "Agentic Review":
        ai_result = agentic_decision_system(case)
    else:
        ai_result = rag_decision_agent(case)

    judge = llm_judge(case, ai_result)
    sem = semantic_evaluator(case, ai_result)

    return {
        "ai_result": ai_result,
        "judge": judge,
        "semantic": sem
    }


tab1, tab2 = st.tabs(["📊 Batch Evaluation", "🧑‍💼 Interactive Case Review"])


with tab1:
    st.sidebar.header("Batch Demo Settings")

    num_cases = st.sidebar.slider("Number of cases to evaluate", 1, 20, 5)

    selected_domain = st.sidebar.selectbox(
        "Domain filter",
        ["all", "ecommerce", "finance"]
    )

    filtered_cases = cases

    if selected_domain != "all":
        filtered_cases = [c for c in cases if c["domain"] == selected_domain]

    selected_cases = filtered_cases[:num_cases]

    if st.button("Run Batch Evaluation"):
        rows = []

        with st.spinner("Running batch AI decision pipeline..."):
            for case in selected_cases:
                output = run_pipeline(case, mode="RAG Agent")
                ai_result = output["ai_result"]
                judge = output["judge"]
                sem = output["semantic"]

                rows.append({
                    "case_id": case["case_id"],
                    "domain": case["domain"],
                    "ground_truth": case.get("ground_truth_decision"),
                    "ai_decision": ai_result.get("decision"),
                    "risk_score": ai_result.get("risk_score"),
                    "risk_band": risk_band(ai_result.get("risk_score")),
                    "threshold_action": threshold_action(ai_result.get("risk_score")),
                    "judge_score": judge.get("overall_score"),
                    "reasoning_quality": judge.get("reasoning_quality"),
                    "semantic_similarity": sem.get("semantic_similarity")
                })

        st.session_state["eval_df"] = pd.DataFrame(rows)

    if "eval_df" in st.session_state:
        df = st.session_state["eval_df"]

        st.subheader("Business & Evaluation Metrics")

        col1, col2, col3, col4 = st.columns(4)

        with col1:
            st.metric("Cases Evaluated", len(df))

        with col2:
            accuracy = (df["ground_truth"] == df["ai_decision"]).mean()
            st.metric("Decision Accuracy", f"{accuracy:.0%}")

        with col3:
            human_review_rate = (df["threshold_action"] == "human_review_required").mean()
            st.metric("Human Review Rate", f"{human_review_rate:.0%}")

        with col4:
            st.metric("Avg Judge Score", round(df["judge_score"].mean(), 2))

        st.subheader("Evaluation Results")
        st.dataframe(df, use_container_width=True)

        st.subheader("Interpretation")
        st.write(
            "This dashboard evaluates the system beyond simple accuracy by combining "
            "policy-grounded decisioning, LLM-as-Judge scoring, semantic reasoning alignment, "
            "and threshold-based human review routing."
        )


with tab2:
    st.subheader("Interactive Case Review")
    st.write("Enter a new case and let the AI risk copilot recommend an action.")

    col_left, col_right = st.columns([1, 1])

    with col_left:
        domain = st.selectbox("Case Domain", ["ecommerce", "finance"], key="interactive_domain")

        mode = st.radio(
            "Decision Mode",
            ["RAG Agent", "Agentic Review"],
            help="Agentic Review uses draft → critique → refine, but costs more API calls."
        )

        if domain == "ecommerce":
            account_age_days = st.number_input("Account Age (days)", min_value=1, value=45)
            num_past_refunds_60d = st.number_input("Refund Requests in Last 60 Days", min_value=0, value=2)
            item_price = st.number_input("Item Price ($)", min_value=1, value=600)
            delivery_days_ago = st.number_input("Days Since Delivery", min_value=0, value=5)
            evidence_provided = st.checkbox("Evidence Provided", value=False)
            customer_claim = st.text_area(
                "Customer Claim",
                value="The item is defective and I want a refund."
            )

            manual_ground_truth = st.selectbox(
                "Optional Expected Decision for Evaluation",
                ["escalate", "approve", "reject"]
            )

            custom_case = {
                "case_id": "CUSTOM-E",
                "domain": "ecommerce",
                "customer_profile": {
                    "account_age_days": int(account_age_days),
                    "num_past_refunds_60d": int(num_past_refunds_60d),
                },
                "transaction": {
                    "item_price": float(item_price),
                    "delivery_days_ago": int(delivery_days_ago)
                },
                "customer_claim": customer_claim,
                "evidence_provided": bool(evidence_provided),
                "ground_truth_decision": manual_ground_truth
            }

        else:
            account_age_days = st.number_input("Account Age (days)", min_value=1, value=30)
            amount = st.number_input("Transaction Amount ($)", min_value=1, value=5200)
            rapid_transactions = st.checkbox("Rapid Transactions", value=False)
            geo_risk = st.checkbox("Geographic Risk", value=False)
            customer_claim = st.text_area(
                "Transaction Context",
                value="Normal business transfer to vendor."
            )

            manual_ground_truth = st.selectbox(
                "Optional Expected Decision for Evaluation",
                ["escalate", "approve", "reject"]
            )

            custom_case = {
                "case_id": "CUSTOM-F",
                "domain": "finance",
                "customer_profile": {
                    "account_age_days": int(account_age_days)
                },
                "transaction": {
                    "amount": float(amount),
                    "rapid_transactions": bool(rapid_transactions),
                    "geo_risk": bool(geo_risk)
                },
                "customer_claim": customer_claim,
                "ground_truth_decision": manual_ground_truth
            }

        st.markdown("#### Case Preview")
        st.json(custom_case)

        run_custom = st.button("Run AI Case Review", type="primary")

    with col_right:
        if run_custom:
            with st.spinner("Running AI risk analysis..."):
                output = run_pipeline(custom_case, mode=mode)
                ai_result = output["ai_result"]
                judge = output["judge"]
                sem = output["semantic"]

            st.markdown("### AI Decision")

            decision = ai_result.get("decision", "unknown")
            score = ai_result.get("risk_score", 0)

            c1, c2, c3 = st.columns(3)
            c1.metric("Decision", decision.upper())
            c2.metric("Risk Score", score)
            c3.metric("Risk Band", risk_band(score).upper())

            st.progress(min(max(float(score), 0), 1))

            st.markdown("### Recommended Operational Action")
            action = threshold_action(score)
            if action == "human_review_required":
                st.warning("Human review required")
            elif action == "secondary_review":
                st.info("Secondary review recommended")
            else:
                st.success("Auto-approve allowed")

            st.markdown("### Reasoning")
            st.write(ai_result.get("reasoning", "No reasoning returned."))

            st.markdown("### Risk Signals")
            st.write(ai_result.get("risk_signals", []))

            st.markdown("### Policy Evidence")
            st.write(ai_result.get("policy_evidence", []))

            if "retrieved_rules" in ai_result:
                with st.expander("Retrieved Policy Rules"):
                    for rule in ai_result["retrieved_rules"]:
                        st.write(rule)

            st.markdown("### Evaluation")
            e1, e2, e3 = st.columns(3)
            e1.metric("LLM Judge Score", judge.get("overall_score"))
            e2.metric("Reasoning Quality", judge.get("reasoning_quality"))
            e3.metric("Semantic Similarity", round(sem.get("semantic_similarity", 0), 3))

            with st.expander("Raw AI Output"):
                st.json(ai_result)

            if mode == "Agentic Review":
                with st.expander("Draft / Critique Details"):
                    st.markdown("#### Draft")
                    st.write(ai_result.get("draft"))
                    st.markdown("#### Critique")
                    st.write(ai_result.get("critique"))