import platform
from pathlib import Path

import matplotlib.pyplot as plt
import pandas as pd


OUTPUT_DIR = Path("output")


def set_korean_font():
    """운영체제에 맞는 한글 폰트를 설정한다."""
    system = platform.system()

    if system == "Darwin":       # macOS
        plt.rc("font", family="AppleGothic")
    elif system == "Windows":
        plt.rc("font", family="Malgun Gothic")
    else:
        plt.rc("font", family="NanumGothic")

    # 그래프에서 - 기호가 깨지는 현상 방지
    plt.rcParams["axes.unicode_minus"] = False


def _to_dataframe(rows):
    """뉴스 목록을 pandas DataFrame으로 바꾼다."""
    if not rows:
        return pd.DataFrame()

    return pd.DataFrame(rows)


def chart_by_category(rows, output_dir=OUTPUT_DIR):
    """카테고리별 뉴스 개수 막대그래프를 생성한다."""
    set_korean_font()

    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    df = _to_dataframe(rows)

    if df.empty:
        raise ValueError("시각화할 뉴스 데이터가 없습니다.")

    if "category" not in df.columns:
        raise ValueError("뉴스 데이터에 category 컬럼이 없습니다.")

    categories = (
        df["category"]
        .fillna("미분류")
        .replace("", "미분류")
        .value_counts()
    )

    fig, ax = plt.subplots(figsize=(9, 5))

    ax.bar(categories.index, categories.values)

    ax.set_title("카테고리별 뉴스 수")
    ax.set_xlabel("카테고리")
    ax.set_ylabel("뉴스 수")

    plt.xticks(rotation=30, ha="right")
    plt.tight_layout()

    path = output_dir / "chart_category.png"
    plt.savefig(path, dpi=150)
    plt.close()

    return path


def chart_by_date(rows, output_dir=OUTPUT_DIR):
    """날짜별 뉴스 수집 추이 선그래프를 생성한다."""
    set_korean_font()

    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    df = _to_dataframe(rows)

    if df.empty:
        raise ValueError("시각화할 뉴스 데이터가 없습니다.")

    if "published_at" not in df.columns:
        raise ValueError("뉴스 데이터에 published_at 컬럼이 없습니다.")

    df["published_at"] = pd.to_datetime(
        df["published_at"],
        errors="coerce"
    )

    df = df.dropna(subset=["published_at"])

    daily_counts = (
        df.groupby(df["published_at"].dt.date)
        .size()
        .sort_index()
    )

    fig, ax = plt.subplots(figsize=(9, 5))

    ax.plot(
        [str(date) for date in daily_counts.index],
        daily_counts.values,
        marker="o"
    )

    ax.set_title("일자별 뉴스 수집 추이")
    ax.set_xlabel("날짜")
    ax.set_ylabel("뉴스 수")

    plt.xticks(rotation=30, ha="right")
    plt.tight_layout()

    path = output_dir / "chart_daily.png"
    plt.savefig(path, dpi=150)
    plt.close()

    return path


def build_report(rows, analysis=None, output_dir=OUTPUT_DIR):
    """품질지표, TOP N, AI 인사이트를 포함한 Markdown 리포트를 만든다."""
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    df = _to_dataframe(rows)

    if df.empty:
        raise ValueError("리포트를 생성할 뉴스 데이터가 없습니다.")

    total_count = len(df)

    # 품질지표 1: 본문 존재율
    if "body" in df.columns:
        content_count = (
            df["body"]
            .fillna("")
            .astype(str)
            .str.strip()
            .ne("")
            .sum()
        )
    else:
        content_count = 0

    content_rate = (
        content_count / total_count * 100
        if total_count
        else 0
    )

    # 품질지표 2: AI 요약 완료율
    if "summary" in df.columns:
        summary_count = (
            df["summary"]
            .fillna("")
            .astype(str)
            .str.strip()
            .ne("")
            .sum()
        )
    else:
        summary_count = 0

    summary_rate = (
        summary_count / total_count * 100
        if total_count
        else 0
    )

    # TOP 5 카테고리
    if "category" in df.columns:
        top_categories = (
            df["category"]
            .fillna("미분류")
            .replace("", "미분류")
            .value_counts()
            .head(5)
        )
    else:
        top_categories = pd.Series(dtype=int)

    lines = [
        "# AI 뉴스 트렌드 분석 리포트",
        "",
        f"- 총 뉴스 수: **{total_count}건**",
        "",
        "## 1. 품질 지표",
        "",
        f"- 본문 존재율: **{content_rate:.1f}%** "
        f"({content_count}/{total_count})",
        f"- AI 요약 완료율: **{summary_rate:.1f}%** "
        f"({summary_count}/{total_count})",
        "",
        "## 2. 카테고리 TOP 5",
        "",
    ]

    if top_categories.empty:
        lines.append("- 카테고리 데이터 없음")
    else:
        for rank, (category, count) in enumerate(
            top_categories.items(),
            start=1
        ):
            lines.append(f"{rank}. {category}: {count}건")

    lines.extend(
        [
            "",
            "## 3. AI 인사이트 분석",
            "",
        ]
    )

    if isinstance(analysis, dict):
        trends = analysis.get("trends", [])
        keywords = analysis.get("keywords", [])
        issues = analysis.get("issues", [])
        implications = analysis.get("implications", [])

        lines.append("### 주요 트렌드")
        lines.append("")

        if isinstance(trends, list):
            for item in trends:
                lines.append(f"- {item}")
        elif trends:
            lines.append(str(trends))

        lines.extend(["", "### 핵심 키워드", ""])

        if isinstance(keywords, list):
            lines.append(", ".join(map(str, keywords)))
        elif keywords:
            lines.append(str(keywords))

        lines.extend(["", "### 주요 이슈", ""])

        if isinstance(issues, list):
            for item in issues:
                lines.append(f"- {item}")
        elif issues:
            lines.append(str(issues))

        lines.extend(["", "### 시사점", ""])

        if isinstance(implications, list):
            for item in implications:
                lines.append(f"- {item}")
        elif implications:
            lines.append(str(implications))

    elif analysis:
        lines.append(str(analysis))

    else:
        lines.append("AI 분석 결과가 없습니다.")

    lines.extend(
        [
            "",
            "## 4. 시각화",
            "",
            "### 카테고리별 뉴스 수",
            "",
            "![카테고리별 뉴스 수](chart_category.png)",
            "",
            "### 일자별 뉴스 수집 추이",
            "",
            "![일자별 뉴스 수집 추이](chart_daily.png)",
            "",
        ]
    )

    report_path = output_dir / "report.md"

    report_path.write_text(
        "\n".join(lines),
        encoding="utf-8"
    )

    return report_path


def export_data(
    rows,
    file_format,
    status=None,
    category=None,
    output_dir=OUTPUT_DIR
):
    """뉴스 데이터를 CSV / Excel / JSONL로 내보낸다."""
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    df = _to_dataframe(rows)

    if df.empty:
        raise ValueError("내보낼 뉴스 데이터가 없습니다.")

    # 상태 필터
    if status and "status" in df.columns:
        df = df[df["status"] == status]

    # 카테고리 필터
    if category and "category" in df.columns:
        df = df[df["category"] == category]

    file_format = file_format.lower()

    if file_format == "csv":
        path = output_dir / "news.csv"

        df.to_csv(
            path,
            index=False,
            encoding="utf-8-sig"
        )

    elif file_format in ("excel", "xlsx"):
        path = output_dir / "news.xlsx"

        df.to_excel(
            path,
            index=False
        )

    elif file_format == "jsonl":
        path = output_dir / "news.jsonl"

        df.to_json(
            path,
            orient="records",
            lines=True,
            force_ascii=False
        )

    else:
        raise ValueError(
            "지원하지 않는 형식입니다. "
            "csv, excel, jsonl 중 하나를 사용하세요."
        )

    return path