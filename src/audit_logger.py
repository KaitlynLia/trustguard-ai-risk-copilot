import json
import sqlite3
from pathlib import Path
from datetime import datetime, timezone

ROOT_DIR = Path(__file__).resolve().parent.parent
AUDIT_DB_PATH = ROOT_DIR / "data" / "audit_logs.db"


def get_connection():
    AUDIT_DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    return sqlite3.connect(AUDIT_DB_PATH)


def init_audit_db():
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS review_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp TEXT NOT NULL,
            mode TEXT,
            case_id TEXT,
            domain TEXT,
            case_json TEXT,
            ai_decision TEXT,
            risk_score REAL,
            risk_band TEXT,
            threshold_action TEXT,
            reasoning TEXT,
            risk_signals_json TEXT,
            policy_evidence_json TEXT,
            retrieved_rules_json TEXT,
            judge_score REAL,
            reasoning_quality REAL,
            semantic_similarity REAL,
            latency_seconds REAL,
            reviewer_final_decision TEXT,
            reviewer_note TEXT,
            reviewer_agrees INTEGER
        )
        """
    )

    conn.commit()
    conn.close()


def save_review(
    case,
    ai_result,
    mode,
    risk_band_value,
    threshold_action_value,
    judge=None,
    semantic=None,
    latency_seconds=None,
):
    init_audit_db()

    judge = judge or {}
    semantic = semantic or {}

    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute(
        """
        INSERT INTO review_logs (
            timestamp,
            mode,
            case_id,
            domain,
            case_json,
            ai_decision,
            risk_score,
            risk_band,
            threshold_action,
            reasoning,
            risk_signals_json,
            policy_evidence_json,
            retrieved_rules_json,
            judge_score,
            reasoning_quality,
            semantic_similarity,
            latency_seconds
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            datetime.now(timezone.utc).isoformat(),
            mode,
            case.get("case_id"),
            case.get("domain"),
            json.dumps(case, ensure_ascii=False),
            ai_result.get("decision"),
            ai_result.get("risk_score"),
            risk_band_value,
            threshold_action_value,
            ai_result.get("reasoning"),
            json.dumps(ai_result.get("risk_signals", []), ensure_ascii=False),
            json.dumps(ai_result.get("policy_evidence", []), ensure_ascii=False),
            json.dumps(ai_result.get("retrieved_rules", []), ensure_ascii=False),
            judge.get("overall_score"),
            judge.get("reasoning_quality"),
            semantic.get("semantic_similarity"),
            latency_seconds,
        ),
    )

    audit_id = cursor.lastrowid
    conn.commit()
    conn.close()

    return audit_id


def save_feedback(audit_id, reviewer_final_decision, reviewer_note, reviewer_agrees):
    init_audit_db()

    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute(
        """
        UPDATE review_logs
        SET
            reviewer_final_decision = ?,
            reviewer_note = ?,
            reviewer_agrees = ?
        WHERE id = ?
        """,
        (
            reviewer_final_decision,
            reviewer_note,
            int(bool(reviewer_agrees)),
            audit_id,
        ),
    )

    conn.commit()
    conn.close()


def load_recent_reviews(limit=50):
    init_audit_db()

    conn = get_connection()
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    cursor.execute(
        """
        SELECT
            id,
            timestamp,
            mode,
            case_id,
            domain,
            ai_decision,
            risk_score,
            risk_band,
            threshold_action,
            judge_score,
            semantic_similarity,
            latency_seconds,
            reviewer_final_decision,
            reviewer_agrees
        FROM review_logs
        ORDER BY id DESC
        LIMIT ?
        """,
        (limit,),
    )

    rows = [dict(row) for row in cursor.fetchall()]
    conn.close()

    return rows