"""뉴스 자동 수집·AI 분석 CLI 파이프라인 진입점.

담당: 팀원 A (팀장). 파서 정의는 팀장만 수정. cmd_* 함수 본문은 각 담당자가 채운다.
서브커맨드: fetch, clean, summarize, analyze, report, export, list, show
"""
import argparse
import logging
import os
import sys
import time

import db
from config import load_config, setup_logging

log = logging.getLogger("main")


# ---------- 팀원 B ----------
def cmd_fetch(args, cfg, conn):
    import fetcher
    policy = cfg.get("duplicate_policy", "skip")
    ua, delay, timeout = cfg.get("user_agent", ""), cfg.get("request_delay_sec", 1.0), cfg.get("request_timeout_sec", 10)
    log.info("뉴스 수집 시작: source=%s, category=%s, limit=%d", args.source, args.category or "전체", args.limit)
    counts = {"inserted": 0, "skipped": 0, "updated": 0, "failed": 0}

    sources = []
    if args.source in ("rss", "all"):
        sources += [("rss", s) for s in cfg["sources"].get("rss", [])]
    if args.source in ("crawl", "all"):
        sources += [("crawl", s) for s in cfg["sources"].get("crawl", [])]
    if args.category:
        sources = [(m, s) for m, s in sources if s.get("category") == args.category]

    for method, s in sources:
        try:
            if method == "rss":
                items = fetcher.fetch_rss(s["url"], s["category"], args.limit, s["name"],
                                          full_body=cfg.get("fetch_full_body", False),
                                          delay=delay, ua=ua, timeout=timeout)
            else:
                items = fetcher.fetch_crawl(s["section_url"], s["category"], args.limit, s,
                                            delay=delay, ua=ua, timeout=timeout, source_name=s["name"])
        except Exception as e:  # noqa: BLE001
            log.error("소스 %s 수집 실패: %s", s.get("name"), e)
            counts["failed"] += 1
            continue
        for a in items:
            counts[db.insert_raw(conn, a, policy)] += 1
        log.info("소스 %s: %d건 처리", s.get("name"), len(items))
    log.info("수집 완료: 신규 %d건, 중복스킵 %d건, 갱신 %d건, 실패 %d건",
             counts["inserted"], counts["skipped"], counts["updated"], counts["failed"])


def cmd_clean(args, cfg, conn):
    import cleaner
    raws = db.get_raw_unclean(conn)
    if args.limit:
        raws = raws[: args.limit]
    ok = bad = 0
    for r in raws:
        c = cleaner.clean_article(r)
        if c:
            db.insert_clean(conn, c); ok += 1
        else:
            bad += 1
    log.info("정제 완료: %d건 저장, %d건 제외", ok, bad)


# ---------- 팀원 C ----------
def cmd_summarize(args, cfg, conn):
    import analyzer
    if args.id:
        row = db.get_clean_by_id(conn, args.id)
        targets = [row] if row else []
    elif args.all:
        targets = db.get_clean(conn, limit=args.limit)
    else:  # 기본: --unsummarized
        targets = db.get_unsummarized(conn, limit=args.limit)

    if not args.force:
        before = len(targets)
        targets = [t for t in targets if t.get("status") != "summarized"]
        if before - len(targets):
            log.info("이미 요약된 %d건 스킵 (--force 로 재요약 가능)", before - len(targets))

    log.info("요약 대상: %d건", len(targets))
    ok = fail = 0
    for i, t in enumerate(targets, 1):
        log.info("[%d/%d] ID=%s 요약 중...", i, len(targets), t["id"])
        if analyzer.summarize_one(conn, t, cfg):
            ok += 1
        else:
            fail += 1
        time.sleep(0.3)
    log.info("요약 완료: %d건 성공, %d건 실패", ok, fail)


def cmd_analyze(args, cfg, conn):
    import analyzer
    log.info("AI 분석 요청 중... (기간 %s~%s, 카테고리 %s)", args.date_from, args.date_to, args.category or "전체")
    res = analyzer.analyze_range(conn, args.date_from, args.date_to, args.category, cfg)
    if res:
        log.info("분석 완료")
        print()
        print(analyzer.format_analysis(res))
    else:
        log.error("분석 결과 없음")


# ---------- 팀원 D ----------
def cmd_report(args, cfg, conn):
    import report
    text = report.build_report(conn, cfg)
    print(text)
    out = args.out or os.path.join(cfg["output_dir"], f"report.{args.format}")
    with open(out, "w", encoding="utf-8") as f:
        f.write(text)
    log.info("리포트 저장: %s", out)


def cmd_export(args, cfg, conn):
    import report
    rows = db.get_clean(conn, category=args.category, date_from=args.date_from,
                        date_to=args.date_to, status=args.status)
    out = args.out or os.path.join(cfg["output_dir"], f"news.{args.format}")
    report.export_data(rows, args.format, out)
    log.info("%d건 저장: %s", len(rows), out)


# ---------- 보너스 ----------
def cmd_list(args, cfg, conn):
    total = db.get_clean_count(conn, category=args.category, date_from=args.date_from,
                               date_to=args.date_to, keyword=args.keyword)
    rows = db.get_clean(conn, category=args.category, date_from=args.date_from, date_to=args.date_to,
                        keyword=args.keyword, limit=args.page_size, offset=(args.page - 1) * args.page_size)
    pages = max(1, -(-total // args.page_size))
    print(f"{'ID':>4} | {'날짜':10} | {'카테고리':6} | {'상태':10} | 제목")
    print("-" * 80)
    for r in rows:
        print(f"{r['id']:>4} | {r['published_at']:10} | {r['category']:6} | {r['status']:10} | {r['title'][:50]}")
    print(f"\n페이지 {args.page}/{pages} (총 {total}건)")


def cmd_show(args, cfg, conn):
    r = db.get_clean_by_id(conn, args.id)
    if not r:
        log.error("ID=%s 기사가 없습니다.", args.id); return
    print(f"[{r['id']}] {r['title']}")
    print(f"날짜: {r['published_at']} | 카테고리: {r['category']} | 소스: {r['source']} ({r['method']}) | 상태: {r['status']}")
    print(f"URL: {r['url']}\n")
    print("본문:", r["body"][:500] + ("..." if len(r["body"]) > 500 else ""))
    if r.get("summary"):
        print(f"\n요약: {r['summary']}\n키워드: {r['keywords']}\n감성: {r['sentiment']}")


# ---------- 파서 ----------
def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="news_pipeline", description="뉴스 자동 수집·AI 요약·인사이트 분석 CLI")
    sub = p.add_subparsers(dest="command", required=True)

    f = sub.add_parser("fetch", help="뉴스 수집 (RSS/크롤링) → raw 저장")
    f.add_argument("--source", choices=["rss", "crawl", "all"], default="all")
    f.add_argument("--category", default=None)
    f.add_argument("--limit", type=int, default=20, help="소스당 최대 건수 (기본 20)")
    f.set_defaults(func=cmd_fetch)

    c = sub.add_parser("clean", help="raw → clean 정제")
    c.add_argument("--limit", type=int, default=None)
    c.set_defaults(func=cmd_clean)

    s = sub.add_parser("summarize", help="AI 요약")
    g = s.add_mutually_exclusive_group()
    g.add_argument("--all", action="store_true", help="전체 대상")
    g.add_argument("--id", type=int, help="특정 기사 1건")
    g.add_argument("--unsummarized", action="store_true", help="미요약 기사만 (기본)")
    s.add_argument("--limit", type=int, default=10)
    s.add_argument("--force", action="store_true", help="이미 요약된 기사도 재요약")
    s.set_defaults(func=cmd_summarize)

    a = sub.add_parser("analyze", help="AI 인사이트 분석")
    a.add_argument("--date-from", dest="date_from", default=None)
    a.add_argument("--date-to", dest="date_to", default=None)
    a.add_argument("--category", default=None)
    a.set_defaults(func=cmd_analyze)

    r = sub.add_parser("report", help="차트 + 리포트 생성")
    r.add_argument("--out", default=None)
    r.add_argument("--format", choices=["md", "txt"], default="md")
    r.set_defaults(func=cmd_report)

    e = sub.add_parser("export", help="데이터 내보내기")
    e.add_argument("--format", choices=["csv", "xlsx", "jsonl"], default="csv")
    e.add_argument("--status", choices=["clean", "summarized"], default=None)
    e.add_argument("--category", default=None)
    e.add_argument("--date-from", dest="date_from", default=None)
    e.add_argument("--date-to", dest="date_to", default=None)
    e.add_argument("--out", default=None)
    e.set_defaults(func=cmd_export)

    l = sub.add_parser("list", help="(보너스) 뉴스 목록 조회")
    l.add_argument("--category", default=None)
    l.add_argument("--date-from", dest="date_from", default=None)
    l.add_argument("--date-to", dest="date_to", default=None)
    l.add_argument("--keyword", default=None)
    l.add_argument("--page", type=int, default=1)
    l.add_argument("--page-size", dest="page_size", type=int, default=10)
    l.set_defaults(func=cmd_list)

    sh = sub.add_parser("show", help="(보너스) 뉴스 상세 조회")
    sh.add_argument("--id", type=int, required=True)
    sh.set_defaults(func=cmd_show)
    return p


def main():
    cfg = load_config()
    setup_logging(cfg.get("log_level", "INFO"))
    conn = db.get_conn(cfg["db_path"])
    db.init_db(conn)
    args = build_parser().parse_args()
    try:
        args.func(args, cfg, conn)
    except Exception as e:  # noqa: BLE001
        log.error("실행 실패: %s", e, exc_info=cfg.get("log_level") == "DEBUG")
        sys.exit(1)
    finally:
        conn.close()


if __name__ == "__main__":
    main()
