"""AI 요약(summarize) / 인사이트 분석(analyze) / 감성(보너스).

담당: 팀원 C
"""
import logging

import db
from ai_client import call_json

log = logging.getLogger(__name__)

SUMMARY_SYSTEM = (
    "당신은 뉴스 요약 전문가입니다. 반드시 아래 JSON 형식으로만 답하고, 다른 텍스트나 마크다운 코드펜스를 붙이지 마세요.\n"
    '{"summary": "3문장 이내 한국어 요약", "keywords": ["키워드1","키워드2","키워드3"], '
    '"sentiment": "positive|negative|neutral"}'
)

ANALYSIS_SYSTEM = (
    "당신은 산업 트렌드 분석가입니다. 여러 뉴스를 종합해 아래 JSON 형식으로만 답하세요.\n"
    '{"trends": ["주요 트렌드 3~5개"], "keywords": ["핵심 키워드 5~10개"], '
    '"common_points": ["공통점 2~3개"], "differences": ["차이점 2~3개"], '
    '"issues": ["주요 이슈 3개"], "implications": "시사점 3~5문장"}'
)


def summarize_one(conn, article: dict, cfg: dict) -> bool:
    max_chars = cfg["ai"].get("max_body_chars", 3000)
    user = f"[제목] {article['title']}\n[본문] {article['body'][:max_chars]}"
    res = call_json(SUMMARY_SYSTEM, user, cfg)
    if not res or not res.get("summary"):
        return False
    db.save_summary(conn, article["id"], res["summary"], res.get("keywords", []),
                    res.get("sentiment"), cfg["ai"]["model"])
    log.info("ID=%s 요약 완료 (%d자 → %d자)", article["id"], len(article["body"]), len(res["summary"]))
    return True


def analyze_range(conn, date_from, date_to, category, cfg: dict) -> dict | None:
    rows = db.get_clean(conn, category=category, date_from=date_from, date_to=date_to)
    if not rows:
        log.warning("분석 대상 기사가 없습니다.")
        return None
    rows = rows[: cfg["ai"].get("max_articles_for_analysis", 60)]
    lines = [f"기간: {date_from} ~ {date_to}, 카테고리: {category or '전체'}, 기사 수: {len(rows)}"]
    for i, r in enumerate(rows, 1):
        lines.append(f"{i}. [{r['title']}] {r.get('summary') or r['body'][:300]}")
    res = call_json(ANALYSIS_SYSTEM, "\n".join(lines), cfg)
    if not res:
        return None
    db.save_analysis(conn, {"date_from": date_from, "date_to": date_to, "category": category,
                            "article_count": len(rows)}, res, cfg["ai"]["model"])
    return res


def format_analysis(res: dict) -> str:
    """콘솔·리포트 공용 출력 형식."""
    out = ["=== AI 인사이트 분석 결과 ==="]
    def sec(title, items):
        if items:
            out.append(f"[{title}]")
            out.extend(f"- {x}" for x in items) if isinstance(items, list) else out.append(str(items))
    sec("주요 트렌드", res.get("trends"))
    if res.get("keywords"):
        out.append("[핵심 키워드]"); out.append(", ".join(res["keywords"]))
    sec("공통점", res.get("common_points"))
    sec("차이점", res.get("differences"))
    sec("주요 이슈", res.get("issues"))
    sec("시사점", res.get("implications"))
    return "\n".join(out)
