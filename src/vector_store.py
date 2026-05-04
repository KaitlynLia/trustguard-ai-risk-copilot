#RAG
import re
import chromadb
from src.config import POLICY_DIR, VECTOR_DB_DIR

COLLECTION_NAME = "policy_rules"


def split_policy_into_rules(policy_text: str, max_chars: int = 1200):
    """
    Split policy text into retrieval-friendly chunks.
    Works for short handcrafted policies and longer extracted FINRA text.
    """
    policy_text = policy_text.strip()
    if not policy_text:
        return []

    paragraphs = [
        p.strip()
        for p in re.split(r"\n\s*\n", policy_text)
        if len(p.strip()) > 40
    ]

    chunks = []
    current = ""

    for paragraph in paragraphs:
        if len(current) + len(paragraph) <= max_chars:
            current = (current + "\n\n" + paragraph).strip()
        else:
            if current:
                chunks.append(current)
            current = paragraph

    if current:
        chunks.append(current)

    return chunks


def initialize_vector_store(reset: bool = True):
    """
    Build a local ChromaDB vector store from policy files.
    reset=True is useful after policy files change.
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
        policy_text = path.read_text(encoding="utf-8")
        rules = split_policy_into_rules(policy_text)

        for i, rule in enumerate(rules):
            documents.append(rule)
            ids.append(f"{domain}_rule_{i}")
            metadatas.append(
                {
                    "domain": domain,
                    "rule_id": i,
                    "source_file": path.name,
                }
            )

    if not documents:
        raise ValueError("No policy rules were extracted. Check policy files.")

    collection.add(
        documents=documents,
        ids=ids,
        metadatas=metadatas,
    )

    return collection


def get_vector_collection():
    db_client = chromadb.PersistentClient(path=str(VECTOR_DB_DIR))
    return db_client.get_collection(COLLECTION_NAME)


def retrieve_relevant_rules(case: dict, top_k: int = 5):
    """
    Retrieve the most relevant policy rules for a case.
    """
    collection = get_vector_collection()
    query = str(case)

    results = collection.query(
        query_texts=[query],
        n_results=top_k,
        where={"domain": case["domain"]},
    )

    return results["documents"][0]