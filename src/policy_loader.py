from src.config import POLICY_DIR

def load_policy(domain: str) -> str:
    if domain == "ecommerce":
        path = POLICY_DIR / "ecommerce_return_policy.txt"
    elif domain == "finance":
        path = POLICY_DIR / "financial_risk_policy.txt"
    else:
        raise ValueError(f"Unknown domain: {domain}")

    return path.read_text()


def get_policy_for_case(case: dict) -> str:
    return load_policy(case["domain"])