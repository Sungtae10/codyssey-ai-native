"""SQLite 저장소. raw / clean / summaries / analyses 4개 테이블.

담당: 팀원 A (팀장)
다른 팀원은 이 파일의 함수만 호출하고 SQL 을 직접 쓰지 않는다.
기사 dict 의 키 이름은 컬럼명과 동일하게 맞춘다.
"""
import json
import sqlite3
from datetime import datetime

SCHEMA = """
CREATE TABLE IF NOT EXISTS raw_articles (
  id            INTEGER PRIMARY KEY AUTOINCREMENT,
  url           TEXT UNIQUE NOT NULL,
  title         TEXT,
  body          TEXT,
  source        TEXT,
  method        TEXT,
  category      TEXT,
  published_raw TEXT,
  collected_at  TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS clean_articles (
  id            INTEGER PRIMARY KEY,
  url           TEXT UNIQUE NOT NULL,
  title         TEXT NOT NULL,
  body          TEXT NOT NULL,
  source        TEXT,
  method        TEXT,
  category      TEXT NOT NULL,
  published_at  TEXT NOT NULL,
  collected_at  TEXT NOT NULL,
  status        TEXT NOT NULL DEFAULT 'clean',
  cleaned_at    TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS summaries (
  article_id  INTEGER PRIMARY KEY,
  summary     TEXT NOT NULL,
  keywords    TEXT,
  sentiment   TEXT,
  model       TEXT,
  created_at  TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS analyses (
  id            INTEGER PRIMARY KEY AUTOINCREMENT,
  date_from     TEXT,
  date_to       TEXT,
  category      TEXT,
  article_count INTEGER,
  result_json   TEXT NOT NULL,
  model         TEXT,
  created_at    TEXT NOT NULL
);
"""

RAW_COLS = ["url", "title", "body", "source", "method", "category", "published_raw", "collected_at"]
CLEAN_COLS = ["id", "url", "title", "body", "source", "method", "category",
              "published_at", "collected_at", "status", "cleaned_at"]


def _now() -> str:
    return datetime.now().isoformat(timespec="seconds")


# ---------- 연결 ----------
def get_conn(db_path: str) -> sqlite3.Connection:
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    return conn


def init_db(conn: sqlite3.Connection) -> None:
    conn.executescript(SCHEMA)
    conn.commit()


# ---------- raw ----------
def insert_raw(conn, article: dict, policy: str = "skip") -> str:
    """반환: 'inserted' | 'skipped' | 'updated'"""
    article.setdefault("collected_at", _now())
    vals = tuple(article.get(k) for k in RAW_COLS)
    cols = ",".join(RAW_COLS)
    marks = ",".join("?" * len(RAW_COLS))

    if policy == "upsert":
        exists = conn.execute("SELECT 1 FROM raw_articles WHERE url=?", (article["url"],)).fetchone()
        conn.execute(
            f"INSERT INTO raw_articles({cols}) VALUES({marks}) "
            "ON CONFLICT(url) DO UPDATE SET title=excluded.title, body=excluded.body, "
            "source=excluded.source, method=excluded.method, category=excluded.category, "
            "published_raw=excluded.published_raw, collected_at=excluded.collected_at",
            vals,
        )
        conn.commit()
        return "updated" if exists else "inserted"

    cur = conn.execute(f"INSERT OR IGNORE INTO raw_articles({cols}) VALUES({marks})", vals)
    conn.commit()
    return "inserted" if cur.rowcount else "skipped"


def get_raw_unclean(conn) -> list:
    rows = conn.execute(
        "SELECT r.* FROM raw_articles r LEFT JOIN clean_articles c ON c.id = r.id WHERE c.id IS NULL ORDER BY r.id"
    ).fetchall()
    return [dict(r) for r in rows]


def get_raw_count(conn) -> int:
    return conn.execute("SELECT COUNT(*) FROM raw_articles").fetchone()[0]


# ---------- clean ----------
def insert_clean(conn, article: dict) -> None:
    article.setdefault("status", "clean")
    article.setdefault("cleaned_at", _now())
    cols = ",".join(CLEAN_COLS)
    marks = ",".join("?" * len(CLEAN_COLS))
    conn.execute(
        f"INSERT OR REPLACE INTO clean_articles({cols}) VALUES({marks})",
        tuple(article.get(k) for k in CLEAN_COLS),
    )
    conn.commit()


def get_clean(conn, category=None, date_from=None, date_to=None, status=None,
              keyword=None, limit=None, offset=0) -> list:
    """조건 필터된 clean 목록(요약·키워드·감성 LEFT JOIN 포함). list/show/export/analyze 공용."""
    sql = ("SELECT c.*, s.summary, s.keywords, s.sentiment "
           "FROM clean_articles c LEFT JOIN summaries s ON s.article_id = c.id WHERE 1=1")
    args = []
    if category:
        sql += " AND c.category=?"; args.append(category)
    if date_from:
        sql += " AND c.published_at>=?"; args.append(date_from)
    if date_to:
        sql += " AND c.published_at<=?"; args.append(date_to)
    if status:
        sql += " AND c.status=?"; args.append(status)
    if keyword:
        sql += " AND (c.title LIKE ? OR c.body LIKE ?)"; args += [f"%{keyword}%", f"%{keyword}%"]
    sql += " ORDER BY c.published_at DESC, c.id DESC"
    if limit:
        sql += f" LIMIT {int(limit)} OFFSET {int(offset)}"
    return [dict(r) for r in conn.execute(sql, args).fetchall()]


def get_clean_by_id(conn, article_id: int):
    rows = conn.execute(
        "SELECT c.*, s.summary, s.keywords, s.sentiment FROM clean_articles c "
        "LEFT JOIN summaries s ON s.article_id = c.id WHERE c.id=?", (article_id,)
    ).fetchall()
    return dict(rows[0]) if rows else None


def get_clean_count(conn, **filters) -> int:
    return len(get_clean(conn, **filters))


def get_unsummarized(conn, limit=None) -> list:
    return get_clean(conn, status="clean", limit=limit)


# ---------- summaries ----------
def save_summary(conn, article_id: int, summary: str, keywords, sentiment, model) -> None:
    kw = ",".join(keywords) if isinstance(keywords, (list, tuple)) else (keywords or "")
    conn.execute(
        "INSERT OR REPLACE INTO summaries(article_id, summary, keywords, sentiment, model, created_at) "
        "VALUES(?,?,?,?,?,?)",
        (article_id, summary, kw, sentiment, model, _now()),
    )
    conn.execute("UPDATE clean_articles SET status='summarized' WHERE id=?", (article_id,))
    conn.commit()


# ---------- analyses ----------
def save_analysis(conn, meta: dict, result: dict, model) -> int:
    cur = conn.execute(
        "INSERT INTO analyses(date_from, date_to, category, article_count, result_json, model, created_at) "
        "VALUES(?,?,?,?,?,?,?)",
        (meta.get("date_from"), meta.get("date_to"), meta.get("category"), meta.get("article_count"),
         json.dumps(result, ensure_ascii=False), model, _now()),
    )
    conn.commit()
    return cur.lastrowid


def get_latest_analysis(conn):
    row = conn.execute("SELECT * FROM analyses ORDER BY id DESC LIMIT 1").fetchone()
    if not row:
        return None
    d = dict(row)
    d["result"] = json.loads(d.pop("result_json"))
    return d


# ---------- 리포트용 집계 ----------
def stats(conn) -> dict:
    """품질 지표 계산에 쓰는 기본 숫자들."""
    raw = get_raw_count(conn)
    raw_no_body = conn.execute(
        "SELECT COUNT(*) FROM raw_articles WHERE body IS NULL OR LENGTH(body) < 100").fetchone()[0]
    clean = conn.execute("SELECT COUNT(*) FROM clean_articles").fetchone()[0]
    summarized = conn.execute("SELECT COUNT(*) FROM clean_articles WHERE status='summarized'").fetchone()[0]
    return {"raw": raw, "raw_no_body": raw_no_body, "clean": clean, "summarized": summarized}
