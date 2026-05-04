#RAG
import re
import chromadb
from src.config import POLICY_DIR, VECTOR_DB_DIR

COLLECTION_NAME = "policy_rules"


def split_policy_into_rules(policy_text: str):
    """
    Split policy text into policy rule chunks.
    Works for numbered rules, paragraphs, and simple line-based policies.
    """
    policy_text = policy_text.strip()

    if not policy_text:
        return []

    # First try numbered sections like "1. Standard Return Window"
    blocks = re.split(r"\n(?=\d+\.\s)", policy_text)

    rules = []
    for block in blocks:
        cleaned = block.strip()
        if len(cleaned) > 20:
            rules.append(cleaned)

    # Fallback: split by non-empty paragraphs
    if not rules:
        paragraphs = [p.strip() for p in policy_text.split("\n\n") if len(p.strip()) > 20]
        rules.extend(paragraphs)

    # Final fallback: split by lines
    if not rules:
        lines = [line.strip() for line in policy_text.splitlines() if len(line.strip()) > 10]
        rules.extend(lines)

    return rules


def initialize_vector_store(reset: bool = True):
    """
    Build a local ChromaDB vector store from policy files.
    reset=True is useful during development to avoid duplicate IDs.
    """
    VECTOR_DB_DIR.mkdir(parents=True, exist_ok=True)

    db_client = chromadb.PersistentClient(path=str(VECTOR_DB_DIR))

    if reset:
        try:
            db_client.delete_collection(COLLECTION_NAME)
        except Exception:
            pass

    collection = db_client.get_or_create_collection(name=COLLECTION_NAME)

    policy_files = {
        "ecommerce": POLICY_DIR / "ecommerce_return_policy.txt",
        "finance": POLICY_DIR / "financial_risk_policy.txt",
    }

    documents = []
    ids = []
    metadatas = []

    for domain, path in policy_files.items():
        policy_text = path.read_text()
        rules = split_policy_into_rules(policy_text)

        for i, rule in enumerate(rules):
            documents.append(rule)
            ids.append(f"{domain}_rule_{i}")
            metadatas.append({"domain": domain, "rule_id": i})
    
    if not documents:
        raise ValueError(
            "No policy rules were extracted. Check policy files and split_policy_into_rules()."
        )
    
    collection.add(
        documents=documents,
        ids=ids,
        metadatas=metadatas
    )

    return collection


def get_vector_collection():
    db_client = chromadb.PersistentClient(path=str(VECTOR_DB_DIR))
    return db_client.get_collection(COLLECTION_NAME)


def retrieve_relevant_rules(case: dict, top_k: int = 3):
    """
    Retrieve the most relevant policy rules for a case.
    """
    collection = get_vector_collection()

    query = str(case)

    results = collection.query(
        query_texts=[query],
        n_results=top_k,
        where={"domain": case["domain"]}
    )

    return results["documents"][0]