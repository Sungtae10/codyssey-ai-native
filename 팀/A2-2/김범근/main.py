import argparse
import json
from pathlib import Path

from report import (
    chart_by_category,
    chart_by_date,
    build_report,
    export_data,
)


NEWS_PATH = Path("data/sample_news.json")
ANALYSIS_PATH = Path("data/sample_analysis.json")


def load_news():
    with open(NEWS_PATH, "r", encoding="utf-8") as f:
        return json.load(f)


def load_analysis():
    if not ANALYSIS_PATH.exists():
        return None

    with open(ANALYSIS_PATH, "r", encoding="utf-8") as f:
        return json.load(f)


def cmd_report(args):
    rows = load_news()
    analysis = load_analysis()

    category_chart = chart_by_category(rows)
    daily_chart = chart_by_date(rows)
    report_path = build_report(rows, analysis)

    print("[INFO] 리포트 생성 완료")
    print(f"[INFO] {category_chart}")
    print(f"[INFO] {daily_chart}")
    print(f"[INFO] {report_path}")


def cmd_export(args):
    rows = load_news()

    path = export_data(
        rows=rows,
        file_format=args.format,
        status=args.status,
        category=args.category,
    )

    print(f"[INFO] 데이터 내보내기 완료: {path}")


def main():
    parser = argparse.ArgumentParser(
        description="AI 뉴스 분석 파이프라인"
    )

    subparsers = parser.add_subparsers(
        dest="command",
        required=True
    )

    # report
    report_parser = subparsers.add_parser(
        "report",
        help="시각화와 리포트를 생성합니다."
    )

    report_parser.set_defaults(
        func=cmd_report
    )

    # export
    export_parser = subparsers.add_parser(
        "export",
        help="뉴스 데이터를 파일로 내보냅니다."
    )

    export_parser.add_argument(
        "--format",
        choices=["csv", "excel", "jsonl"],
        required=True,
        help="내보낼 파일 형식"
    )

    export_parser.add_argument(
        "--status",
        help="상태별 필터 (예: summarized)"
    )

    export_parser.add_argument(
        "--category",
        help="카테고리별 필터"
    )

    export_parser.set_defaults(
        func=cmd_export
    )

    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()