"""개발용 샘플 데이터 20건을 raw + clean 테이블에 넣는다.

담당: 팀원 A (팀장)
사용법: python seed_sample.py
샘플 기사는 팀에서 만든 가상 데이터이며 실제 언론 기사가 아니다.
수집(fetch) 코드가 완성되기 전에 팀원 C(AI) / D(리포트) 가 개발할 때 쓴다.
"""
import json
import logging
import os

import db
from cleaner import clean_article
from config import BASE_DIR, load_config, setup_logging


def main():
    cfg = load_config()
    setup_logging(cfg.get("log_level", "INFO"))
    conn = db.get_conn(cfg["db_path"])
    db.init_db(conn)

    path = os.path.join(BASE_DIR, "data", "sample_articles.json")
    with open(path, encoding="utf-8") as f:
        items = json.load(f)

    inserted = 0
    for a in items:
        if db.insert_raw(conn, a, policy="upsert") != "skipped":
            inserted += 1
    for r in db.get_raw_unclean(conn):
        c = clean_article(r)
        if c:
            db.insert_clean(conn, c)
    st = db.stats(conn)
    logging.info("샘플 적재 완료: raw %d건, clean %d건 (DB: %s)", st["raw"], st["clean"], cfg["db_path"])
    conn.close()


if __name__ == "__main__":
    main()
