# AI Promise | 기업 AI 약속 검증

회사가 사업보고서에 "AI로 이것을 하겠다"고 쓴 약속을 찾고, 다음 보고서에 실행 근거가 있는지 찾아 4가지(근거 확인, 일부 확인, 공시에서 확인 불가, 회사가 미추진으로 공시)로 판정해 보여주는 웹 서비스입니다. Codyssey Final Project입니다.

- 핵심 기업: 삼성전자(개발·시연용), SK하이닉스(평가용)
- 확장 데모 기업: 카카오, 신한은행, NAVER. 시간 부족 시 Core 2(삼성전자·SK하이닉스)를 먼저 완성하고, 확장 3곳은 시연용으로 표시해 Human blind evaluation 수치에는 포함하지 않습니다.
- 약속을 찾는 보고서: 2024 사업보고서 / 근거를 찾는 보고서: 2025 사업보고서, 2026 반기보고서

## 1. 폴더

| 폴더 | 내용 | 만든 사람 |
| --- | --- | --- |
| `app/` | 웹 화면 4개 (HTML, CSS, JS). Vercel이 이 폴더를 배포합니다 | 화면: 박수민 (`1011_수민_화면.zip`) / 디자인: 서준용 (시안 v4, 10/12·10/13) / 엔진 결과 연결: 김성태 (`1012_김성태_화면_데이터연결.zip`) |
| `engine/` | 공시 PDF에서 약속을 찾고, 근거를 검색해 판정하고, 면접 카드를 만드는 AI 엔진 | 김성태 |
| `eval/` | 판정 기준(v1, v2)과 사람 정답으로 AI를 평가하는 코드 | 김성태 (정답: 김서원, 김성태) |
| `tests/` | 인터넷과 API 키 없이 가상 회사로 끝까지 도는 시험 | 김성태 |
| `data/` | 공시 PDF와 실행 결과 자리 (PDF는 저장소에 올리지 않습니다) | |

### Final Sprint 데이터 모드

현재 `app/data/results.json`에는 **삼성전자·SK하이닉스 실제 공시 문장을 사람이 원문 대조한 검증용 시연 데이터**가 들어 있습니다. 이는 fake sample이 아니지만, 자동 엔진의 최종 accuracy 결과로 주장하지 않습니다.

- 삼성전자: 김서원 연습 Human Review를 v2 기준에 맞춰 정리
- SK하이닉스: 김서원 독립 Human Review 1차를 반영
- 화면 상단에 검증용 시연 데이터임을 명시
- 자동 엔진 결과와 Human Gold 합의 평가는 별도 증빙으로 구분

이 임시 모드는 사용자 테스트에서 **UI/이해도/신뢰도/활용 의향**을 확인하기 위한 것입니다. 실제 AI 정확도 수치가 없으면 만들어 쓰지 않습니다.

## 2. 화면

- `app/index.html`은 `app/data/results.json`(엔진 결과)을 먼저 읽고, 없으면 `app/data/sample-data.js`(가상 회사 2곳 예시 데이터)를 보여줍니다. 예시 데이터일 때는 화면 위에 "예시 데이터입니다" 띠가 나옵니다.
- 화면 고치는 규칙은 `app/README.md`에 있습니다. 디자인 변경은 CSS에서 합니다.

## 3. 엔진

자세한 준비와 실행 순서는 `engine/README.md`에 있습니다. 결과를 화면에 넣는 명령은 다음과 같습니다.

```bash
cd engine
python run.py export --companies samsung skhynix --copy-to ../app/data/results.json
```

코드 점검(키 없이 가상 회사로 시험):

```bash
python tests/test_mock.py        # 엔진·평가: 마지막 줄에 "시험 통과"
python tests/test_ui_static.py   # 화면: app.js가 쓰는 class가 CSS에 모두 있는지 (브라우저 없이)
python tests/ui_check.py         # 화면: 모든 화면(예시 데이터 18개) x 다크/라이트의 글자 대비, 가로 넘침, 필수 부품 (Playwright 필요)
```

세 검사는 GitHub에 올릴 때마다 CI에서도 자동으로 돌아갑니다.

## 4. 작업 규칙

- 최종 마감 구간에는 **최신 main → 작업 브랜치 → 테스트 → Pull Request → merge** 순서만 사용합니다.
- 실제 배포 여부와 배포 URL은 README의 링크 섹션에 명시하며, 배포가 확인되지 않은 상태를 '배포 완료'라고 표현하지 않습니다.
- main에 합치기 전 `python tests/test_mock.py`, `python tests/test_ui_static.py`, `python tests/ui_check.py`를 통과시킵니다.
- 디자인을 바꾸면 `app/css/style.css` 맨 아래 데이터 연결 부품을 유지하고, 320~390px 모바일 화면과 명도 대비를 다시 확인합니다.
- 사용자 테스트 중 발견된 문제는 먼저 기록하고, 테스트가 끝난 뒤 우선순위가 높은 피드백을 브랜치에서 수정합니다.

## 5. 지키는 것

- API 키(`engine/.env`), 사용자 테스트 참여자의 이름과 연락처는 저장소에 올리지 않습니다. (`.gitignore`로 막아 둠)
- 화면과 판정 이유에 "거짓", "AI 워싱" 같은 단정 표현을 쓰지 않습니다. 근거를 못 찾은 약속은 "공시에서 확인 불가"로 표시하며, 안 했다는 뜻이 아닙니다.
- SK하이닉스는 평가용 기업이라, 사람 정답을 먼저 만든 뒤 AI 결과와 비교합니다.

## 6. 역할

- 김성태: 총괄, AI 엔진, 평가 설계, 저장소와 배포
- 박수민: 화면 4개
- 김서원: 공시 직접 읽기와 정답 매기기, 사용자 테스트 진행
- 서준용: 화면 디자인, 사용자 테스트 진행 보조, 발표자료, 3분 시연 영상

## 7. AI 사용

엔진 코드의 첫 버전, 화면의 엔진 결과 연결 수정, 디자인 시안 반영과 접근성 보정, 화면 자동 검사는 AI 도구(Claude)로 작성했습니다. 문서와 CI 일부는 ChatGPT가 Pull Request로 올렸습니다 (PR #1, #2). 실행, 점검, 수정은 김성태가 합니다. 엔진의 모든 AI 호출 기록은 실행할 때 `data/work/<기업>/llm_log.jsonl`에 남습니다.


## 8. 프로젝트 문서

- [아키텍처](docs/architecture.md)
- [평가 계획](docs/evaluation-plan.md)
- [10분 비대면 사용자 테스트](docs/user-test-protocol.md)
- [시연용 기업 확장 계획 (관문 2 통과 시)](docs/company-expansion-plan.md)
- [AI 윤리·신뢰성](docs/ai-ethics.md)
- [Vercel 배포](docs/deploy.md)
- [Google Drive ↔ GitHub 동기화](docs/drive-sync.md)
- [제출 증빙 체크리스트](docs/submission-evidence-checklist.md)
- [팀 협업 규칙](CONTRIBUTING.md)
- [프로젝트 기획서](docs/project-plan.md)
- [기능·비기능 요구사항](docs/requirements.md)
- [공식 요구사항 ↔ 증빙 매트릭스](docs/official-requirements-matrix.md)
- [사용자 피드백 반영 로그](docs/feedback-log.md)
- [최종 발표 구성안](docs/presentation-outline.md)
- [최종 제출 Release Checklist](docs/release-checklist.md)
- [팀 기여 내역](docs/team-contributions.md)
- [Final Project 결과보고서 초안](docs/final-report-draft.md)

## 9. 추가 평가

- 사용자 테스트: `eval/user_test/`
- 문장 분류 ML 실험 (`eval/ml/`): 이번 제출(10/18)에서는 하지 않고 다음 단계로 둡니다 (기획 보고서 8.3). 코드와 데이터 형식만 있습니다.


## 10. 공식 Final Project 요구사항 대응

- 생성형 AI / AI Agent 핵심 기능: 약속 추출, 근거 검색·재검색, 판정, citation verification, 면접 카드
- 필수 기술요소: **RAG + Agent-style workflow** (자동화 Python pipeline 보조)
- 외부 배포: 공개 URL 필수
- 실제 사용자: **최소 5명 이상**
- 사용자 피드백: 수집 후 최소 1건 이상 실제 서비스에 반영하고 commit/PR로 증빙
- AI 윤리: AI 생성 분석 고지, 단정 표현 금지, 개인정보 비저장
- 기능·비기능 요구사항: [docs/requirements.md](docs/requirements.md)
- 마감 최소 완성안: [docs/final-sprint.md](docs/final-sprint.md)
- 빠른 사용자 테스트: [docs/user-test-quick.md](docs/user-test-quick.md)


## 11. 심사자에게 보여줄 핵심

**AI Promise는 공시 요약기가 아니라 ‘기업의 AI 약속 ↔ 후속 실행 근거’를 연결하는 조사 서비스입니다.**

1. **공식 데이터**: DART 정기공시를 근거로 사용
2. **AI Native 구조**: LLM 약속 추출 + RAG 검색 + 제한적 재검색 + 판정 + citation verification + 면접 카드
3. **검증 가능성**: 사용자가 판정에서 DART 원문까지 되돌아갈 수 있음
4. **안전한 표현**: ‘공시에서 확인 불가’를 실제 미이행으로 단정하지 않음
5. **실사용 검증**: 최소 5명 테스트 및 실제 피드백 반영을 제출 증빙으로 남김

### 제출 링크
- 현재 팀 공유 배포 URL: https://ai-promise-six.vercel.app
- 서비스 URL 최종 검증: **제출 전 시크릿 창/모바일에서 직접 확인 필요**
- 사용자 테스트: **[실제 인원 입력]명**
- 피드백 반영: [docs/feedback-log.md](docs/feedback-log.md)
- 발표자료: **[완성 후 링크 입력]**
- 시연 영상: **[완성 후 링크 입력]**
