"""시각화(matplotlib), 리포트(품질지표·TOP N·AI 인사이트), 내보내기(csv/xlsx/jsonl).

담당: 팀원 D
"""
import logging
import os
import platform
from collections import Counter
from datetime import datetime

import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

import db  # noqa: E402
from analyzer import format_analysis  # noqa: E402

log = logging.getLogger(__name__)


def set_korean_font() -> None:
    """OS 별 한글 폰트 후보 중 설치된 첫 폰트를 사용한다. 없으면 경고만 남긴다."""
    from matplotlib import font_manager
    candidates = {
        "Windows": ["Malgun Gothic", "NanumGothic"],
        "Darwin": ["AppleGothic", "NanumGothic"],
    }.get(platform.system(), ["NanumGothic", "NanumBarunGothic", "Noto Sans CJK KR", "Noto Sans KR"])
    installed = {f.name for f in font_manager.fontManager.ttflist}
    for name in candidates:
        if name in installed:
            plt.rc("font", family=name)
            break
    else:
        log.warning("한글 폰트를 찾지 못했습니다. Linux 는 fonts-nanum 설치 후 ~/.cache/matplotlib 삭제")
    plt.rcParams["axes.unicode_minus"] = False


def chart_by_category(rows: list, out_path: str) -> str:
    set_korean_font()
    s = pd.DataFrame(rows)["category"].value_counts()
    plt.figure(figsize=(7, 4)); s.plot(kind="bar"); plt.title("카테고리별 뉴스 수"); plt.ylabel("건수")
    plt.tight_layout(); plt.savefig(out_path, dpi=120); plt.close()
    return out_path


def chart_by_date(rows: list, out_path: str) -> str:
    set_korean_font()
    s = pd.DataFrame(rows).groupby("published_at").size().sort_index()
    plt.figure(figsize=(7, 4)); s.plot(marker="o"); plt.title("일자별 수집 추이"); plt.ylabel("건수")
    plt.xticks(rotation=45); plt.tight_layout(); plt.savefig(out_path, dpi=120); plt.close()
    return out_path


def build_report(conn, cfg: dict) -> str:
    rows = db.get_clean(conn)
    st = db.stats(conn)
    out_dir = cfg["output_dir"]
    lines = [f"# 뉴스 인사이트 리포트 (생성: {datetime.now():%Y-%m-%d %H:%M})", ""]
    lines += ["## 1. 수집 현황", f"- raw {st['raw']}건 / clean {st['clean']}건 / 요약 {st['summarized']}건", ""]

    def pct(a, b):
        return f"{(a / b * 100):.1f}%" if b else "n/a"
    lines += ["## 2. 품질 지표",
              f"- 본문 결측률: {pct(st['raw_no_body'], st['raw'])}",
              f"- 정제 통과율: {pct(st['clean'], st['raw'])}",
              f"- 요약 완료율: {pct(st['summarized'], st['clean'])}", ""]

    if rows:
        cat = Counter(r["category"] for r in rows).most_common(5)
        lines += ["## 3. TOP N 집계", "### 카테고리별 기사 수 TOP 5"]
        lines += [f"- {c}: {n}건" for c, n in cat]
        kws = Counter(k.strip() for r in rows if r.get("keywords") for k in r["keywords"].split(",") if k.strip())
        if kws:
            lines += ["### 키워드 빈도 TOP 10"] + [f"- {k}: {n}" for k, n in kws.most_common(10)]
        lines.append("")
        p1 = chart_by_category(rows, os.path.join(out_dir, "chart_category.png"))
        p2 = chart_by_date(rows, os.path.join(out_dir, "chart_daily.png"))
        lines += ["## 4. 차트", f"![카테고리]({os.path.basename(p1)})", f"![일자별]({os.path.basename(p2)})", ""]

    latest = db.get_latest_analysis(conn)
    lines += ["## 5. AI 인사이트"]
    if latest:
        lines.append(f"(기간 {latest['date_from']} ~ {latest['date_to']}, 카테고리 {latest['category'] or '전체'}, {latest['article_count']}건)")
        lines.append(format_analysis(latest["result"]))
    else:
        lines.append("아직 analyze 를 실행하지 않았습니다.")
    return "\n".join(lines)


def export_data(rows: list, fmt: str, out_path: str) -> str:
    df = pd.DataFrame(rows)
    if fmt == "csv":
        df.to_csv(out_path, index=False, encoding="utf-8-sig")
    elif fmt == "xlsx":
        df.to_excel(out_path, index=False)
    elif fmt == "jsonl":
        df.to_json(out_path, orient="records", lines=True, force_ascii=False)
    else:
        raise ValueError(f"지원하지 않는 포맷: {fmt}")
    return out_path
