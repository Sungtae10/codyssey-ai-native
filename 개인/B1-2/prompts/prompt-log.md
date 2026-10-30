# 프롬프트 로그 — KARIOS AI 광고 (Codyssey b2-2)

> **제작 방식:** Google Veo(Pro)의 **T2V(텍스트→영상)** 로 씬별 영상을 직접 생성 → CapCut에서 트림·전환·자막·BGM 통합.
> **내레이션:** 음성 없이 **화면 자막(온스크린 텍스트)** 으로 대체. 각 씬의 자막 텍스트를 아래에 명시.

**최종 산출물:** `assets/final/karios_ad_10s.mp4` (10초 · 16:9 · 720p · H.264/AAC · 30fps)

---

## 공통 스타일 레퍼런스

모든 씬 프롬프트 말미의 `[STYLE REF]` 자리에 아래 문장을 그대로 삽입해 화풍을 통일한다.

```
Style: cinematic tech commercial, premium and clean, deep navy blue to warm amber
color grade, volumetric light, shallow depth of field, smooth camera motion,
modern minimal UI design, Apple-style product film. 16:9.
```

**컬러 토큰:** 딥네이비 `#0E1530` → 웜앰버 `#D98324`
**AI 심볼:** 앰버 오브(amber orb) — 씬2(앱 UI 중앙)·씬4(브랜드)에 공통 사용해 KARIOS AI 아이덴티티 통일

---

## 씬 1 (기 · 2.5초) — 문제: 알림 과부하

| 항목 | 내용 |
|---|---|
| **목표 메시지** | 현대 직장인이 알림·메시지·일정에 압도당하는 과부하를 한 컷에 각인 |
| **내레이션/자막** | "매일, 결정의 순간은 너무 빨리 옵니다." |
| **사용 도구** | Google Veo (Pro · T2V) · Suno(BGM 긴장 파트) |
| **출력 파일** | `assets/videos/s1_chaos.mp4` |

**T2V 프롬프트 (Google Veo)**
```
A cinematic wide shot of a young professional sitting at a desk in a dark modern room,
overwhelmed and stressed, surrounded by dozens of glowing smartphone notification bubbles,
chat alerts, and calendar pop-ups swirling chaotically in the air around them.
The person holds their head, exhausted. Cold blue light mixed with chaotic colorful
notification glows. Slow push-in camera. Ambient tense electronic hum. [STYLE REF]
```

**출력 결과:** 알림 과부하가 한눈에 읽히는 오프닝. 시청자의 "이 사람 = 나" 공감 확보.

---

## 씬 2 (승 · 2.5초) — KARIOS AI 앱 등장 & 분석

| 항목 | 내용 |
|---|---|
| **목표 메시지** | KARIOS AI 앱이 켜지며 혼돈을 분석·정리 — "이건 AI 앱이다"가 한눈에 |
| **내레이션/자막** | "KARIOS AI가 당신의 순간을 먼저 분석합니다." |
| **사용 도구** | Google Veo (Pro · T2V) · Suno(BGM 전환 파트) |
| **출력 파일** | `assets/videos/s2_ai_analysis.mp4` |

**T2V 프롬프트 (Google Veo)**
```
A cinematic close-up of a hand holding a modern smartphone in a dark room.
On the screen, a sleek minimalist AI assistant app interface awakens: a glowing amber orb
pulses at the center while clean UI cards and data streams elegantly organize themselves,
as if the AI is analyzing and sorting the chaos. The chaotic notifications from before
flow into the phone and become neat, ordered cards. Soft amber glow illuminates the face.
Calm confident electronic music swell. [STYLE REF]
```

**출력 결과:** 스마트폰 화면에 AI 앱 UI(앰버 오브·정돈된 카드)가 명확히 보임 → "KARIOS = AI 앱" 즉각 전달.

---

## 씬 3 (전 · 2초) — AI가 먼저 제안

| 항목 | 내용 |
|---|---|
| **목표 메시지** | AI가 묻기 전에 먼저 추천 카드를 띄워주는 선제·적시 가치 전달 |
| **내레이션/자막** | "당신보다 한 발 먼저, KARIOS가 제안합니다." |
| **사용 도구** | Google Veo (Pro · T2V) · Suno(BGM 해소 파트) |
| **출력 파일** | `assets/videos/s3_ai_suggest.mp4` |

**T2V 프롬프트 (Google Veo)**
```
A cinematic close-up of a user looking at their smartphone with a calm, relieved smile.
On the screen, the KARIOS AI app proactively displays a clean recommendation card that
gently slides up with a soft amber glow — a smart suggestion notification appearing
before the user even asks. Warm amber ambient light, cozy modern interior softly blurred
in the background. Gentle uplifting music. [STYLE REF]
```

**출력 결과:** "AI가 먼저 알아서 해준다"는 선제 가치가 따뜻하게 전달됨.

---

## 씬 4 (결 · 3초) — 브랜드 각인 (필수 장치)

| 항목 | 내용 |
|---|---|
| **목표 메시지** | 브랜드명·슬로건·CTA 각인 — 과제 필수 "마지막 3–5초 브랜드 장치" 충족 |
| **내레이션/자막** | (브랜드 자막) "KARIOS — Make it Simple" |
| **사용 도구** | Google Veo (Pro · T2V) · CapCut(로고·슬로건 텍스트 오버레이) |
| **출력 파일** | `assets/videos/s4_brand.mp4` |

**T2V 프롬프트 (Google Veo)**
```
A minimal premium brand end card animation: dark navy background, a glowing amber orb
gently forms into a clean logo mark at the center, soft light rays, lots of negative space,
subtle particles settling. Elegant, calm, high-end tech brand reveal. Ambient soft chime.
[STYLE REF]
```

**CapCut 오버레이 텍스트 (정확한 문구)**
- 중앙: `KARIOS` (+ Ø 로고 심볼)
- 하단: `Make it Simple`
- (선택) 최하단 소형: `당신의 AI 비서 · karios.ai`

> ⚠️ 생성형 AI는 화면 내 문자를 자주 왜곡하므로, **정확한 브랜드 텍스트는 Veo에 맡기지 않고 CapCut에서 오버레이**하는 전략 채택.

**출력 결과:** 브랜드명·슬로건·CTA가 정확하고 깔끔하게 각인되는 엔드카드.

---

## 오디오 — BGM (Suno)

| 항목 | 내용 |
|---|---|
| **설정** | Instrumental 모드 ON (보컬 없음 — 광고 BGM) |
| **출력 파일** | `assets/audio/bgm.mp3` (원본 3:02 → 편집에서 10초 사용) |

**프롬프트 (Suno)**
```
Cinematic ambient brand film music, tense textured pad at the start resolving into a calm
warm uplifting tone, minimal, premium, no vocals, subtle brand-sting ending
```

**출력 결과:** 앞부분 긴장(씬1) → 뒷부분 따뜻한 해소(씬2·3)로 영상 서사와 일치. CapCut에서 10초 트림 + 페이드아웃 2초 적용.

---

# 프롬프트 수정 전 / 후 로그 (A → B)

## 로그 1 — 씬1 이미지 프롬프트 (v1 → v2)

| 구분 | 내용 |
|---|---|
| **버전 / 대상** | v1 → v2 · 씬1(문제 제시) · 2026-06 |
| **수정 전 의도** | 인물 "얼굴 클로즈업"으로 과부하 표정을 직접 표현 |
| **A (수정 전)** | `Cinematic close-up of a stressed person's face overwhelmed by floating notifications, detailed facial expression, anxious eyes ...` |
| **발생한 문제** | ① 무료 도구에서 얼굴 디테일·일관성 붕괴 → 씬 간 인물 불일치 ② 표정 과장으로 프리미엄 톤과 충돌 ③ "스톡 영상" 느낌 |
| **B (수정 후)** | 얼굴 제거 → **실루엣** 중심. 과부하를 "표정"이 아닌 "빛·파편(환경)"으로 표현, 와이드 구도로 시네마틱 강화 |
| **결과 변화 · 원인** | 일관성 문제 소멸 · 톤 통일 · 시네마틱↑. **원인:** 얼굴이라는 "고빈도 실패 지점"을 제거해 모델 부담을 낮춤 → 재생성↓ → 크레딧 절약 |

---

## 로그 2 — 영상 도구·방식 전환 (v2 → v3)

| 구분 | 내용 |
|---|---|
| **버전 / 대상** | v2 → v3 · 전체 영상 · 2026-07 |
| **수정 전 방식** | Gemini(T2I) → Kling(I2V): 이미지를 먼저 만들고 영상으로 변환 |
| **A (수정 전)** | 추상적 빛·궤도·홀로그램 카드로 표현. 화풍은 통일됐으나 **"이게 AI 앱인지 불명확"** + **"각 씬이 뭘 의미하는지 애매"** 하다는 동료평가 피드백 |
| **발생한 문제** | ① 각 씬의 의미가 추상적이라 전달 실패 ② "AI 프로그램"임이 시각적으로 드러나지 않음 |
| **B (수정 후)** | **Google Veo(T2V)** 로 전환. 텍스트 프롬프트에서 직접 영상 생성하며 **스마트폰·AI 앱 UI·알림 장면을 명확히 지정** |
| **결과 변화 · 원인** | "KARIOS = AI 비서 앱"이 한눈에 읽힘. **원인:** T2V는 T2I+I2V 조합보다 **구체적 AI 제품 UI 시각화**에 훨씬 정밀하게 대응 가능 |

---

## 로그 3 — 영상 결과물 품질 비교 (1차 → 최종)

| 구분 | 내용 |
|---|---|
| **버전 / 대상** | v1(Kling I2V) → v2(Veo T2V) · 전체 영상 · 2026-07 |
| **A (1차 결과물)** | ① **제품 특성 미표현** — 추상적 빛·궤도만 있어 "무슨 AI 제품인지" 불명확 ② **인체 형태 붕괴** — 팔·다리·비율이 프레임마다 깨져 실루엣으로 우회할 수밖에 없었음 ③ 로고·브랜드 텍스트 생성 불가 |
| **B (최종 결과물)** | ① **제품 특성 명확** — 스마트폰 화면에 KARIOS AI 앱 UI(앰버 오브·추천 카드)가 직접 보임 ② **인체 형태 자연스러움** — 얼굴·손·자세가 정상 렌더링되어 실제 인물 등장 가능 ③ **로고·브랜드 텍스트 정상 생성** |
| **원인 분석** | I2V는 정지 이미지 1장을 기점으로 움직임을 **추론**하기 때문에 인체 구조·UI 디테일이 프레임마다 붕괴됨. 반면 T2V(Veo)는 텍스트에서 영상을 **직접 생성**하며 인체 해부학·UI 레이아웃·문자를 구조적으로 이해 → 형태가 유지됨 |
| **정량 결과** | 길이 10.05초 유지 · 용량 9.36MB → **7.94MB (−15%)** · 720p/30fps 동일 · **실루엣 우회 불필요** |
| **비교 파일(증빙)** | **A(1차):** `assets/archive/karios_ad_v1_before.mp4` (9.36MB) → **B(최종):** `assets/final/karios_ad_10s.mp4` (7.94MB). 두 파일을 직접 재생해 개선 전후 비교 가능 |

**교훈:** 추상적 연출은 "예쁘지만 의미 전달에 실패"할 수 있다. AI 제품 광고에서는 **제품 UI를 직접 보여주는 것**이 브랜드 이해도에 결정적이며, 이를 위해서는 **I2V보다 T2V가 구조적으로 유리**하다.

---

# 편집 사양 (CapCut)

| 항목 | 설정 |
|---|---|
| 씬 길이 | 씬1 2.5s · 씬2 2.5s · 씬3 2s · 씬4 3s = **총 10초** |
| 전환 | 디졸브(Dissolve) — 씬1-2, 씬2-3, 씬3-4 경계 |
| 자막 | 흰색 · 클린 폰트 · 하단 중앙 배치 (씬별 문구는 위 각 씬 참조) |
| 오디오 | BGM 볼륨 조정 + 페이드인 0.5s / 페이드아웃 2s |
| 내보내기 | MP4 · H.264/AAC · 1280×720 · 30fps |

---

*모든 프롬프트는 실제 제작에 사용된 원문이며, AI 도구 정보는 2026년 7월 기준입니다.*
