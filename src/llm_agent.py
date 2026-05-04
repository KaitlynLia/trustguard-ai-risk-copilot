import json
from src.config import client
from src.policy_loader import get_policy_for_case
from src.vector_store import retrieve_relevant_rules


def safe_json_parse(content: str):
    """
    Safely parse JSON from LLM output.
    """
    try:
        return json.loads(content)
    except Exception:
        return {
            "error": "JSON parsing failed",
            "raw_output": content
        }


def build_decision_prompt(case: dict, policy_context: str):
    return f"""
You are an AI risk decision copilot for digital transactions.

Your task is to review a customer case and make a decision based ONLY on the provided policy context.

STRICT REQUIREMENTS:
1. Base your decision only on the policy context.
2. Explicitly link each risk signal to a policy rule.
3. If signals conflict, explain the trade-off.
4. Return valid JSON only.

Decision options:
- approve
- reject
- escalate

Risk score rule:
- 0.0–0.3 = low risk
- 0.4–0.6 = medium risk
- 0.7–1.0 = high risk

Return JSON with this schema:
{{
  "decision": "approve/reject/escalate",
  "risk_score": 0.0,
  "risk_signals": ["signal 1", "signal 2"],
  "policy_evidence": ["specific policy rule used"],
  "reasoning": "brief but specific explanation",
  "recommended_action": "next step for analyst"
}}

Policy Context:
{policy_context}

Case:
{json.dumps(case, indent=2)}
"""


def call_llm_json(prompt: str, temperature: float = 0.3):
    response = client.chat.completions.create(
        model="gpt-4o-mini",
        temperature=temperature,
        messages=[
            {
                "role": "system",
                "content": "You are a precise risk analyst. Return valid JSON only."
            },
            {
                "role": "user",
                "content": prompt
            }
        ]
    )

    content = response.choices[0].message.content
    return safe_json_parse(content)


def decision_agent(case: dict, temperature: float = 0.3):
    """
    Baseline agent: uses full policy document.
    """
    policy = get_policy_for_case(case)
    prompt = build_decision_prompt(case, policy)
    return call_llm_json(prompt, temperature=temperature)


def rag_decision_agent(case: dict, temperature: float = 0.3, top_k: int = 3):
    """
    RAG agent: retrieves only relevant policy rules.
    """
    relevant_rules = retrieve_relevant_rules(case, top_k=top_k)
    policy_context = "\n\n".join(relevant_rules)

    prompt = build_decision_prompt(case, policy_context)
    result = call_llm_json(prompt, temperature=temperature)

    result["retrieved_rules"] = relevant_rules
    return result


def agentic_decision_system(case: dict, temperature: float = 0.3, top_k: int = 3):
    """
    Draft -> Critique -> Refine workflow.
    This is an advanced mode, not the default mode, because it uses more API calls.
    """
    relevant_rules = retrieve_relevant_rules(case, top_k=top_k)
    policy_context = "\n\n".join(relevant_rules)

    draft_prompt = f"""
You are a risk analyst. Draft an initial decision for the case using only the policy rules.

Policy Rules:
{policy_context}

Case:
{json.dumps(case, indent=2)}

Return concise analysis.
"""

    draft_response = client.chat.completions.create(
        model="gpt-4o-mini",
        temperature=temperature,
        messages=[
            {"role": "system", "content": "You are a careful risk analyst."},
            {"role": "user", "content": draft_prompt}
        ]
    )

    draft = draft_response.choices[0].message.content

    critique_prompt = f"""
You are a strict reviewer. Review the draft decision and find any unsupported claims,
missing policy evidence, or weak reasoning.

Policy Rules:
{policy_context}

Case:
{json.dumps(case, indent=2)}

Draft Decision:
{draft}

Return concise critique.
"""

    critique_response = client.chat.completions.create(
        model="gpt-4o-mini",
        temperature=temperature,
        messages=[
            {"role": "system", "content": "You are a strict reviewer."},
            {"role": "user", "content": critique_prompt}
        ]
    )

    critique = critique_response.choices[0].message.content

    final_prompt = f"""
You are an AI risk decision copilot.

Finalize the decision using:
1. The original case
2. The retrieved policy rules
3. The draft decision
4. The critique

Return valid JSON only with this schema:
{{
  "decision": "approve/reject/escalate",
  "risk_score": 0.0,
  "risk_signals": ["signal 1", "signal 2"],
  "policy_evidence": ["specific policy rule used"],
  "reasoning": "brief but specific explanation",
  "recommended_action": "next step for analyst",
  "draft_summary": "short summary of the first draft",
  "critique_summary": "short summary of what was corrected"
}}

Policy Rules:
{policy_context}

Case:
{json.dumps(case, indent=2)}

Draft:
{draft}

Critique:
{critique}
"""

    final_result = call_llm_json(final_prompt, temperature=0.1)

    final_result["retrieved_rules"] = relevant_rules
    final_result["draft"] = draft
    final_result["critique"] = critique

    return final_result