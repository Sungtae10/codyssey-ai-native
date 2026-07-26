// n8n Code 노드에 들어갈 스코어링 로직 단위 테스트 (로컬 검증용)
const SIGNAL = {
  '자본시장': ['투자', '인수', '합병', '지분', '상장'],
  '기술자산': ['특허', '양산', '출시'],
  '제도정책': ['규제'],
  '사업화':   ['계약', '수주', '협력'],
};
const THRESHOLD = 2;
const MAX_ITEMS = 5;
const TOOL = 'n8n';

const stripTags = (s = '') =>
  String(s).replace(/<[^>]*>/g, ' ').replace(/&[a-zA-Z#0-9]+;/g, ' ').replace(/\s+/g, ' ').trim();
const jsonSafe = (s = '') => String(s).replace(/[\x22\x5C\r\n]/g, ' ').replace(/\s+/g, ' ').trim();
const kst = (d) => {
  const dt = d ? new Date(d) : new Date();
  if (isNaN(dt.getTime())) return '';
  return new Intl.DateTimeFormat('sv-SE', {
    timeZone: 'Asia/Seoul', year: 'numeric', month: '2-digit', day: '2-digit',
    hour: '2-digit', minute: '2-digit', hour12: false,
  }).format(dt).replace('T', ' ');
};

function run(items) {
  const out = [];
  for (const item of items.slice(0, MAX_ITEMS)) {
    const j = item.json;
    const title = stripTags(j.title);
    const summary = stripTags(j.contentSnippet || j.content || j.description || '').slice(0, 200);
    const hay = (title + ' ' + summary).toLowerCase();
    const matched = [];
    for (const words of Object.values(SIGNAL)) {
      for (const w of words) {
        if (hay.includes(w.toLowerCase()) && !matched.includes(w)) matched.push(w);
      }
    }
    const score = matched.length;
    out.push({ json: {
      collected_at: kst(),
      tool: TOOL,
      tier: score >= THRESHOLD ? 'CORE' : 'REF',
      score,
      matched_keywords: matched.join(','),
      title,
      title_safe: jsonSafe(title),
      summary,
      published_at: kst(j.isoDate || j.pubDate),
      link: j.link || '',
    }});
  }
  return out;
}

// --- 실제 rss.etnews.com/Section901.xml 에서 확인된 형태의 테스트 픽스처 ---
const fixture = [
  { json: { title: '울산 글로벌 산업AX 선도도시 추진…‘피지컬AI’와 ‘AIDC’ 양축',
    description: '<p>울산시가 산업 인공지능 전환(AX) 선도도시 조성에 나선다. 시는 관련 기업과 투자 협력 양해각서를 체결하고 데이터센터 유치 계약을 추진한다.</p>',
    pubDate: 'Sun, 26 Jul 2026 09:10:00 +0900', link: 'https://www.etnews.com/20260726000001' } },
  { json: { title: '스리랑카, 군용 드론 동원해 모기 ‘소탕’…올해만 뎅기열 56명 사망',
    description: '스리랑카 정부가 드론을 활용해 모기 서식지를 탐지하고 있다.',
    pubDate: 'Sun, 26 Jul 2026 08:40:00 +0900', link: 'https://www.etnews.com/20260726000002' } },
  { json: { title: '유인원도 긴장하면 서로 끌어안아…"사람처럼 신체접촉 통해 연대감 형성"',
    description: '연구팀은 유인원의 사회적 행동을 관찰했다.',
    pubDate: 'Sun, 26 Jul 2026 08:20:00 +0900', link: 'https://www.etnews.com/20260726000003' } },
  { json: { title: '정의선·젠슨 황, 한달만에 재회…"자율주행·로봇 협력 구체화"',
    description: '양사는 자율주행 반도체 공동개발 계약을 체결하고 내년 양산을 목표로 한다.',
    pubDate: 'Sat, 25 Jul 2026 19:00:00 +0900', link: 'https://www.etnews.com/20260725000004' } },
  { json: { title: '李대통령, 방미 성과 9500억달러…빅테크 AI R&D 거점도 한국에',
    description: '정부는 규제 완화와 세제 지원을 약속했다.',
    pubDate: 'Sat, 25 Jul 2026 17:30:00 +0900', link: 'https://www.etnews.com/20260725000005' } },
];

const res = run(fixture);
console.log('=== 스코어링 결과 ===');
for (const r of res) {
  console.log(`[${r.json.tier}] score=${r.json.score} kw=${r.json.matched_keywords || '-'} | ${r.json.title.slice(0, 34)}`);
}
const core = res.filter((r) => r.json.tier === 'CORE').length;
console.log(`\nCORE=${core} / REF=${res.length - core}  (두 경로 모두 발화: ${core > 0 && core < res.length})`);
console.log('\n=== 필드 검증 (1번 아이템) ===');
console.log(JSON.stringify(res[0].json, null, 2));
console.log('\n=== JSON 이스케이프 안전성 (3번 아이템: ASCII 따옴표 포함) ===');
console.log('원본     :', res[2].json.title);
console.log('title_safe:', res[2].json.title_safe);
console.log('페이로드  :', JSON.stringify({ content: `[REF] ${res[2].json.title_safe}` }));
