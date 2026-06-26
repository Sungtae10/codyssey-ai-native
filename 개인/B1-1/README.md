# Codyssey AI Tools Mission 1

## 프로젝트 개요
본 프로젝트는 **기술경영/CFM 논문 요약 및 연구 활용성 분석 AI 프롬프트 시스템**을 설계한 결과물이다. 논문 초록 또는 본문 일부를 입력하면 AI가 연구 질문, 방법론, 핵심 발견, CFM 연구와의 관련성, 한계 및 후속 연구 여지를 구조화하여 출력한다.

## 제출 파일 구성
| 파일 | 내용 |
|---|---|
| `01_task_definition_and_prompt_design.md` | 과업 정의, 입력 템플릿, 시스템/유저 프롬프트, Few-shot 예시 |
| `02_model_comparison_report.md` | Gemini, Claude, GPT-5.5 모델 비교 및 최종 선정 |
| `03_hallucination_test.md` | 환각 정의, Pass/Fail 기준, 검증 질문 7개 |
| `04_conversation_log.md` | 12턴 대화 로그 및 문맥 유지 평가 |
| `appendix/prompt_versions.md` | v1/v2 프롬프트와 개선 이력 |
| `appendix/raw_model_outputs.md` | 모델별 출력 요약 |

## 평가항목 대응표
| 평가항목 | 대응 파일 |
|---|---|
| 업무 과업 정의, 타겟 사용자, 입력/출력 규칙 | `01_task_definition_and_prompt_design.md` |
| 복사 가능한 입력 템플릿 | `01_task_definition_and_prompt_design.md` |
| 3종 모델 비교표, 평가 축, 점수, 근거 | `02_model_comparison_report.md` |
| Few-shot 3개, 모호한 입력→되묻기 | `01_task_definition_and_prompt_design.md` |
| 환각 검증 질문 5개 이상 및 Pass/Fail | `03_hallucination_test.md` |
| 10턴 이상 대화 로그와 중간 조건 변경 | `04_conversation_log.md` |
| 시스템/유저 프롬프트/입력 템플릿 분리 | `01_task_definition_and_prompt_design.md` |
| v1→v2 개선 과정 | `appendix/prompt_versions.md` |
| 평가 축 기반 모델 비교 | `02_model_comparison_report.md` |

## 개인정보 및 보안 처리
GitHub token, 비밀번호, 전화번호, 계정정보 등 민감정보는 포함하지 않았다. 공개 제출을 위해 개인 이름은 “사용자”, “연구자”, “본 연구”로 익명화하였다.

## 확인 순서
README → 01 과업/프롬프트 설계 → 02 모델 비교 → 03 환각 검증 → 04 대화 로그 → appendix 순서로 확인하면 된다.
