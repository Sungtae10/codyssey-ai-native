// n8n 워크플로우 JSON 생성기 (수동 이스케이프 오류 방지용)
const fs = require('fs');

const jsCode = `// ── TRC-v1 계약 (2)(3) 구현 ─────────────────────────────
const SIGNAL = {
  '자본시장': ['투자', '인수', '합병', '지분', '상장'],
  '기술자산': ['특허', '양산', '출시'],
  '제도정책': ['규제'],
  '사업화':   ['계약', '수주', '협력'],
};
const THRESHOLD = 2;   // θ
const MAX_ITEMS = 5;   // 계약 (1)
const TOOL = 'n8n';

const stripTags = (s = '') =>
  String(s).replace(/<[^>]*>/g, ' ').replace(/&[a-zA-Z#0-9]+;/g, ' ').replace(/\\s+/g, ' ').trim();

const jsonSafe = (s = '') =>
  String(s).replace(/["\\\\\\r\\n]/g, ' ').replace(/\\s+/g, ' ').trim();

const kst = (d) => {
  const dt = d ? new Date(d) : new Date();
  if (isNaN(dt.getTime())) return '';
  return new Intl.DateTimeFormat('sv-SE', {
    timeZone: 'Asia/Seoul', year: 'numeric', month: '2-digit', day: '2-digit',
    hour: '2-digit', minute: '2-digit', hour12: false,
  }).format(dt).replace('T', ' ');
};

const out = [];
for (const item of $input.all().slice(0, MAX_ITEMS)) {
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
    matched_keywords: matched.join(',') || '-',
    title,
    title_safe: jsonSafe(title),
    summary,
    published_at: kst(j.isoDate || j.pubDate),
    link: j.link || '',
  }});
}
return out;`;

const discordText =
  '=🔎 [CORE] {{ $json.title_safe }}\n' +
  '· 점수 {{ $json.score }} / 시그널 {{ $json.matched_keywords }}\n' +
  '· 발행 {{ $json.published_at }} · 수집 {{ $json.tool }}\n' +
  '{{ $json.link }}';

const sheetColumns = () => ({
  mappingMode: 'defineBelow',
  value: {
    '수집시각': '={{ $json.collected_at }}',
    '도구': '={{ $json.tool }}',
    '분류': '={{ $json.tier }}',
    '점수': '={{ $json.score }}',
    '매칭키워드': '={{ $json.matched_keywords }}',
    '제목': '={{ $json.title }}',
    '요약': '={{ $json.summary }}',
    '발행일': '={{ $json.published_at }}',
    '링크': '={{ $json.link }}',
  },
  matchingColumns: [],
  schema: [],
  attemptToConvertTypes: false,
  convertFieldsToString: true,
});

const wf = {
  name: 'TRC-v1 · 기술경영 리서치 큐레이션 (n8n)',
  nodes: [
    {
      parameters: {
        pollTimes: { item: [{ mode: 'everyDay', hour: 8, minute: 0 }] },
        feedUrl: 'https://rss.etnews.com/Section901.xml',
        options: {},
      },
      id: 'a1000000-0000-4000-8000-000000000001',
      name: 'RSS Feed Trigger',
      type: 'n8n-nodes-base.rssFeedReadTrigger',
      typeVersion: 1,
      position: [-220, 300],
    },
    {
      parameters: { mode: 'runOnceForAllItems', jsCode },
      id: 'a1000000-0000-4000-8000-000000000002',
      name: '정규화+스코어링',
      type: 'n8n-nodes-base.code',
      typeVersion: 2,
      position: [20, 300],
    },
    {
      parameters: {
        rules: {
          values: [
            {
              conditions: {
                options: { caseSensitive: true, leftValue: '', typeValidation: 'loose', version: 2 },
                conditions: [{
                  id: 'cond-core',
                  leftValue: '={{ $json.score }}',
                  rightValue: 2,
                  operator: { type: 'number', operation: 'gte' },
                }],
                combinator: 'and',
              },
              renameOutput: true,
              outputKey: 'CORE',
            },
            {
              conditions: {
                options: { caseSensitive: true, leftValue: '', typeValidation: 'loose', version: 2 },
                conditions: [{
                  id: 'cond-ref',
                  leftValue: '={{ $json.score }}',
                  rightValue: 2,
                  operator: { type: 'number', operation: 'lt' },
                }],
                combinator: 'and',
              },
              renameOutput: true,
              outputKey: 'REF',
            },
          ],
        },
        options: { fallbackOutput: 1 },
      },
      id: 'a1000000-0000-4000-8000-000000000003',
      name: '중요도 분기',
      type: 'n8n-nodes-base.switch',
      typeVersion: 3.2,
      position: [260, 300],
    },
    {
      parameters: {
        operation: 'append',
        documentId: { __rl: true, mode: 'url', value: 'YOUR_SPREADSHEET_URL_HERE' },
        sheetName: { __rl: true, mode: 'name', value: 'CORE' },
        columns: sheetColumns(),
        options: {},
      },
      id: 'a1000000-0000-4000-8000-000000000004',
      name: 'Sheets · CORE 적재',
      type: 'n8n-nodes-base.googleSheets',
      typeVersion: 4.5,
      position: [520, 180],
    },
    {
      parameters: {
        method: 'POST',
        url: 'YOUR_DISCORD_WEBHOOK_URL_HERE',
        sendBody: true,
        specifyBody: 'keypair',
        bodyParameters: { parameters: [{ name: 'content', value: discordText }] },
        options: {},
      },
      id: 'a1000000-0000-4000-8000-000000000005',
      name: 'Discord · CORE 알림',
      type: 'n8n-nodes-base.httpRequest',
      typeVersion: 4.2,
      position: [760, 180],
    },
    {
      parameters: {
        operation: 'append',
        documentId: { __rl: true, mode: 'url', value: 'YOUR_SPREADSHEET_URL_HERE' },
        sheetName: { __rl: true, mode: 'name', value: 'REF' },
        columns: sheetColumns(),
        options: {},
      },
      id: 'a1000000-0000-4000-8000-000000000006',
      name: 'Sheets · REF 적재',
      type: 'n8n-nodes-base.googleSheets',
      typeVersion: 4.5,
      position: [520, 420],
    },
  ],
  connections: {
    'RSS Feed Trigger': { main: [[{ node: '정규화+스코어링', type: 'main', index: 0 }]] },
    '정규화+스코어링': { main: [[{ node: '중요도 분기', type: 'main', index: 0 }]] },
    '중요도 분기': {
      main: [
        [{ node: 'Sheets · CORE 적재', type: 'main', index: 0 }],
        [{ node: 'Sheets · REF 적재', type: 'main', index: 0 }],
      ],
    },
    'Sheets · CORE 적재': { main: [[{ node: 'Discord · CORE 알림', type: 'main', index: 0 }]] },
  },
  settings: { executionOrder: 'v1', timezone: 'Asia/Seoul' },
  pinData: {},
};

fs.writeFileSync(__dirname + '/n8n_TRC_v1.json', JSON.stringify(wf, null, 2) + '\n', 'utf8');
console.log('written: n8n_TRC_v1.json');

// 검증: 재파싱 + Code 노드 로직이 문법적으로 유효한지 확인
const reparsed = JSON.parse(fs.readFileSync(__dirname + '/n8n_TRC_v1.json', 'utf8'));
const code = reparsed.nodes.find((n) => n.type === 'n8n-nodes-base.code').parameters.jsCode;
new Function('$input', code); // SyntaxError가 나면 여기서 throw
console.log('JSON 재파싱 OK / Code 노드 문법 OK');
console.log('노드 수:', reparsed.nodes.length, '| 커넥션 키:', Object.keys(reparsed.connections).length);
