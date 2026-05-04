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

    selected_domain = st.sidebar.selectbox(
        "Domain filter",
        ["all", "ecommerce", "finance"]
    )

    filtered_cases = cases
    if selected_domain != "all":
        filtered_cases = [c for c in cases if c["domain"] == selected_domain]

    max_cases = len(filtered_cases)

    if max_cases == 0:
        st.warning("No cases available for the selected domain.")
        selected_cases = []
    else:
        display_max_cases = min(20, max_cases)
        default_cases = min(10, display_max_cases)

        num_cases = st.sidebar.slider(
            "Number of cases to evaluate",
            min_value=1,
            max_value=display_max_cases,
            value=default_cases
        )

        selected_cases = filtered_cases[:num_cases]

        st.caption(
            f"Showing {num_cases} out of {max_cases} available cases. "
            "Batch evaluation is capped at 20 cases to avoid long LLM runtime."
        )

    if st.button("Run Batch Evaluation"):
        rows = []

        with st.spinner("Running batch AI decision pipeline..."):
            for case in selected_cases:
                output = run_pipeline(case, mode="RAG Agent")
                ai_result = output["ai_result"]
                judge = output["judge"]
                sem = output["semantic"]

                risk_score = ai_result.get("risk_score")

                rows.append({
                    "case_id": case["case_id"],
                    "domain": case["domain"],
                    "ground_truth": case.get("ground_truth_decision"),
                    "ai_decision": ai_result.get("decision"),
                    "risk_score": risk_score,
                    "risk_band": risk_band(risk_score),
                    "threshold_action": threshold_action(risk_score),
                    "judge_score": judge.get("overall_score"),
                    "reasoning_quality": judge.get("reasoning_quality"),
                    "semantic_similarity": sem.get("semantic_similarity")
                })

        st.session_state["eval_df"] = pd.DataFrame(rows)

    if "eval_df" in st.session_state:
        df = st.session_state["eval_df"]

        st.subheader("Business & Evaluation Metrics")

        st.caption(
            "Metrics are computed on a curated synthetic benchmark for portfolio demonstration. "
            "Reference-aligned accuracy means the AI decision matches the expected case label; "
            "it should not be interpreted as production-level model accuracy."
        )

        col1, col2, col3, col4 = st.columns(4)

        with col1:
            st.metric("Cases Evaluated", len(df))

        with col2:
            accuracy = (df["ground_truth"] == df["ai_decision"]).mean()
            st.metric("Reference-Aligned Accuracy", f"{accuracy:.0%}")

        with col3:
            human_review_rate = (df["threshold_action"] == "human_review_required").mean()
            st.metric("Human Review Rate", f"{human_review_rate:.0%}")

        with col4:
            st.metric("Avg Judge Score", round(df["judge_score"].mean(), 2))

        st.markdown("### Decision & Risk Distribution")

        chart_col1, chart_col2 = st.columns(2)

        with chart_col1:
            if "ai_decision" in df.columns:
                decision_counts = df["ai_decision"].value_counts().reset_index()
                decision_counts.columns = ["AI Decision", "Count"]
                st.bar_chart(decision_counts, x="AI Decision", y="Count")

        with chart_col2:
            if "risk_band" in df.columns:
                risk_counts = df["risk_band"].value_counts().reset_index()
                risk_counts.columns = ["Risk Band", "Count"]
                st.bar_chart(risk_counts, x="Risk Band", y="Count")

        st.subheader("Case-Level Evaluation Results")

        st.caption(
            "Each row represents one reviewed case, including the reference decision, AI decision, "
            "risk score, threshold action, judge score, reasoning quality, and semantic similarity."
        )

        st.dataframe(df, use_container_width=True)

        st.subheader("Interpretation")

        st.write(
            "The dashboard evaluates the system beyond simple label matching by combining "
            "policy-grounded decisioning, LLM-as-Judge scoring, semantic reasoning alignment, "
            "risk-band calibration, and threshold-based human review routing."
        )

        st.write(
            "A high reference-aligned accuracy on this benchmark should be interpreted as a "
            "workflow validation signal rather than proof of production performance. In a real deployment, "
            "the same pipeline should be tested on larger, independently labeled historical cases."
        )


with tab2:
    st.subheader("Interactive Case Review")
    st.write(
        "Test a single risk case with policy-grounded AI decisioning. "
        "Use a sample case or edit the JSON directly."
    )

    sample_cases = {
        "E-commerce: high-value return without receipt": {
            "case_id": "CUSTOM-E-HIGH-VALUE-NO-RECEIPT",
            "domain": "ecommerce",
            "customer_profile": {
                "account_age_days": 28,
                "num_past_refunds_60d": 2
            },
            "transaction": {
                "item_price": 899.99,
                "delivery_days_ago": 6
            },
            "customer_claim": "Customer requests a refund for a high-value electronic item but cannot provide a receipt or clear photo evidence.",
            "evidence_provided": False,
            "ground_truth_decision": "escalate"
        },
        "E-commerce: low-risk standard return": {
            "case_id": "CUSTOM-E-STANDARD-RETURN",
            "domain": "ecommerce",
            "customer_profile": {
                "account_age_days": 420,
                "num_past_refunds_60d": 0
            },
            "transaction": {
                "item_price": 48.50,
                "delivery_days_ago": 4
            },
            "customer_claim": "Customer reports that the item arrived in the wrong size and requests a standard return within the allowed return window.",
            "evidence_provided": True,
            "ground_truth_decision": "approve"
        },
        "Finance: new account rapid high-value transfer": {
            "case_id": "CUSTOM-F-NEW-RAPID-HIGH-VALUE",
            "domain": "finance",
            "customer_profile": {
                "account_age_days": 4
            },
            "transaction": {
                "amount": 12500.00,
                "rapid_transactions": True,
                "geo_risk": True
            },
            "customer_claim": "New account initiated multiple high-value transfers within 24 hours from a new geographic location.",
            "ground_truth_decision": "escalate"
        },
        "Finance: routine business transfer": {
            "case_id": "CUSTOM-F-ROUTINE-BUSINESS",
            "domain": "finance",
            "customer_profile": {
                "account_age_days": 760
            },
            "transaction": {
                "amount": 850.00,
                "rapid_transactions": False,
                "geo_risk": False
            },
            "customer_claim": "Long-standing customer sends a routine payment to an existing vendor with no unusual activity.",
            "ground_truth_decision": "approve"
        }
    }

    if "interactive_case_json" not in st.session_state:
        st.session_state["interactive_case_json"] = json.dumps(
            sample_cases["E-commerce: high-value return without receipt"],
            indent=2
        )

    col_left, col_right = st.columns([1, 1.1])

    with col_left:
        st.markdown("### 1. Configure Case")

        selected_sample = st.selectbox(
            "Load a sample case",
            list(sample_cases.keys())
        )

        if st.button("Load Selected Sample"):
            st.session_state["interactive_case_json"] = json.dumps(
                sample_cases[selected_sample],
                indent=2
            )

        mode = st.radio(
            "Decision Mode",
            ["RAG Agent", "Agentic Review"],
            help=(
                "RAG Agent is faster and cheaper. "
                "Agentic Review runs draft → critique → refine and uses more API calls."
            )
        )

        run_evaluation = st.checkbox(
            "Run evaluation scoring",
            value=False,
            help=(
                "When enabled, the app also runs LLM-as-Judge and semantic similarity. "
                "This is useful for demo metrics but costs extra API calls."
            )
        )

        st.markdown("### 2. Edit Case JSON")

        case_json_text = st.text_area(
            "Case JSON",
            key="interactive_case_json",
            height=430
        )

        analyze_case = st.button("Analyze Case", type="primary")

    with col_right:
        st.markdown("### 3. AI Review Output")

        if analyze_case:
            try:
                custom_case = json.loads(case_json_text)
            except json.JSONDecodeError as e:
                st.error(f"Invalid JSON format: {e}")
                st.stop()

            required_fields = ["case_id", "domain", "customer_profile", "transaction"]
            missing_fields = [field for field in required_fields if field not in custom_case]

            if missing_fields:
                st.error(f"Missing required fields: {missing_fields}")
                st.stop()

            if custom_case["domain"] not in ["ecommerce", "finance"]:
                st.error("Domain must be either 'ecommerce' or 'finance'.")
                st.stop()

            with st.spinner("Running policy-grounded AI risk review..."):
                if mode == "Agentic Review":
                    ai_result = agentic_decision_system(custom_case)
                else:
                    ai_result = rag_decision_agent(custom_case)

            decision = ai_result.get("decision", "unknown")
            score = ai_result.get("risk_score", None)

            st.markdown("#### Decision Summary")

            c1, c2, c3 = st.columns(3)
            c1.metric("Decision", str(decision).upper())

            if isinstance(score, (int, float)):
                c2.metric("Risk Score", round(float(score), 2))
                c3.metric("Risk Band", risk_band(float(score)).upper())
                st.progress(min(max(float(score), 0.0), 1.0))
            else:
                c2.metric("Risk Score", "N/A")
                c3.metric("Risk Band", "UNKNOWN")

            st.markdown("#### Recommended Action")

            action = threshold_action(score)

            if action == "human_review_required":
                st.warning("Human review required before final decision.")
            elif action == "secondary_review":
                st.info("Secondary review recommended.")
            elif action == "auto_approve_allowed":
                st.success("Auto-approval may be allowed under the current risk threshold.")
            else:
                st.warning("Manual check required because risk score is unavailable.")

            st.markdown("#### AI Reasoning")
            st.write(ai_result.get("reasoning", "No reasoning returned."))

            st.markdown("#### Risk Signals")
            risk_signals = ai_result.get("risk_signals", [])
            if risk_signals:
                for signal in risk_signals:
                    st.write(f"- {signal}")
            else:
                st.write("No risk signals returned.")

            st.markdown("#### Policy Evidence")
            policy_evidence = ai_result.get("policy_evidence", [])
            if policy_evidence:
                for evidence in policy_evidence:
                    st.write(f"- {evidence}")
            else:
                st.write("No policy evidence returned.")

            retrieved_rules = ai_result.get("retrieved_rules", [])
            if retrieved_rules:
                with st.expander("Retrieved Policy Context"):
                    for i, rule in enumerate(retrieved_rules, start=1):
                        st.markdown(f"**Retrieved Rule {i}**")
                        st.write(rule)

            if run_evaluation:
                st.markdown("#### Evaluation Scoring")

                with st.spinner("Running evaluation scoring..."):
                    judge = llm_judge(custom_case, ai_result)
                    sem = semantic_evaluator(custom_case, ai_result)

                e1, e2, e3 = st.columns(3)
                e1.metric("LLM Judge Score", judge.get("overall_score"))
                e2.metric("Reasoning Quality", judge.get("reasoning_quality"))
                e3.metric(
                    "Semantic Similarity",
                    round(sem.get("semantic_similarity", 0), 3)
                )

                with st.expander("Evaluator Details"):
                    st.json({
                        "llm_judge": judge,
                        "semantic_evaluation": sem
                    })

            if mode == "Agentic Review":
                with st.expander("Agentic Draft and Critique"):
                    st.markdown("**Draft**")
                    st.write(ai_result.get("draft", "No draft returned."))
                    st.markdown("**Critique**")
                    st.write(ai_result.get("critique", "No critique returned."))

            with st.expander("Raw Structured AI Output"):
                st.json(ai_result)
        else:
            st.info("Load a sample case, edit the JSON if needed, then click Analyze Case.")