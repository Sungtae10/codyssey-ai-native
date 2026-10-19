# 배포 가이드

현재 웹은 빌드가 필요 없는 HTML/CSS/JS 구조입니다.

## Vercel
**현재 연결 (10/15 19:29):** 프로젝트 `ai-promise`, Root Directory `app`, 주소 https://ai-promise-six.vercel.app. main에 올리면 이 주소로 다시 배포되고, 다른 브랜치는 Vercel 로그인이 필요한 미리보기 주소로 배포됩니다.

가장 단순한 방법은 Vercel 프로젝트의 **Root Directory를 `app`**으로 지정하는 것입니다.

1. GitHub 저장소 `Sungtae10/ai-promise` 연결
2. Root Directory: `app`
3. Framework Preset: Other
4. Build Command: 비움
5. Output Directory: 비움
6. Deploy

## 실제 데이터 반영
배포 전에 엔진에서 실제 결과를 생성합니다.

```bash
cd engine
python run.py export --companies samsung   # 결과는 data/results/ai_promise_data.json 에만 저장
python run.py check --file ../data/results/ai_promise_data.json
# 사용자 테스트가 끝나고 SK하이닉스 합의 뒤에만: python run.py export --companies samsung skhynix --copy-to ../app/data/results.json
```

`results.json`이 없으면 화면은 예시 데이터로 fallback합니다. 최종 심사용 URL에서는 반드시 화면 상단에 '예시 데이터' 띠가 없는지 확인합니다.

## 배포 QA
- [ ] 기업 선택
- [ ] 약속 목록
- [ ] 약속 상세
- [ ] DART 원문 링크
- [ ] 면접 카드
- [ ] 모바일 화면
- [ ] 다크/라이트 모드
- [ ] 실제 데이터 고지문구
