import os
from pathlib import Path
from dotenv import load_dotenv
from openai import OpenAI

ROOT_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = ROOT_DIR / "data"
POLICY_DIR = DATA_DIR / "policies"
CASE_DIR = DATA_DIR / "cases"
OUTPUT_DIR = DATA_DIR / "outputs"
VECTOR_DB_DIR = DATA_DIR / "vector_db"

load_dotenv(ROOT_DIR / ".env", override=True)

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

if not OPENAI_API_KEY:
    raise ValueError("OPENAI_API_KEY is missing. Please check your .env file.")

client = OpenAI(api_key=OPENAI_API_KEY)