"""Google Drive의 10분 사용자 테스트 기록지를 요약합니다.

핵심 원칙
- 본 테스트 + 동의한 참가자만 정량 분석
- R0 예행연습, 의견 참여는 정량 분석 제외
- 주 지표: 4분 안에 정답을 찾은 비율
- 시간은 4분 안에 완료한 사례만 요약
- 4분 제한으로 censored 된 값을 이용해 '몇 분 단축'을 계산하지 않음
"""
import csv
import statistics
import sys
from collections import Counter
from pathlib import Path


YES = {"1", "true", "yes", "y", "예", "네", "o", "정답", "맞음"}
NO = {"0", "false", "no", "n", "아니오", "아니요", "x", "오답", "틀림"}


def norm(v):
    return str(v or "").strip()


def as_float(v):
    try:
        return float(norm(v))
    except (TypeError, ValueError):
        return None


def as_bool(v):
    s = norm(v).lower()
    if s in YES:
        return True
    if s in NO:
        return False
    return None


def mean(values):
    xs = [x for x in values if x is not None]
    return sum(xs) / len(xs) if xs else None


def pct(x):
    return "-" if x is None else f"{x * 100:.1f}%"


def fmt(x, digits=1):
    return "-" if x is None else f"{x:.{digits}f}"


def is_main_test(r):
    return norm(r.get("구분")) == "본 테스트" and as_bool(r.get("동의")) is True


def valid_quant(r):
    """두 과제 모두 '4분 안에 끝냄'이 적혀 있어야 하고, 정답 칸은 4분 안에 끝낸 과제에만 필요합니다.
    시간 초과(끝냄=아니오)면 정답 칸이 비어 있어도 '실패'로 셉니다. (빈칸이라고 빼면 시간 초과가 빠져 성공률이 부풀려짐)"""
    if not is_main_test(r):
        return False
    for prefix in ("서비스", "직접 검색"):
        finished = as_bool(r.get(f"{prefix} 4분 안에 끝냄"))
        if finished is None:
            return False
        if finished and as_bool(r.get(f"{prefix} 정답")) is None:
            return False
    return True


def success(r, prefix):
    finished = as_bool(r.get(f"{prefix} 4분 안에 끝냄"))
    correct = as_bool(r.get(f"{prefix} 정답"))
    return finished is True and correct is True


def completed_time(r, prefix):
    finished = as_bool(r.get(f"{prefix} 4분 안에 끝냄"))
    t = as_float(r.get(f"{prefix} 걸린 시간(초)"))
    if finished is True and t is not None:
        return t
    return None


def summarize_times(rows, prefix):
    xs = [completed_time(r, prefix) for r in rows]
    xs = [x for x in xs if x is not None]
    return {
        "n": len(xs),
        "mean": mean(xs),
        "median": statistics.median(xs) if xs else None,
        "min": min(xs) if xs else None,
        "max": max(xs) if xs else None,
    }


def survey_mean(rows, col):
    return mean([as_float(r.get(col)) for r in rows])


def print_times(label, s):
    print(
        f"- {label} 완료자 시간: n={s['n']}, "
        f"평균 {fmt(s['mean'])}초, 중앙값 {fmt(s['median'])}초 "
        f"(범위 {fmt(s['min'])}~{fmt(s['max'])}초)"
    )


def main(path):
    with open(path, encoding="utf-8-sig", newline="") as f:
        rows = list(csv.DictReader(f))

    main_rows = [r for r in rows if is_main_test(r)]
    quant = [r for r in rows if valid_quant(r)]
    pilot = [r for r in rows if norm(r.get("구분")) == "예행연습"]
    opinion = [r for r in rows if norm(r.get("구분")) == "의견 참여"]

    service_success = mean([1.0 if success(r, "서비스") else 0.0 for r in quant])
    baseline_success = mean([1.0 if success(r, "직접 검색") else 0.0 for r in quant])

    service_times = summarize_times(quant, "서비스")
    baseline_times = summarize_times(quant, "직접 검색")

    service_timeout = sum(as_bool(r.get("서비스 4분 안에 끝냄")) is False for r in quant)
    baseline_timeout = sum(as_bool(r.get("직접 검색 4분 안에 끝냄")) is False for r in quant)

    service_correct = mean([
        1.0 if as_bool(r.get("서비스 정답")) is True else 0.0
        for r in quant
        if as_bool(r.get("서비스 정답")) is not None
    ])
    baseline_correct = mean([
        1.0 if as_bool(r.get("직접 검색 정답")) is True else 0.0
        for r in quant
        if as_bool(r.get("직접 검색 정답")) is not None
    ])

    order = Counter(norm(r.get("과제1 방식")) or "미기록" for r in quant)
    tools = Counter(norm(r.get("직접 검색 쓴 도구")) for r in quant if norm(r.get("직접 검색 쓴 도구")))

    survey_rows = main_rows + opinion

    print("# 사용자 테스트 결과")
    print()
    print("## 표본")
    print(f"- 기록된 전체 행: {len(rows)}")
    print(f"- 본 테스트 + 동의: {len(main_rows)}명")
    print(f"- 정량 분석 가능: {len(quant)}명")
    print(f"- 예행연습: {len(pilot)}명 (정량 제외)")
    print(f"- 의견 참여: {len(opinion)}명 (정량 제외)")
    print()

    print("## 주 지표: 4분 안에 정답 찾기")
    print(f"- AI Promise: {pct(service_success)} ({sum(success(r, '서비스') for r in quant)}/{len(quant) if quant else 0})")
    print(f"- 직접 검색: {pct(baseline_success)} ({sum(success(r, '직접 검색') for r in quant)}/{len(quant) if quant else 0})")
    if service_success is not None and baseline_success is not None:
        print(f"- 성공률 차이: {(service_success - baseline_success) * 100:+.1f}%p")
    print()

    print("## 보조 지표")
    print(f"- 서비스 정답률(시간 제한과 별도): {pct(service_correct)}")
    print(f"- 직접검색 정답률(시간 제한과 별도): {pct(baseline_correct)}")
    print(f"- 서비스 시간 초과: {service_timeout}/{len(quant) if quant else 0}")
    print(f"- 직접검색 시간 초과: {baseline_timeout}/{len(quant) if quant else 0}")
    print_times("서비스", service_times)
    print_times("직접검색", baseline_times)
    print("- 주의: 4분에서 중단된 참가자가 있으므로 '몇 분 단축' 같은 paired time-saved 수치는 계산하지 않습니다.")
    print()

    print("## 순서 배정")
    for k, v in order.items():
        print(f"- {k}: {v}명")
    if tools:
        print("\n## 직접 검색 도구")
        for k, v in tools.most_common():
            print(f"- {k}: {v}명")

    # 설문 점수는 본 테스트 참가자와 의견 참여를 섞지 않습니다 (과제를 한 조건이 달라서)
    print("\n## 설문")
    for col, label in [
        ("설문1 이해(1~5)", "이해도"),
        ("설문2 신뢰(1~5)", "신뢰도"),
        ("설문3 활용 의향(1~5)", "면접 활용 의향"),
    ]:
        line = f"- {label} 평균: 본 테스트 {fmt(survey_mean(main_rows, col))}/5"
        if opinion:
            line += f", 의견 참여(참고) {fmt(survey_mean(opinion, col))}/5"
        print(line)

    feedback = [norm(r.get("설문4 개선 의견")) for r in survey_rows if norm(r.get("설문4 개선 의견"))]
    if feedback:
        print("\n## 개선 의견")
        for x in feedback:
            print(f"- {x}")

    if len(quant) < 6:
        print("\n## 해석 주의")
        print("- 정량 분석 표본이 6명 미만입니다. 결과를 탐색적 결과로만 제시하는 것이 안전합니다.")


if __name__ == "__main__":
    if len(sys.argv) != 2:
        raise SystemExit("사용법: python eval/user_test/analyze.py <기록지.csv>")
    p = Path(sys.argv[1])
    if not p.exists():
        raise SystemExit(f"파일이 없습니다: {p}")
    main(p)
