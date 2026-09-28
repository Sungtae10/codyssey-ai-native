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
LINE = "─" * 44
TOP_LIMIT = 5  # 보너스 2: 인기 프롬프트 목록에 보여 줄 개수


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


def make_prompt(title, content, category, favorite=False, views=0):
    """프롬프트 1개를 딕셔너리로 만든다.
    모든 프롬프트가 같은 키(제목, 내용, 카테고리, 즐겨찾기, 조회수)를 갖도록 이 함수 한 곳에서만 만든다.
    """
    return {
        "title": title,
        "content": content,
        "category": category,
        "favorite": favorite,
        "views": views,  # 보너스 2: 상세 보기로 열어 본 횟수
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


def ask_yes_no(message):
    """y 또는 n을 입력받아 True 또는 False를 돌려준다. 한글 자판 상태에서 누른 ㅛ, ㅜ도 인정한다."""
    while True:
        answer = input(message).strip().lower()
        if answer in ("y", "yes", "ㅛ"):
            return True
        if answer in ("n", "no", "ㅜ"):
            return False
        print("  y 또는 n으로 입력해 주세요.")


def choose_category(current=None):
    """미리 정한 카테고리 중 하나를 번호로 고르거나, 새 이름을 직접 입력받는다.
    current(지금 카테고리)를 넘기면 0번 '그대로 두기'가 생기고, 0을 고르면 None을 돌려준다. (보너스 2: 수정)
    """
    print("\n카테고리 선택:")
    if current is not None:
        print(f"0) 그대로 두기 (현재: {current})")
    for number, category in enumerate(CATEGORIES, start=1):
        print(f"{number}) {category}")
    custom_number = len(CATEGORIES) + 1
    print(f"{custom_number}) 직접 입력")

    while True:
        number = to_number(input("선택: "))
        if current is not None and number == 0:
            return None
        if number is not None and 1 <= number <= len(CATEGORIES):
            return CATEGORIES[number - 1]
        if number == custom_number:
            return input_text("새 카테고리 이름: ")
        print("  목록에 있는 번호를 골라 주세요.")


def select_prompt(prompts, message):
    """프롬프트 번호를 입력받아 리스트 위치(index)를 돌려준다.
    화면 번호는 1부터, 리스트 위치는 0부터 시작하므로 '번호 - 1'을 돌려준다.
    잘못된 번호면 안내 메시지를 출력하고 None을 돌려준다.
    """
    if not prompts:
        print("등록된 프롬프트가 없습니다.")
        return None
    number = to_number(input(message))
    if number is None or number < 1 or number > len(prompts):
        print(f"잘못된 번호입니다. 1~{len(prompts)} 사이의 번호를 입력해 주세요.")
        return None
    return number - 1


# ============================================================
# 출력 도우미: 화면에 보여 주는 모양을 한 곳에서 관리
# ============================================================
def print_title(title):
    """기능 화면의 제목 줄을 출력한다. 예: === 프롬프트 추가 ==="""
    print()
    print(f"=== {title} ===")


def format_prompt_line(number, prompt):
    """목록에 보여 줄 한 줄을 만든다. 예: 1. [페르소나] Paper Lens ⭐"""
    star = ""
    if prompt["favorite"]:
        star = " ⭐"
    return f"{number}. [{prompt['category']}] {prompt['title']}{star}"


def print_all_lines(prompts):
    """모든 프롬프트를 1번부터 번호를 붙여 한 줄씩 출력한다."""
    for number, prompt in enumerate(prompts, start=1):
        print(format_prompt_line(number, prompt))


def print_prompt_lines(pairs):
    """(전체 번호, 프롬프트) 쌍 목록을 한 줄씩 출력한다. 카테고리, 검색, 즐겨찾기 결과에 쓴다."""
    for number, prompt in pairs:
        print(format_prompt_line(number, prompt))


def preview(text, limit=30):
    """긴 내용은 첫 줄 앞부분만 잘라서 보여 준다. (보너스 2: 수정 화면에서 사용)"""
    first_line = text.strip().split("\n")[0]
    if len(first_line) > limit:
        return first_line[:limit] + "..."
    if "\n" in text.strip():
        return first_line + " ..."
    return first_line


# ============================================================
# 찾기: 조건에 맞는 프롬프트를 (전체 번호, 프롬프트) 쌍으로 모으는 함수
# ============================================================
def get_categories(prompts):
    """기본 카테고리 6개 뒤에, 사용자가 직접 입력한 카테고리를 덧붙여 돌려준다."""
    categories = list(CATEGORIES)  # 원본 상수는 그대로 두고 복사본에 덧붙인다
    for prompt in prompts:
        if prompt["category"] not in categories:
            categories.append(prompt["category"])
    return categories


def find_by_category(prompts, category):
    """해당 카테고리의 프롬프트만 모은다."""
    results = []
    for number, prompt in enumerate(prompts, start=1):
        if prompt["category"] == category:
            results.append((number, prompt))
    return results


def find_by_keyword(prompts, keyword):
    """제목 또는 내용에 검색어가 들어 있는 프롬프트를 모은다. 영문 대소문자는 구분하지 않는다."""
    keyword = keyword.lower()
    results = []
    for number, prompt in enumerate(prompts, start=1):
        in_title = keyword in prompt["title"].lower()
        in_content = keyword in prompt["content"].lower()
        if in_title or in_content:
            results.append((number, prompt))
    return results


def find_favorites(prompts):
    """즐겨찾기(favorite)가 True인 프롬프트만 모은다."""
    results = []
    for number, prompt in enumerate(prompts, start=1):
        if prompt["favorite"]:
            results.append((number, prompt))
    return results


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


def show_list(prompts):
    """저장된 모든 프롬프트를 1번부터 번호를 붙여 출력한다. 즐겨찾기는 ⭐로 표시한다."""
    print_title("프롬프트 목록")
    if not prompts:
        print("등록된 프롬프트가 없습니다. 1번 메뉴에서 먼저 추가해 주세요.")
        return
    print_all_lines(prompts)
    print(f"\n총 {len(prompts)}개의 프롬프트")


def show_by_category(prompts):
    """카테고리 목록(개수 포함)을 보여 주고, 고른 카테고리의 프롬프트만 출력한다."""
    print_title("카테고리별 조회")
    categories = get_categories(prompts)
    for number, category in enumerate(categories, start=1):
        count = len(find_by_category(prompts, category))
        print(f"{number}) {category} ({count}개)")

    number = to_number(input("선택: "))
    if number is None or number < 1 or number > len(categories):
        print("잘못된 번호입니다. 메뉴로 돌아갑니다.")
        return

    category = categories[number - 1]
    results = find_by_category(prompts, category)
    print(f"\n[{category}] 카테고리 프롬프트:")
    if not results:
        print("이 카테고리에는 아직 프롬프트가 없습니다.")
        return
    print_prompt_lines(results)
    print(f"\n총 {len(results)}개의 프롬프트 (번호는 전체 목록 기준)")


def search_prompt(prompts):
    """검색어를 입력받아 제목 또는 내용에 그 검색어가 있는 프롬프트를 출력한다."""
    print_title("프롬프트 검색")
    keyword = input_text("검색어: ")
    results = find_by_keyword(prompts, keyword)
    print("\n검색 결과:")
    if not results:
        print(f"'{keyword}'이(가) 들어간 프롬프트가 없습니다.")
        return
    print_prompt_lines(results)
    print(f"\n{len(results)}개의 프롬프트를 찾았습니다. (번호는 전체 목록 기준)")


def show_detail(prompts):
    """번호를 입력받아 그 프롬프트의 제목, 카테고리, 즐겨찾기 여부, 내용 전체를 출력한다."""
    print_title("프롬프트 상세 보기")
    print_all_lines(prompts)
    index = select_prompt(prompts, "\n번호 입력: ")
    if index is None:
        return

    prompt = prompts[index]
    prompt["views"] += 1  # 보너스 2: 상세 보기를 할 때마다 조회수 1 증가
    favorite_text = "없음"
    if prompt["favorite"]:
        favorite_text = "⭐"
    print()
    print(LINE)
    print(f"제목: {prompt['title']}")
    print(f"카테고리: {prompt['category']}")
    print(f"즐겨찾기: {favorite_text}")
    print(f"조회수: {prompt['views']}회")
    print(LINE)
    print("내용:")
    print(prompt["content"])
    print(LINE)


def toggle_favorite(prompts):
    """번호를 입력받아 즐겨찾기를 켜고 끈다. (True면 False로, False면 True로)"""
    print_title("즐겨찾기 관리")
    print_all_lines(prompts)
    index = select_prompt(prompts, "\n프롬프트 번호 입력: ")
    if index is None:
        return

    prompt = prompts[index]
    prompt["favorite"] = not prompt["favorite"]
    if prompt["favorite"]:
        print(f"'{prompt['title']}' 프롬프트를 즐겨찾기에 추가했습니다! ⭐")
    else:
        print(f"'{prompt['title']}' 프롬프트를 즐겨찾기에서 해제했습니다.")


def show_favorites(prompts):
    """즐겨찾기한 프롬프트만 모아서 출력한다."""
    print_title("즐겨찾기 목록")
    results = find_favorites(prompts)
    if not results:
        print("즐겨찾기한 프롬프트가 없습니다. 6번 메뉴에서 추가해 주세요.")
        return
    print_prompt_lines(results)
    print(f"\n총 {len(results)}개의 즐겨찾기 (번호는 전체 목록 기준)")


# ============================================================
# 보너스 2: 수정, 삭제, 조회수 TOP 목록
# ============================================================
def edit_prompt(prompts):
    """번호로 고른 프롬프트의 제목, 내용, 카테고리를 고친다. 아무것도 입력하지 않은 항목은 그대로 둔다."""
    print_title("프롬프트 수정")
    print_all_lines(prompts)
    index = select_prompt(prompts, "\n수정할 번호: ")
    if index is None:
        return

    prompt = prompts[index]
    print("바꾸지 않을 항목은 아무것도 입력하지 않고 Enter를 누르세요.")
    new_title = input(f"새 제목 (현재: {prompt['title']}): ").strip()
    new_content = input(f"새 내용 (현재: {preview(prompt['content'])}): ").strip()
    new_category = choose_category(current=prompt["category"])

    changed = False
    if new_title:
        prompt["title"] = new_title
        changed = True
    if new_content:
        prompt["content"] = new_content
        changed = True
    if new_category is not None and new_category != prompt["category"]:
        prompt["category"] = new_category
        changed = True

    if changed:
        print(f"\n'{prompt['title']}' 프롬프트를 수정했습니다.")
    else:
        print("\n바뀐 내용이 없습니다.")


def delete_prompt(prompts):
    """번호로 고른 프롬프트를 확인(y/n)을 받은 뒤 목록에서 지운다."""
    print_title("프롬프트 삭제")
    print_all_lines(prompts)
    index = select_prompt(prompts, "\n삭제할 번호: ")
    if index is None:
        return

    title = prompts[index]["title"]
    if not ask_yes_no(f"'{title}' 프롬프트를 삭제할까요? (y/n): "):
        print("삭제를 취소했습니다.")
        return
    prompts.pop(index)
    print(f"'{title}' 프롬프트를 삭제했습니다. 뒤에 있던 프롬프트 번호는 하나씩 앞당겨집니다.")


def get_views(pair):
    """정렬 기준 함수: (번호, 프롬프트) 쌍에서 조회수를 꺼낸다."""
    number, prompt = pair
    return prompt["views"]


def show_top_prompts(prompts):
    """상세 보기 조회수가 많은 순서로 최대 TOP_LIMIT개를 보여 준다. 조회수가 같으면 먼저 등록된 것이 앞에 온다."""
    print_title(f"인기 프롬프트 TOP {TOP_LIMIT} (조회수 순)")
    viewed = []
    for number, prompt in enumerate(prompts, start=1):
        if prompt["views"] > 0:
            viewed.append((number, prompt))
    if not viewed:
        print("아직 조회 기록이 없습니다. 5번(상세 보기)으로 프롬프트를 열면 조회수가 올라갑니다.")
        return

    viewed.sort(key=get_views, reverse=True)
    rank = 1
    for number, prompt in viewed[:TOP_LIMIT]:
        print(f"{rank}위 | {format_prompt_line(number, prompt)} | 조회 {prompt['views']}회")
        rank += 1


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
    print("---- 보너스 ----")
    print("8. 프롬프트 수정")
    print("9. 프롬프트 삭제")
    print(f"10. 인기 프롬프트 TOP {TOP_LIMIT}")
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
        elif choice == "2":
            show_list(prompts)
        elif choice == "3":
            show_by_category(prompts)
        elif choice == "4":
            search_prompt(prompts)
        elif choice == "5":
            show_detail(prompts)
        elif choice == "6":
            toggle_favorite(prompts)
        elif choice == "7":
            show_favorites(prompts)
        elif choice == "8":
            edit_prompt(prompts)
        elif choice == "9":
            delete_prompt(prompts)
        elif choice == "10":
            show_top_prompts(prompts)
        elif choice == "0":
            print("\n프로그램을 종료합니다. 실행 중에 추가하거나 바꾼 내용은 초기화됩니다.")
            break
        else:
            print("잘못된 입력입니다. 메뉴에 있는 번호를 입력해 주세요.")


if __name__ == "__main__":
    try:
        main()
    except (KeyboardInterrupt, EOFError):
        # Ctrl+C를 누르거나 입력이 끊겨도 빨간 오류(Traceback) 대신 안내만 보여 주고 끝낸다.
        print("\n\n프로그램을 종료합니다.")
