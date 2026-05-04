import re
import requests
from pathlib import Path
from pypdf import PdfReader

FINRA_URL = "https://www.finra.org/sites/default/files/2025-01/2025-annual-regulatory-oversight-report.pdf"

ROOT_DIR = Path(__file__).resolve().parent.parent
POLICY_DIR = ROOT_DIR / "data" / "policies"
RAW_DIR = ROOT_DIR / "data" / "raw"

PDF_PATH = RAW_DIR / "finra_2025_annual_regulatory_oversight_report.pdf"
OUTPUT_PATH = POLICY_DIR / "financial_risk_policy.txt"


def download_finra_pdf():
    RAW_DIR.mkdir(parents=True, exist_ok=True)

    response = requests.get(FINRA_URL, timeout=60)
    response.raise_for_status()

    PDF_PATH.write_bytes(response.content)
    print(f"Downloaded FINRA PDF to: {PDF_PATH}")


def extract_pdf_text():
    reader = PdfReader(str(PDF_PATH))
    pages = []

    for page in reader.pages:
        text = page.extract_text() or ""
        pages.append(text)

    full_text = "\n".join(pages)
    full_text = re.sub(r"\n{3,}", "\n\n", full_text)
    full_text = re.sub(r"[ \t]+", " ", full_text)

    return full_text


def keep_relevant_sections(full_text: str) -> str:
    keywords = [
        "Financial Crimes Prevention",
        "Cybersecurity and Cyber-Enabled Fraud",
        "Anti-Money Laundering, Fraud and Sanctions",
        "New Account Fraud",
        "Account Takeovers",
        "Investment Fraud",
        "suspicious transactions",
        "customer due diligence",
        "geographic",
        "fraud",
        "sanctions",
        "AML",
        "risk",
        "escalate",
        "monitoring",
    ]

    paragraphs = [p.strip() for p in full_text.split("\n\n") if len(p.strip()) > 80]

    selected = []
    for p in paragraphs:
        if any(k.lower() in p.lower() for k in keywords):
            selected.append(p)

    header = """
Financial Transaction Risk Review Policy

Source: FINRA 2025 Annual Regulatory Oversight Report
URL: https://www.finra.org/sites/default/files/2025-01/2025-annual-regulatory-oversight-report.pdf

This policy text is extracted from publicly available FINRA regulatory guidance and adapted for a prototype AI risk decision copilot. It is used for educational and portfolio demonstration purposes only.
"""

    if not selected:
        raise ValueError("No relevant FINRA sections were extracted. Check PDF parsing.")

    return header.strip() + "\n\n" + "\n\n".join(selected)


def main():
    download_finra_pdf()
    full_text = extract_pdf_text()
    policy_text = keep_relevant_sections(full_text)

    POLICY_DIR.mkdir(parents=True, exist_ok=True)
    OUTPUT_PATH.write_text(policy_text, encoding="utf-8")

    print(f"Saved extracted FINRA policy text to: {OUTPUT_PATH}")
    print(f"Characters saved: {len(policy_text)}")


if __name__ == "__main__":
    main()