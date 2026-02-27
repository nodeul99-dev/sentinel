"""
Sentinel.DS 통합 DB 모듈 (규정검색 + FSS 재무건전성 + 손익집계)
"""
import hashlib
import json
import sqlite3
import os
from datetime import datetime
from pathlib import Path

from config import DB_PATH


def get_conn() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


# ── DB 초기화 ───────────────────────────────────────────────────────────────

def init_db():
    """규정검색 테이블 초기화"""
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    with get_conn() as conn:
        conn.executescript("""
            CREATE TABLE IF NOT EXISTS documents (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                doc_name TEXT NOT NULL,
                doc_category TEXT NOT NULL,
                filename TEXT NOT NULL,
                uploaded_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                article_count INTEGER DEFAULT 0,
                enacted_date TEXT
            );

            CREATE TABLE IF NOT EXISTS articles (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                doc_id INTEGER REFERENCES documents(id) ON DELETE CASCADE,
                article_number TEXT,
                article_title TEXT,
                article_text TEXT NOT NULL,
                page_number INTEGER
            );

            CREATE INDEX IF NOT EXISTS idx_articles_doc_id ON articles(doc_id);
        """)
        cols = [r[1] for r in conn.execute("PRAGMA table_info(documents)").fetchall()]
        if "enacted_date" not in cols:
            conn.execute("ALTER TABLE documents ADD COLUMN enacted_date TEXT")
        if "source_type" not in cols:
            conn.execute("ALTER TABLE documents ADD COLUMN source_type TEXT NOT NULL DEFAULT 'pdf'")


def init_fss_tables():
    """FSS 재무건전성 테이블 초기화"""
    with get_conn() as conn:
        conn.executescript("""
            CREATE TABLE IF NOT EXISTS fss_securities_data (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                company_code TEXT NOT NULL,
                company_name TEXT NOT NULL,
                quarter TEXT NOT NULL,
                data_source TEXT NOT NULL,
                metrics TEXT NOT NULL,
                collected_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(company_code, quarter, data_source)
            );

            CREATE TABLE IF NOT EXISTS fss_update_log (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                data_source TEXT NOT NULL,
                quarter TEXT NOT NULL,
                update_status TEXT,
                items_count INTEGER,
                error_message TEXT,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );

        """)


# ── 규정검색: 문서 CRUD ──────────────────────────────────────────────────────

def upsert_document(
    doc_name: str, doc_category: str, filename: str,
    enacted_date: str | None = None, source_type: str = "pdf",
) -> int:
    with get_conn() as conn:
        row = conn.execute(
            "SELECT id FROM documents WHERE doc_name = ? AND doc_category = ?",
            (doc_name, doc_category),
        ).fetchone()
        if row:
            doc_id = row["id"]
            conn.execute("DELETE FROM articles WHERE doc_id = ?", (doc_id,))
            conn.execute(
                "UPDATE documents SET filename = ?, uploaded_at = ?, enacted_date = ?, source_type = ? WHERE id = ?",
                (filename, datetime.now().isoformat(), enacted_date, source_type, doc_id),
            )
        else:
            cur = conn.execute(
                "INSERT INTO documents (doc_name, doc_category, filename, enacted_date, source_type) VALUES (?, ?, ?, ?, ?)",
                (doc_name, doc_category, filename, enacted_date, source_type),
            )
            doc_id = cur.lastrowid
    return doc_id


def update_article_count(doc_id: int, count: int):
    with get_conn() as conn:
        conn.execute(
            "UPDATE documents SET article_count = ? WHERE id = ?", (count, doc_id)
        )


def insert_articles(doc_id: int, articles: list[dict]):
    with get_conn() as conn:
        conn.executemany(
            """INSERT INTO articles (doc_id, article_number, article_title, article_text, page_number)
               VALUES (:doc_id, :article_number, :article_title, :article_text, :page_number)""",
            [{"doc_id": doc_id, **a} for a in articles],
        )


def get_all_documents() -> list[dict]:
    with get_conn() as conn:
        rows = conn.execute(
            "SELECT * FROM documents ORDER BY uploaded_at DESC"
        ).fetchall()
    return [dict(r) for r in rows]


def delete_document(doc_id: int):
    with get_conn() as conn:
        conn.execute("DELETE FROM documents WHERE id = ?", (doc_id,))


def get_document_by_id(doc_id: int) -> dict | None:
    with get_conn() as conn:
        row = conn.execute(
            "SELECT * FROM documents WHERE id = ?", (doc_id,)
        ).fetchone()
    return dict(row) if row else None


def get_articles_by_doc_id(doc_id: int) -> list[dict]:
    with get_conn() as conn:
        rows = conn.execute(
            "SELECT * FROM articles WHERE doc_id = ? ORDER BY id", (doc_id,)
        ).fetchall()
    return [dict(r) for r in rows]


def search_articles(keyword: str, categories: list[str] | None = None) -> list[dict]:
    if not keyword.strip():
        return []

    placeholders = ""
    params: list = [f"%{keyword}%"]

    if categories:
        ph = ",".join("?" * len(categories))
        placeholders = f" AND d.doc_category IN ({ph})"
        params += categories

    sql = f"""
        SELECT a.id, a.doc_id, a.article_number, a.article_title, a.article_text, a.page_number,
               d.doc_name, d.doc_category, d.filename, d.source_type, d.enacted_date
        FROM articles a
        JOIN documents d ON a.doc_id = d.id
        WHERE a.article_text LIKE ?{placeholders}
        ORDER BY d.doc_name, a.id
    """
    with get_conn() as conn:
        rows = conn.execute(sql, params).fetchall()
    return [dict(r) for r in rows]


# ── FSS 재무건전성 ───────────────────────────────────────────────────────────

def save_fss_data(quarter: str, data_source: str, data_list: list[dict]):
    """
    수집된 증권사 데이터를 DB에 저장 (upsert).

    Args:
        quarter: "2024Q3"
        data_source: "ncr_data"
        data_list: [{"company_code": ..., "company_name": ..., "metrics": {...}}, ...]
    """
    now = datetime.now().isoformat()
    with get_conn() as conn:
        for item in data_list:
            metrics_json = json.dumps(item["metrics"], ensure_ascii=False)
            conn.execute("""
                INSERT INTO fss_securities_data
                    (company_code, company_name, quarter, data_source, metrics, collected_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(company_code, quarter, data_source)
                DO UPDATE SET
                    company_name = excluded.company_name,
                    metrics = excluded.metrics,
                    updated_at = excluded.updated_at
            """, (
                item["company_code"], item["company_name"],
                quarter, data_source, metrics_json, now, now
            ))



def get_fss_data(quarter: str, data_source: str) -> list[dict]:
    """특정 분기/소스의 데이터 조회"""
    with get_conn() as conn:
        rows = conn.execute("""
            SELECT company_code, company_name, quarter, data_source, metrics, updated_at
            FROM fss_securities_data
            WHERE quarter = ? AND data_source = ?
            ORDER BY company_name
        """, (quarter, data_source)).fetchall()

    result = []
    for row in rows:
        d = dict(row)
        d["metrics"] = json.loads(d["metrics"])
        result.append(d)
    return result


def get_available_quarters(data_source: str) -> list[str]:
    """데이터가 있는 분기 목록 반환"""
    with get_conn() as conn:
        rows = conn.execute("""
            SELECT DISTINCT quarter FROM fss_securities_data
            WHERE data_source = ?
            ORDER BY quarter DESC
        """, (data_source,)).fetchall()
    return [r["quarter"] for r in rows]


def get_company_history(company_name: str, data_source: str, n: int = 4) -> list[dict]:
    """특정 회사의 최근 n분기 데이터를 오래된 순으로 반환"""
    with get_conn() as conn:
        rows = conn.execute("""
            SELECT quarter, metrics
            FROM fss_securities_data
            WHERE company_name = ? AND data_source = ?
            ORDER BY quarter DESC
            LIMIT ?
        """, (company_name, data_source, n)).fetchall()
    result = []
    for row in reversed(rows):
        result.append({
            "quarter": row["quarter"],
            "metrics": json.loads(row["metrics"]),
        })
    return result


def log_fss_update(data_source: str, quarter: str, status: str,
                   items_count: int = 0, error_message: str = None):
    """업데이트 로그 기록"""
    with get_conn() as conn:
        conn.execute("""
            INSERT INTO fss_update_log
                (data_source, quarter, update_status, items_count, error_message)
            VALUES (?, ?, ?, ?, ?)
        """, (data_source, quarter, status, items_count, error_message))


def get_fss_update_log(limit: int = 20) -> list[dict]:
    """최근 업데이트 로그 조회"""
    with get_conn() as conn:
        rows = conn.execute("""
            SELECT * FROM fss_update_log
            ORDER BY updated_at DESC
            LIMIT ?
        """, (limit,)).fetchall()
    return [dict(r) for r in rows]


# ── 손익집계 ─────────────────────────────────────────────────────────────────

_PNL_DEFAULT_DIVISIONS = [
    # (division, department, sort_order)
    ("S&T",       "에쿼티마켓",   1),
    ("S&T",       "자본시장",     2),
    ("S&T",       "FI금융",       3),
    ("S&T",       "채권금융",     4),
    ("주식파생운용", "주식운용",   11),
    ("주식파생운용", "시장조성",   12),
    ("주식파생운용", "파생운용",   13),
    ("글로벌마켓",  "글로벌대체",  21),
    ("글로벌마켓",  "IB",          22),
    ("글로벌마켓",  "프로젝트금융", 23),
    ("대체투자",    "부동산금융",  31),
    ("대체투자",    "개발금융",    32),
    ("대체투자",    "자산관리",    33),
    ("헤지펀드",    "헤지펀드",    41),
    ("기타",        "기타",        51),
    ("본사공통",    "본사공통",    61),
]

_DEFAULT_PIN = "0000"


def _hash_pin(pin: str) -> str:
    return hashlib.sha256(pin.encode()).hexdigest()


def init_pnl_tables():
    """손익집계 테이블 초기화 및 기본 부서 데이터 시드"""
    with get_conn() as conn:
        conn.executescript("""
            CREATE TABLE IF NOT EXISTS pnl_divisions (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                division    TEXT NOT NULL,
                department  TEXT NOT NULL,
                pin_hash    TEXT NOT NULL,
                sort_order  INTEGER DEFAULT 0,
                UNIQUE(division, department)
            );

            CREATE TABLE IF NOT EXISTS pnl_entries (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                trade_date  TEXT NOT NULL,
                division    TEXT NOT NULL,
                department  TEXT NOT NULL,
                pnl_daily   REAL NOT NULL,
                entered_at  TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at  TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(trade_date, division, department)
            );
        """)
        count = conn.execute("SELECT COUNT(*) FROM pnl_divisions").fetchone()[0]
        if count == 0:
            default_hash = _hash_pin(_DEFAULT_PIN)
            conn.executemany(
                "INSERT OR IGNORE INTO pnl_divisions (division, department, pin_hash, sort_order) VALUES (?, ?, ?, ?)",
                [(div, dept, default_hash, order) for div, dept, order in _PNL_DEFAULT_DIVISIONS],
            )


def get_pnl_divisions() -> list[dict]:
    with get_conn() as conn:
        rows = conn.execute(
            "SELECT * FROM pnl_divisions ORDER BY sort_order"
        ).fetchall()
    return [dict(r) for r in rows]


def verify_pnl_pin(division: str, department: str, pin: str) -> bool:
    with get_conn() as conn:
        row = conn.execute(
            "SELECT pin_hash FROM pnl_divisions WHERE division = ? AND department = ?",
            (division, department),
        ).fetchone()
    if row is None:
        return False
    return row["pin_hash"] == _hash_pin(pin)


def set_pnl_pin(division: str, department: str, new_pin: str) -> bool:
    with get_conn() as conn:
        result = conn.execute(
            "UPDATE pnl_divisions SET pin_hash = ? WHERE division = ? AND department = ?",
            (_hash_pin(new_pin), division, department),
        )
    return result.rowcount > 0


def upsert_pnl_entry(trade_date: str, division: str, department: str, pnl_daily: float):
    now = datetime.now().isoformat()
    with get_conn() as conn:
        conn.execute("""
            INSERT INTO pnl_entries (trade_date, division, department, pnl_daily, entered_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?)
            ON CONFLICT(trade_date, division, department)
            DO UPDATE SET pnl_daily = excluded.pnl_daily, updated_at = excluded.updated_at
        """, (trade_date, division, department, pnl_daily, now, now))


def get_pnl_entries_by_date(trade_date: str) -> dict:
    """특정 날짜의 손익 반환 → {(division, department): pnl}"""
    with get_conn() as conn:
        rows = conn.execute(
            "SELECT division, department, pnl_daily FROM pnl_entries WHERE trade_date = ?",
            (trade_date,),
        ).fetchall()
    return {(r["division"], r["department"]): r["pnl_daily"] for r in rows}


def get_pnl_entries_sum(start_date: str, end_date: str) -> dict:
    """기간 합계 → {(division, department): sum}"""
    with get_conn() as conn:
        rows = conn.execute("""
            SELECT division, department, SUM(pnl_daily) as pnl_sum
            FROM pnl_entries
            WHERE trade_date >= ? AND trade_date <= ?
            GROUP BY division, department
        """, (start_date, end_date)).fetchall()
    return {(r["division"], r["department"]): r["pnl_sum"] for r in rows}


def get_pnl_latest_date() -> str | None:
    with get_conn() as conn:
        row = conn.execute(
            "SELECT MAX(trade_date) as latest FROM pnl_entries"
        ).fetchone()
    return row["latest"] if row and row["latest"] else None


def get_pnl_trend(division: str, department: str, start_date: str, end_date: str) -> list[dict]:
    """특정 본부 일별 손익 추이"""
    with get_conn() as conn:
        rows = conn.execute("""
            SELECT trade_date, pnl_daily
            FROM pnl_entries
            WHERE division = ? AND department = ?
              AND trade_date >= ? AND trade_date <= ?
            ORDER BY trade_date
        """, (division, department, start_date, end_date)).fetchall()
    return [dict(r) for r in rows]


def get_pnl_division_trend(division: str, start_date: str, end_date: str) -> list[dict]:
    """부문 전체 일별 합계 추이 (하위 본부 합산)"""
    with get_conn() as conn:
        rows = conn.execute("""
            SELECT trade_date, SUM(pnl_daily) as pnl_daily
            FROM pnl_entries
            WHERE division = ? AND trade_date >= ? AND trade_date <= ?
            GROUP BY trade_date
            ORDER BY trade_date
        """, (division, start_date, end_date)).fetchall()
    return [dict(r) for r in rows]
