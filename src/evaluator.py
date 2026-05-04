import json
import numpy as np
from sklearn.metrics.pairwise import cosine_similarity
from src.config import client


def safe_json_parse(content: str):
    try:
        return json.loads(content)
    except Exception:
        return {
            "error": "JSON parsing failed",
            "raw_output": content
        }


def llm_judge(case: dict, ai_result: dict):
    judge_prompt = f"""
You are an independent evaluator for an AI risk decision system.

Evaluate whether the AI decision is correct, policy-grounded, and useful for a human analyst.

Return valid JSON only with this schema:
{{
  "decision_correctness": 0,
  "policy_grounding": 0,
  "reasoning_quality": 0,
  "risk_score_alignment": 0,
  "overall_score": 0,
  "main_issue": "briefly describe the biggest issue, or 'none'",
  "improvement_suggestion": "brief suggestion"
}}

Ground Truth Decision:
{case["ground_truth_decision"]}

Case:
{json.dumps(case, indent=2)}

AI Result:
{json.dumps(ai_result, indent=2)}
"""

    response = client.chat.completions.create(
        model="gpt-4o-mini",
        temperature=0,
        messages=[
            {"role": "system", "content": "You are a strict evaluator. Return valid JSON only."},
            {"role": "user", "content": judge_prompt}
        ]
    )

    return safe_json_parse(response.choices[0].message.content)


def get_embedding(text: str):
    response = client.embeddings.create(
        model="text-embedding-3-small",
        input=text
    )
    return response.data[0].embedding


def build_reference_reasoning(case: dict):
    if case["domain"] == "ecommerce":
        profile = case["customer_profile"]
        txn = case["transaction"]

        return f"""
Decision should be {case['ground_truth_decision']} based on ecommerce return policy.
Item price is {txn.get('item_price')}.
Customer has {profile.get('num_past_refunds_60d')} refund requests in the past 60 days.
Evidence provided: {case.get('evidence_provided')}.
Account age: {profile.get('account_age_days')} days.
Relevant factors include high-value items, frequent refund behavior, missing evidence,
claim type, and manual review requirements.
"""

    if case["domain"] == "finance":
        profile = case["customer_profile"]
        txn = case["transaction"]

        return f"""
Decision should be {case['ground_truth_decision']} based on financial transaction risk policy.
Transaction amount is {txn.get('amount')}.
Account age: {profile.get('account_age_days')} days.
Rapid transactions: {txn.get('rapid_transactions')}.
Geographic risk: {txn.get('geo_risk')}.
Relevant factors include transaction size, new account risk, rapid transfers,
geographic risk, and escalation requirements.
"""

    return f"Decision should be {case['ground_truth_decision']}."


def semantic_evaluator(case: dict, ai_result: dict):
    ai_reasoning = ai_result.get("reasoning", "")
    reference_reasoning = build_reference_reasoning(case)

    ai_emb = get_embedding(ai_reasoning)
    ref_emb = get_embedding(reference_reasoning)

    similarity = cosine_similarity(
        np.array(ai_emb).reshape(1, -1),
        np.array(ref_emb).reshape(1, -1)
    )[0][0]

    return {
        "case_id": case["case_id"],
        "semantic_similarity": float(similarity),
        "ai_reasoning": ai_reasoning,
        "reference_reasoning": reference_reasoning
    }


def risk_band(score):
    if score is None:
        return "unknown"
    if score < 0.4:
        return "low"
    elif score < 0.7:
        return "medium"
    else:
        return "high"


def threshold_action(score):
    if score is None:
        return "manual_check_required"
    if score >= 0.7:
        return "human_review_required"
    elif score >= 0.4:
        return "secondary_review"
    else:
        return "auto_approve_allowed"


def consistency_test(case: dict, agent_func, runs: int = 5):
    decisions = []
    scores = []

    for _ in range(runs):
        result = agent_func(case)
        decisions.append(result.get("decision"))
        scores.append(result.get("risk_score"))

    valid_scores = [s for s in scores if isinstance(s, (int, float))]

    score_variance = max(valid_scores) - min(valid_scores) if valid_scores else None

    return {
        "case_id": case["case_id"],
        "decisions": decisions,
        "scores": scores,
        "decision_consistent": len(set(decisions)) == 1,
        "score_variance": score_variance
    }