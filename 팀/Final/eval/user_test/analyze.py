"""10분 사용자 테스트 결과를 요약합니다. 표준 라이브러리만 사용합니다."""
import csv
import statistics
import sys
from pathlib import Path


def as_float(v):
    try:
        return float(v)
    except (TypeError, ValueError):
        return None


def as_bool(v):
    return str(v).strip().lower() in {"1", "true", "yes", "y", "정답", "o"}


def mean(values):
    xs = [x for x in values if x is not None]
    return sum(xs) / len(xs) if xs else None


def fmt(x, digits=1):
    return "-" if x is None else f"{x:.{digits}f}"


def main(path):
    with open(path, encoding="utf-8-sig", newline="") as f:
        rows = list(csv.DictReader(f))

    quant = [r for r in rows if str(r.get("quantitative", "1")).strip() not in {"0", "false", "False"}]
    st = [as_float(r.get("service_seconds")) for r in quant]
    bt = [as_float(r.get("baseline_seconds")) for r in quant]
    st = [x for x in st if x is not None]
    bt = [x for x in bt if x is not None]

    paired = []
    for r in quant:
        s, b = as_float(r.get("service_seconds")), as_float(r.get("baseline_seconds"))
        if s is not None and b is not None:
            paired.append(b - s)

    service_acc = mean([1.0 if as_bool(r.get("service_correct")) else 0.0 for r in quant if r.get("service_correct") != ""])
    base_acc = mean([1.0 if as_bool(r.get("baseline_correct")) else 0.0 for r in quant if r.get("baseline_correct") != ""])

    print("# 사용자 테스트 결과")
    print()
    print(f"- 전체 참여자: {len(rows)}명")
    print(f"- 정량 분석 포함: {len(quant)}명")
    print(f"- 서비스 소요시간 중앙값: {fmt(statistics.median(st) if st else None)}초")
    print(f"- 직접검색 소요시간 중앙값: {fmt(statistics.median(bt) if bt else None)}초")
    print(f"- 개인별 시간 절감 중앙값: {fmt(statistics.median(paired) if paired else None)}초")
    print(f"- 서비스 정답률: {fmt(service_acc * 100 if service_acc is not None else None)}%")
    print(f"- 직접검색 정답률: {fmt(base_acc * 100 if base_acc is not None else None)}%")
    for col, label in [
        ("understanding_1_5", "이해도"),
        ("trust_1_5", "신뢰도"),
        ("interview_use_1_5", "면접 활용 의향"),
    ]:
        print(f"- {label} 평균: {fmt(mean([as_float(r.get(col)) for r in rows]))}/5")

    feedback = [r.get("feedback", "").strip() for r in rows if r.get("feedback", "").strip()]
    if feedback:
        print("\n## 개선 의견")
        for x in feedback:
            print(f"- {x}")


if __name__ == "__main__":
    if len(sys.argv) != 2:
        raise SystemExit("사용법: python eval/user_test/analyze.py <results.csv>")
    p = Path(sys.argv[1])
    if not p.exists():
        raise SystemExit(f"파일이 없습니다: {p}")
    main(p)
