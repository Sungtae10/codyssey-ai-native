"""
나만의 프롬프트 관리 프로그램 (Prompt Manager)
Codyssey AI 네이티브 과정 A1-1 | Python & Git 기초

이전 미션에서 만든 프롬프트를 한곳에 모아 추가, 조회, 검색, 즐겨찾기로 관리한다.
실행 방법: python prompt_manager.py
"""


# ============================================================
# 상수: 프로그램 전체에서 쓰는 고정 값
# ============================================================
CATEGORIES = ["텍스트 생성", "이미지 생성", "영상 생성", "페르소나", "자동화", "기타"]


# ============================================================
# 기본 데이터: 이전 미션에서 실제로 사용한 프롬프트 원문
# ============================================================
# B1-1 (GenAI 기초, ChatGPT에게 일 시키기): 논문 요약 시스템 프롬프트 v2
PAPER_LENS_V2 = """당신은 기술경영 분야 논문 리뷰 보조 연구원 "Paper Lens"입니다.

[목표] 사용자가 제공한 논문 텍스트를 읽고, 연구에 활용 가능한 형태로 핵심을 요약하며,
사용자의 CFM(Corporate Foresight Maturity)/기술경영 연구와의 접점을 적극 제안합니다.

[출력 형식]
- 기본 출력은 반드시 아래 5개 항목으로만 구성한다. 5개 항목 외 별도 섹션(예: '다음 행동')을 임의로 추가하지 않는다.
  추가 제안이 필요하면, 본 요약을 마친 뒤 "추가 제안을 원하시면 말씀해 주세요"라고 안내만 한다.
1. 연구 질문(RQ)
2. 방법론 (데이터/분석기법)
3. 핵심 발견 (3가지)
4. 기술경영(CFM) 연구와의 관련성
5. 한계 및 후속 연구 여지
- 각 항목은 핵심 위주로 3~5개 bullet 이내로 작성한다. (항목 간 길이 편차를 줄인다)

[안전장치]
- 핵심 정보(방법론, 표본 등)가 텍스트에서 누락된 것으로 보이면, 요약 전에 최대 3개까지 확인 질문을 한다.
- 원문에 근거가 없는데 단정하지 않는다.
- 정보가 원문에 없으면 "원문에 명시 없음"이라고 표기한다.

[추론 표시 규칙]
- 원문 초록에 직접 근거가 없는 모든 적용·확장·제안에는 예외 없이 문장 앞 또는 뒤에 [추론] 태그를 붙인다.
- 특히 4번(CFM 관련성)과 5번(후속 연구)에서 추론이 많아지므로, 사실 진술과 추론 진술을 한 문장 안에 섞지 않는다.

[사실 처리 규칙]
- 수치·통계·연도는 원문 그대로 인용하고, 불확실하면 "확인 필요"로 표기한다.
- 평가성 표현("우수한", "획기적인")은 쓰지 않고 사실만 기술한다.

[개인정보 규칙]
- 특정 개인의 실명을 출력에 포함하지 않는다. 사용자를 지칭할 때는 "사용자" 또는 "연구자"로 표현한다."""

# B1-1 (GenAI 기초): 논문 요약 입력 템플릿 (사용자 프롬프트)
PAPER_SUMMARY_TEMPLATE = """[업무 과업] 논문 핵심 요약
[원문] (논문 초록/본문 텍스트 붙여넣기)
[원하는 결과]
- 연구 질문(RQ)
- 방법론 (데이터/분석기법)
- 핵심 발견 3가지
- 내 연구(CFM/기술경영)와의 관련성
- 한계 및 후속 연구 여지
[톤] 간결, 학술적, 사실 위주
[금지] 원문에 없는 내용 추측 금지, 불확실하면 "원문에 명시 없음" 표기
[확인 질문 규칙] 텍스트가 잘려 핵심 정보가 빠졌으면 최대 3개까지 질문 후 요약 시작"""

# B1-2 (멀티모달 광고 제작): 씬1 키비주얼 이미지 프롬프트 (Gemini, 1차 버전)
KARIOS_SCENE1_IMAGE = """Cinematic wide shot, lone human silhouette seen from behind standing in a dark void,
overwhelmed by chaotic streams of glowing notification fragments and data particles
swirling around them, cinematic, minimal, deep navy (#0E1530) to warm amber (#D98324) gradient,
volumetric light, shallow depth of field, premium product film, clean, no text, 16:9"""

# B1-2 (멀티모달 광고 제작): Veo 영상 공통 스타일과 씬별 영상 프롬프트 (최종 버전)
VEO_STYLE = (
    "Style: cinematic tech commercial, premium and clean, deep navy blue (#0E1530) "
    "to warm amber (#D98324) color grade, volumetric light, shallow depth of field, "
    "smooth camera motion, modern minimal UI design, Apple-style product film. 16:9."
)

KARIOS_SCENE1_VIDEO = """A cinematic wide shot of a young professional sitting at a desk in a dark modern room,
overwhelmed and stressed, surrounded by dozens of glowing smartphone notification bubbles,
chat alerts, and calendar pop-ups swirling chaotically in the air around them.
The person holds their head, exhausted. Cold blue light mixed with chaotic colorful
notification glows. Slow push-in camera. Ambient tense electronic hum.
""" + VEO_STYLE

KARIOS_SCENE3_VIDEO = """A cinematic close-up of a user looking at their smartphone with a calm, relieved smile.
On the screen, the KARIOS AI app proactively displays a clean recommendation card that
gently slides up with a soft amber glow, a smart suggestion notification appearing
before the user even asks. Warm amber ambient light, cozy modern interior softly blurred
in the background. Gentle uplifting music.
""" + VEO_STYLE

# B2-2 (노코드 자동화 팀 프로젝트): Make 시나리오에서 Gemini에 보낸 뉴스 요약 프롬프트
FIFA_NEWS_SUMMARY = (
    "FIFA 2026 관련 뉴스를 한국어 3줄로만 요약해줘. 핵심만. "
    "제목: {{2.Title}} 내용: escapeJSON({{2.Description}})"
)


def make_prompt(title, content, category, favorite=False):
    """프롬프트 1개를 딕셔너리로 만든다.
    모든 프롬프트가 같은 키(제목, 내용, 카테고리, 즐겨찾기)를 갖도록 이 함수 한 곳에서만 만든다.
    """
    return {
        "title": title,
        "content": content,
        "category": category,
        "favorite": favorite,
    }


def create_default_prompts():
    """이전 미션(B1-1, B1-2, B2-2)에서 실제로 쓴 프롬프트 6개로 기본 목록을 만든다.
    '기타' 카테고리는 일부러 비워 두어 '프롬프트 없음' 안내를 바로 확인할 수 있게 했다.
    """
    return [
        make_prompt("Paper Lens 논문 리뷰 연구원 v2 (B1-1)", PAPER_LENS_V2, "페르소나", favorite=True),
        make_prompt("논문 핵심 요약 입력 템플릿 (B1-1)", PAPER_SUMMARY_TEMPLATE, "텍스트 생성"),
        make_prompt("KARIOS 씬1 키비주얼 (B1-2, Gemini)", KARIOS_SCENE1_IMAGE, "이미지 생성"),
        make_prompt("KARIOS 씬1 알림 과부하 영상 (B1-2, Veo)", KARIOS_SCENE1_VIDEO, "영상 생성"),
        make_prompt("KARIOS 씬3 AI 선제 추천 영상 (B1-2, Veo)", KARIOS_SCENE3_VIDEO, "영상 생성"),
        make_prompt("FIFA 2026 뉴스 3줄 요약 (B2-2, Make+Gemini)", FIFA_NEWS_SUMMARY, "자동화"),
    ]


# ============================================================
# 입력 도우미: 잘못된 입력을 걸러 내는 함수
# ============================================================
def input_text(message):
    """글자를 입력받는다. 비어 있거나 공백뿐이면 다시 입력받는다."""
    while True:
        text = input(message).strip()
        if text:
            return text
        print("  비어 있습니다. 다시 입력해 주세요.")


def to_number(text):
    """'3'처럼 숫자로만 된 글자는 정수 3으로 바꾸고, 아니면 None을 돌려준다."""
    text = text.strip()
    if text.isdecimal():
        return int(text)
    return None


def choose_category():
    """미리 정한 카테고리 중 하나를 번호로 고르거나, 새 이름을 직접 입력받는다."""
    print("\n카테고리 선택:")
    for number, category in enumerate(CATEGORIES, start=1):
        print(f"{number}) {category}")
    custom_number = len(CATEGORIES) + 1
    print(f"{custom_number}) 직접 입력")

    while True:
        number = to_number(input("선택: "))
        if number is not None and 1 <= number <= len(CATEGORIES):
            return CATEGORIES[number - 1]
        if number == custom_number:
            return input_text("새 카테고리 이름: ")
        print("  목록에 있는 번호를 골라 주세요.")


# ============================================================
# 출력 도우미: 화면에 보여 주는 모양을 한 곳에서 관리
# ============================================================
def print_title(title):
    """기능 화면의 제목 줄을 출력한다. 예: === 프롬프트 추가 ==="""
    print()
    print(f"=== {title} ===")


# ============================================================
# 필수 기능
# ============================================================
def add_prompt(prompts):
    """제목, 내용, 카테고리를 입력받아 새 프롬프트를 목록 끝에 추가한다. 즐겨찾기는 False로 시작한다."""
    print_title("프롬프트 추가")
    title = input_text("제목: ")
    content = input_text("내용: ")
    category = choose_category()
    prompts.append(make_prompt(title, content, category))
    print(f"\n'{title}' 프롬프트가 추가되었습니다! (현재 {len(prompts)}개)")


# ============================================================
# 메뉴와 프로그램 시작점
# ============================================================
def show_menu():
    """메인 메뉴를 출력한다."""
    print()
    print("=== 나만의 프롬프트 관리 ===")
    print("1. 프롬프트 추가")
    print("2. 프롬프트 목록")
    print("3. 카테고리별 조회")
    print("4. 프롬프트 검색")
    print("5. 프롬프트 상세 보기")
    print("6. 즐겨찾기 관리")
    print("7. 즐겨찾기 목록")
    print("0. 종료")


def main():
    """프로그램 시작점. 사용자가 0을 입력할 때까지 메뉴를 반복해서 보여 준다."""
    prompts = create_default_prompts()
    print(f"이전 미션 프롬프트 {len(prompts)}개를 불러왔습니다.")

    while True:
        show_menu()
        choice = input("선택: ").strip()

        if choice == "1":
            add_prompt(prompts)
        elif choice in ("2", "3", "4", "5", "6", "7"):
            print("아직 준비 중인 기능입니다.")
        elif choice == "0":
            print("\n프로그램을 종료합니다. 실행 중에 추가하거나 바꾼 내용은 초기화됩니다.")
            break
        else:
            print("잘못된 입력입니다. 메뉴에 있는 번호를 입력해 주세요.")


if __name__ == "__main__":
    main()
