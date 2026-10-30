"""시각화(matplotlib), 리포트(품질지표·TOP N·AI 인사이트), 내보내기(csv/xlsx/jsonl).

담당: 팀원 D (김범근). 통합: 김성태 (함수 인자를 main.py 계약에 맞춤).
- chart_by_category(rows, out_path) / chart_by_date(rows, out_path) -> 저장 경로
- build_report(conn, cfg) -> 리포트 본문(MD 문자열). 파일 저장은 main.py 가 한다.
- export_data(rows, fmt, out_path) -> 저장 경로
"""
import logging
import os
import platform
from collections import Counter
from datetime import datetime

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import pandas as pd  # noqa: E402

import db  # noqa: E402
from analyzer import format_analysis  # noqa: E402

log = logging.getLogger(__name__)


def set_korean_font() -> None:
    """OS 별 한글 폰트 후보 중 설치된 첫 폰트를 사용한다."""
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


def _to_dataframe(rows) -> pd.DataFrame:
    return pd.DataFrame(rows) if rows else pd.DataFrame()


# ---------- 차트 ----------
def chart_by_category(rows: list, out_path: str) -> str:
    """카테고리별 뉴스 수 막대그래프."""
    set_korean_font()
    df = _to_dataframe(rows)
    if df.empty or "category" not in df.columns:
        raise ValueError("시각화할 뉴스 데이터가 없습니다.")

    categories = df["category"].fillna("미분류").replace("", "미분류").value_counts()
    fig, ax = plt.subplots(figsize=(9, 5))
    ax.bar(categories.index, categories.values)
    ax.set_title("카테고리별 뉴스 수")
    ax.set_xlabel("카테고리")
    ax.set_ylabel("뉴스 수")
    plt.xticks(rotation=30, ha="right")
    plt.tight_layout()
    plt.savefig(out_path, dpi=150)
    plt.close()
    return out_path


def chart_by_date(rows: list, out_path: str) -> str:
    """일자별 뉴스 수집 추이 선그래프."""
    set_korean_font()
    df = _to_dataframe(rows)
    if df.empty or "published_at" not in df.columns:
        raise ValueError("시각화할 뉴스 데이터가 없습니다.")

    df = df.copy()
    df["published_at"] = pd.to_datetime(df["published_at"], errors="coerce")
    df = df.dropna(subset=["published_at"])
    daily = df.groupby(df["published_at"].dt.date).size().sort_index()

    fig, ax = plt.subplots(figsize=(9, 5))
    ax.plot([str(d) for d in daily.index], daily.values, marker="o")
    ax.set_title("일자별 뉴스 수집 추이")
    ax.set_xlabel("날짜")
    ax.set_ylabel("뉴스 수")
    plt.xticks(rotation=30, ha="right")
    plt.tight_layout()
    plt.savefig(out_path, dpi=150)
    plt.close()
    return out_path


# ---------- 리포트 ----------
def _pct(a: int, b: int) -> str:
    return f"{a / b * 100:.1f}%" if b else "n/a"


def build_report(conn, cfg: dict) -> str:
    """품질지표, TOP N, 차트, AI 인사이트를 포함한 Markdown 리포트 본문을 만든다."""
    rows = db.get_clean(conn)
    st = db.stats(conn)
    out_dir = cfg["output_dir"]
    df = _to_dataframe(rows)

    lines = [
        f"# AI 뉴스 트렌드 분석 리포트 (생성: {datetime.now():%Y-%m-%d %H:%M})",
        "",
        "## 1. 수집 현황",
        f"- raw {st['raw']}건 / clean {st['clean']}건 / 요약 {st['summarized']}건",
        "",
        "## 2. 품질 지표",
        f"- 본문 결측률: {_pct(st['raw_no_body'], st['raw'])} ({st['raw_no_body']}/{st['raw']})",
        f"- 정제 통과율: {_pct(st['clean'], st['raw'])} ({st['clean']}/{st['raw']})",
        f"- AI 요약 완료율: {_pct(st['summarized'], st['clean'])} ({st['summarized']}/{st['clean']})",
        "",
        "## 3. TOP N 집계",
    ]

    if df.empty:
        lines.append("- 리포트를 생성할 뉴스 데이터가 없습니다. fetch → clean 을 먼저 실행하세요.")
    else:
        top_cat = df["category"].fillna("미분류").replace("", "미분류").value_counts().head(5)
        lines.append("### 카테고리별 기사 수 TOP 5")
        lines += [f"{i}. {c}: {n}건" for i, (c, n) in enumerate(top_cat.items(), 1)]

        kws = Counter(
            k.strip() for r in rows if r.get("keywords")
            for k in str(r["keywords"]).split(",") if k.strip()
        )
        if kws:
            lines += ["", "### 키워드 빈도 TOP 10"]
            lines += [f"{i}. {k}: {n}회" for i, (k, n) in enumerate(kws.most_common(10), 1)]

        sentiments = Counter(r["sentiment"] for r in rows if r.get("sentiment"))
        if sentiments:
            lines += ["", "### 감성 분포"]
            lines += [f"- {s}: {n}건" for s, n in sentiments.most_common()]

        p1 = chart_by_category(rows, os.path.join(out_dir, "chart_category.png"))
        p2 = chart_by_date(rows, os.path.join(out_dir, "chart_daily.png"))
        lines += [
            "", "## 4. 시각화",
            f"![카테고리별 뉴스 수]({os.path.basename(p1)})",
            f"![일자별 뉴스 수집 추이]({os.path.basename(p2)})",
        ]

    latest = db.get_latest_analysis(conn)
    lines += ["", "## 5. AI 인사이트 분석"]
    if latest:
        lines.append(
            f"(기간 {latest['date_from'] or '전체'} ~ {latest['date_to'] or '전체'}, "
            f"카테고리 {latest['category'] or '전체'}, {latest['article_count']}건, 모델 {latest['model']})"
        )
        lines.append(format_analysis(latest["result"]))
    else:
        lines.append("AI 분석 결과가 없습니다. analyze 를 먼저 실행하세요.")
    return "\n".join(lines)


# ---------- 내보내기 ----------
def export_data(rows: list, fmt: str, out_path: str) -> str:
    """뉴스 데이터를 csv / xlsx / jsonl 로 저장한다. 필터링은 호출 전에 db.get_clean 으로 끝낸다."""
    df = _to_dataframe(rows)
    fmt = fmt.lower()
    if fmt == "csv":
        df.to_csv(out_path, index=False, encoding="utf-8-sig")
    elif fmt in ("xlsx", "excel"):
        df.to_excel(out_path, index=False)
    elif fmt == "jsonl":
        df.to_json(out_path, orient="records", lines=True, force_ascii=False)
    else:
        raise ValueError("지원하지 않는 형식입니다. csv, xlsx, jsonl 중 하나를 사용하세요.")
    return out_path
