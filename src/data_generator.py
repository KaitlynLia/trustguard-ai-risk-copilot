import random
import json
from pathlib import Path

# Fix the random seed for reproducibility 
random.seed(42)

def generate_ecommerce_case(i):
    price = random.choice([50, 120, 300, 600, 980, 1500])
    refunds = random.randint(0, 6)
    account_age = random.randint(5, 365)
    delivery_days = random.randint(1, 10)
    evidence = random.choice([True, False])

    # Ground truth rule logic
    if price > 500 and refunds >= 3:
        decision = "escalate"
    elif refunds >= 5:
        decision = "reject"
    elif not evidence:
        decision = "escalate"
    else:
        decision = "approve"

    return {
        "case_id": f"E-{i:03d}",
        "domain": "ecommerce",
        "customer_profile": {
            "account_age_days": account_age,
            "num_past_refunds_60d": refunds,
        },
        "transaction": {
            "item_price": price,
            "delivery_days_ago": delivery_days
        },
        "customer_claim": random.choice([
            "item is defective",
            "wrong item received",
            "no longer needed",
            "item damaged on arrival"
        ]),
        "evidence_provided": evidence,
        "ground_truth_decision": decision
    }

def generate_finance_case(i):
    amount = random.choice([200, 800, 2000, 5000, 12000])
    account_age = random.randint(1, 365)
    rapid_txn = random.choice([True, False])
    geo_risk = random.choice([True, False])

    if amount > 5000 and account_age < 30:
        decision = "escalate"
    elif rapid_txn and geo_risk:
        decision = "reject"
    elif geo_risk:
        decision = "escalate"
    else:
        decision = "approve"

    return {
        "case_id": f"F-{i:03d}",
        "domain": "finance",
        "customer_profile": {
            "account_age_days": account_age
        },
        "transaction": {
            "amount": amount,
            "rapid_transactions": rapid_txn,
            "geo_risk": geo_risk
        },
        "customer_claim": "Transaction flagged for review",
        "ground_truth_decision": decision
    }

if __name__ == "__main__":
    # Dynamically resolve the project root directory
    root_dir = Path(__file__).resolve().parent.parent
    data_path = root_dir / "data" / "cases"
    data_path.mkdir(parents=True, exist_ok=True)
    
    cases = []
    
    # Generate ecommerce mock data
    for i in range(100):
        cases.append(generate_ecommerce_case(i))
        
    # Generate finance mock data
    for i in range(100):
        cases.append(generate_finance_case(i))
        
    output_path = data_path / "cases.json"
    with open(output_path, "w") as f:
        json.dump(cases, f, indent=2)
        
    print(f" Successfully generated 200 mock cases and saved to: {output_path}")