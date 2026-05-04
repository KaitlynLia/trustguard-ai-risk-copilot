import pandas as pd
import json
from pathlib import Path


def load_ecommerce_csv(csv_path):
    df = pd.read_csv(csv_path)
    cases = []

    for _, row in df.iterrows():
        cases.append({
            "case_id": row["case_id"],
            "domain": "ecommerce",
            "customer_profile": {
                "account_age_days": int(row["account_age_days"]),
                "num_past_refunds_60d": int(row["num_past_refunds_60d"])
            },
            "transaction": {
                "item_price": float(row["item_price"]),
                "delivery_days_ago": int(row["delivery_days_ago"])
            },
            "customer_claim": row["customer_claim"],
            "evidence_provided": bool(row["evidence_provided"]),
            "ground_truth_decision": row.get("ground_truth_decision", "unknown")
        })

    return cases


def load_finance_csv(csv_path):
    df = pd.read_csv(csv_path)
    cases = []

    for _, row in df.iterrows():
        cases.append({
            "case_id": row["case_id"],
            "domain": "finance",
            "customer_profile": {
                "account_age_days": int(row["account_age_days"])
            },
            "transaction": {
                "amount": float(row["amount"]),
                "rapid_transactions": bool(row["rapid_transactions"]),
                "geo_risk": bool(row["geo_risk"])
            },
            "customer_claim": row["customer_claim"],
            "ground_truth_decision": row.get("ground_truth_decision", "unknown")
        })

    return cases


def save_cases(cases, output_path):
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    with open(output_path, "w") as f:
        json.dump(cases, f, indent=2)

    print(f"Saved {len(cases)} cases to {output_path}")