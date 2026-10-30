/* 내 경험 연결 서버 함수 검사 (인터넷, API 키 없이 몇 초)
   실행: node tests/test_resume_api.js   (마지막 줄 "이력서 연결 함수 검사 통과")

   1. 근거 검사: 없는 약속 번호, 이력서에 없는 인용, 점수·단정 표현이 든 항목은 빠지고 개수 제한을 지키는지
      (10/20 v2) 직접/간접 연결만 받고, 간접 연결에는 한계 문장이 꼭 붙고, 보완점의 '면접 전에 준비할 것' 목록도 검사하는지
   1-1. 지원 직무: 30자까지 자르고 줄바꿈·꺾쇠를 빼는지, 모델에 [지원 직무]로 전해지는지
   2. 준비 상태(GET): 키가 없으면 configured: false, POST는 503
   3. POST 정상: 가짜 OpenAI 응답으로 결과가 나오고, 회사 쪽 정보는 결과 파일에서 붙는지
   4. 대체 모델: 설정한 모델이 실패하면 대체 모델로 넘어가는지
   5. 입력 검사: 너무 짧거나 긴 이력서, 결과 파일에 없는 기업은 400
   6. 같은 주소에서 너무 자주 부르면 429
*/
'use strict';
const path = require('path');
const assert = require('assert');

const handler = require(path.join(__dirname, '..', 'app', 'api', 'resume-fit.js'));
const T = handler._test;
const problems = [];
function check(cond, msg) { if (!cond) problems.push(msg); }

const RESUME = [
  '기술경영 석사과정에서 기업 공시 문서를 LLM으로 분석하는 연구를 하고 있습니다.',
  '반도체 기업 전략팀 인턴으로 HBM 시장 자료를 정리하고 경쟁사 투자 계획을 비교했습니다.',
  'Python으로 데이터 파이프라인을 만들고 대시보드로 공유했습니다.'
].join('\n');

const COMPANY = {
  id: 'samsung', name: '삼성전자',
  promises: [
    { id: 'samsung-p1', type: 'specific', title: '갤럭시 AI 확대', sentence: '...', verdict: 'evidence_found', reason: 'r', evidence: [{ sentence: 'e', citation_verified: true, source: { report: '2025 사업보고서' } }] },
    { id: 'samsung-p2', type: 'specific', title: 'HBM4 양산', sentence: '...', verdict: 'partial', reason: 'r', evidence: [] },
    { id: 'samsung-d1', type: 'directional', title: '방향', sentence: '...', verdict: null, reason: null, evidence: [] }
  ]
};

// 1) 근거 검사 (10/20 v2: 직접/간접 연결, 한계 문장, 준비할 것 목록)
const raw = {
  summary: '삼성전자는 자료에서 HBM과 갤럭시 AI 확대를 강조합니다. 시장 분석 경험은 전략 검토에 이어지지만 제품 개발 경험으로 넓혀 말하면 안 됩니다.',
  connections: [
    { level: 'direct', promise_id: 'samsung-p2', resume_quote: '반도체 기업 전략팀 인턴으로 HBM 시장 자료를 정리하고', competency: '시장·경쟁사 분석', role_link: '전략기획에서 시장 분석에 바로 씁니다.', why: 'HBM 양산 약속의 시장 상황을 이해하는 데 이어집니다.', limit: '' },
    { level: 'indirect', promise_id: 'samsung-p1', resume_quote: '이력서에 없는 문장입니다', competency: 'x', role_link: 'x', why: 'x', limit: 'x' },
    { level: 'indirect', promise_id: 'samsung-p9', resume_quote: 'Python으로 데이터 파이프라인을 만들고', competency: 'x', role_link: 'x', why: 'x', limit: 'x' },
    { level: 'indirect', promise_id: 'samsung-p1', resume_quote: 'Python으로   데이터 파이프라인을\n만들고', competency: '데이터 처리', role_link: '적합도 90점입니다', why: 'x', limit: '' },
    { level: 'indirect', promise_id: 'samsung-p1', resume_quote: 'Python으로   데이터 파이프라인을\n만들고', competency: '데이터 처리', role_link: '데이터로 사업 현황을 정리하는 데 씁니다.', why: 'AI 기능 확대 현황을 숫자로 보는 데 이어집니다.', limit: '' },
    { level: 'weird', promise_id: 'samsung-p1', resume_quote: 'Python으로 데이터 파이프라인을 만들고', competency: 'x', role_link: 'x', why: 'x', limit: '' },
    { category: 'strong', promise_id: 'samsung-p1', resume_quote: 'Python으로 데이터 파이프라인을 만들고', why: '예전 형식(level 없음)' }
  ],
  gaps: [
    { promise_id: 'samsung-p1', title: '모바일 제품 경험', why: '갤럭시 AI 확대 약속을 이해하려면 필요합니다.', prepare: ['갤럭시 AI 주요 기능 정리', '합격 확률 높이기', '온디바이스 AI와 클라우드 AI 차이'] },
    { promise_id: 'samsung-p1', title: '', why: '제목 없음', prepare: [] },
    { promise_id: 'samsung-p2', title: '양산 공정 지식', why: 'HBM4 양산 약속과 이어집니다.', prepare: '공정 기초 공부' }
  ],
  talking_points: [
    { promise_id: 'samsung-p2', text: '저는 HBM 시장 자료를 정리한 경험이 있습니다.' },
    { promise_id: 'samsung-p1', text: '이 회사는 거짓 약속을 했습니다.' },
    { promise_id: 'samsung-p1', text: '합격 확률을 높이겠습니다.' },
    { promise_id: 'samsung-p1', text: '데이터 파이프라인 경험으로 AI 기능 확대를 돕겠습니다.' },
    { promise_id: 'samsung-p2', text: '네 번째 포인트입니다.' },
    { promise_id: 'samsung-p2', text: '다섯 번째 포인트입니다.' }
  ],
  questions: [
    { promise_id: 'samsung-p2', text: 'HBM4 양산 일정이 궁금합니다.' },
    { promise_id: 'samsung-d1', text: '방향성 약속의 다음 단계가 궁금합니다.' },
    { promise_id: 'samsung-p1', text: '세 번째 질문이 궁금합니다.' }
  ]
};
const v = T.validate(raw, COMPANY, RESUME);
check(v.connections.length === 2, '연결 2개만 남아야 함: ' + v.connections.length);
check(v.connections[0].promise_title === 'HBM4 양산' && v.connections[0].verdict === 'partial', '연결에 결과 파일의 약속 제목과 판정이 붙어야 함');
check(v.connections[0].level === 'direct' && v.connections[0].limit === '' && v.connections[0].competency === '시장·경쟁사 분석', '직접 연결은 한계 문장 없이 역량 이름과 함께');
check(v.connections[1].level === 'indirect' && v.connections[1].limit === T.DEFAULT_LIMIT, '간접 연결은 한계 문장이 비어 있으면 기본 문장이 붙어야 함');
check(v.connections.every(function (c) { return RESUME.replace(/\s+/g, '').indexOf(c.resume_quote.replace(/\s+/g, '')) >= 0; }), '남은 인용은 이력서에 그대로 있어야 함 (띄어쓰기 무시)');
const v2 = T.validate({ summary: '', connections: [{ level: 'direct', promise_id: 'samsung-p2', resume_quote: '정리했습니다. Python으로', competency: 'a', role_link: 'b', why: 'PDF 띄어쓰기', limit: '' }], gaps: [], talking_points: [], questions: [] }, COMPANY, '자료를 정리했습니다 . Python 으로 만들었습니다');
check(v2.connections.length === 1, 'PDF에서 띄어쓰기가 달라진 인용도 같은 글자면 통과해야 함');
check(v.gaps.length === 2, '보완할 점 2개(제목 없는 것은 빠짐): ' + v.gaps.length);
check(v.gaps[0].prepare.length === 2 && v.gaps[0].prepare.join(' ').indexOf('합격') < 0, '준비할 것에서 합격 표현은 빠져야 함: ' + JSON.stringify(v.gaps[0].prepare));
check(Array.isArray(v.gaps[1].prepare) && v.gaps[1].prepare[0] === '공정 기초 공부', '준비할 것이 글 하나로 와도 목록으로 바뀌어야 함');
check(v.summary.indexOf('삼성전자는') === 0, '요약 문장이 남아야 함');
check(T.validate({ summary: '적합도 90점입니다', connections: [], gaps: [], talking_points: [], questions: [] }, COMPANY, RESUME).summary === '', '점수 표현이 든 요약은 빈 문자열');
check(v.talking_points.length === 3, '포인트는 3개로 제한: ' + v.talking_points.length);
check(v.talking_points.every(function (t) { return t.text.indexOf('거짓') < 0 && t.text.indexOf('합격') < 0; }), '단정 표현·합격 표현 포인트는 빠져야 함');
check(v.questions.length === 2, '질문은 2개로 제한');
check(v.dropped === 5 + 1 + 3 + 1, '빠진 항목 수(연결 5, 보완점 1, 포인트 3, 질문 1): ' + v.dropped);

// 1-1) 지원 직무 정리
check(T.cleanRole('  재무·투자  ') === '재무·투자', '직무 앞뒤 공백 정리');
check(T.cleanRole('<script>x</script>').indexOf('<') < 0 && T.cleanRole('<script>x</script>').indexOf('>') < 0, '직무에서 꺾쇠는 빠져야 함');
check(T.cleanRole('가'.repeat(50)).length === 30, '직무는 30자까지');
check(T.cleanRole('전략\n기획') === '전략 기획', '직무의 줄바꿈은 공백으로');

// 회사 자료에는 인용 검사 통과 근거만
const ctx = T.companyContext({ name: 'X', promises: [{ id: 'a', type: 'specific', title: 't', sentence: 's', verdict: 'partial', evidence: [
  { sentence: '통과한 근거', citation_verified: true, source: { report: 'R' } }, { sentence: '실패한 근거', citation_verified: false, source: { report: 'R' } }] }] });
check(ctx.indexOf('통과한 근거') >= 0 && ctx.indexOf('실패한 근거') < 0, '회사 자료에는 인용 검사 통과 근거만 넣어야 함');
check(T.outputText({ output: [{ type: 'reasoning' }, { type: 'message', content: [{ type: 'output_text', text: '{"a":1}' }] }] }) === '{"a":1}', 'Responses API 출력 읽기');

function fakeRes() {
  return { statusCode: 0, headers: {}, body: '', setHeader: function (k, v2) { this.headers[k] = v2; }, end: function (s) { this.body = s; } };
}
async function call(method, body, ip, url) {
  const req = { method: method, url: url || '/api/resume-fit', headers: { 'x-forwarded-for': ip || '1.1.1.1', host: 'example.test' }, body: body };
  const res = fakeRes();
  await handler(req, res);
  return { status: res.statusCode, json: JSON.parse(res.body || '{}') };
}

(async function main() {
  // 2) 키 없음
  delete process.env.OPENAI_API_KEY;
  let r = await call('GET');
  check(r.status === 200 && r.json.configured === false, 'GET: 키가 없으면 configured false');
  r = await call('POST', { company: 'samsung', resume: RESUME });
  check(r.status === 503, 'POST: 키가 없으면 503, 받은 값 ' + r.status);

  // 3) 정상 (가짜 OpenAI)
  process.env.OPENAI_API_KEY = 'test-key';
  const seen = [];
  global.fetch = async function (url, opts) {
    const body = JSON.parse(opts.body);
    seen.push({ model: body.model, schema: Boolean(body.text), user: (body.input && body.input[1] && body.input[1].content) || '' });
    const realIds = require(path.join(__dirname, '..', 'app', 'data', 'results.json')).companies.filter(function (c) { return c.id === 'samsung'; })[0].promises.map(function (p) { return p.id; });
    const out = { summary: '요약입니다. 두 번째 문장입니다.',
      connections: [{ level: 'indirect', promise_id: realIds[1], resume_quote: '반도체 기업 전략팀 인턴으로 HBM 시장 자료를 정리하고', competency: '시장 분석', role_link: '재무·투자 직무에서 사업성 검토에 씁니다.', why: 'HBM 관련 경험이 이어집니다.', limit: 'HBM을 직접 개발한 경험은 아닙니다.' }],
      gaps: [{ promise_id: realIds[1], title: '양산 공정 지식', why: '약속과 이어집니다.', prepare: ['공정 기초', '최근 공시 읽기'] }], talking_points: [{ promise_id: realIds[1], text: '저는 HBM 시장 자료를 정리했습니다.' }], questions: [{ promise_id: realIds[1], text: '양산 계획이 궁금합니다.' }] };
    if (global.FAIL_FIRST && seen.length <= 2) return { ok: false, status: 404, json: async function () { return { error: { message: 'model not found' } }; } };
    return { ok: true, status: 200, json: async function () { return { output: [{ type: 'message', content: [{ type: 'output_text', text: JSON.stringify(out) }] }] }; } };
  };
  r = await call('POST', { company: 'samsung', resume: RESUME, role: ' 재무·투자 ' }, '2.2.2.2');
  check(r.status === 200 && r.json.ok === true, 'POST 정상: 200, 받은 값 ' + r.status + ' ' + JSON.stringify(r.json).slice(0, 200));
  check(r.json.model === 'gpt-6.1-sol', '기본 모델 gpt-6.1-sol: ' + r.json.model);
  check(r.json.connections && r.json.connections.length === 1 && r.json.connections[0].promise_title, '결과에 약속 제목이 붙어야 함');
  check(seen[0].schema === true, '첫 호출은 JSON 형식 지정');
  check(seen[0].user.indexOf('[지원 직무]\n재무·투자\n') >= 0, '모델에 지원 직무가 [지원 직무]로 전해져야 함');
  check(r.json.role === '재무·투자', '결과에 정리한 지원 직무가 붙어야 함: ' + r.json.role);
  check(r.json.connections[0].level === 'indirect' && r.json.connections[0].limit === 'HBM을 직접 개발한 경험은 아닙니다.', '간접 연결과 한계 문장이 결과에 있어야 함');
  check(r.json.gaps.length === 1 && r.json.gaps[0].prepare.length === 2 && r.json.summary === '요약입니다. 두 번째 문장입니다.', '보완점(준비할 것)과 요약이 결과에 있어야 함');

  // 4) 대체 모델
  global.FAIL_FIRST = true; seen.length = 0;
  r = await call('POST', { company: 'samsung', resume: RESUME }, '3.3.3.3');
  check(seen[0].user.indexOf('[지원 직무]\n선택하지 않음\n') >= 0, '직무를 안 고르면 "선택하지 않음"으로 전해져야 함');
  check(r.status === 200 && r.json.model === 'gpt-4o-mini', '설정 모델 2번 실패 후 대체 모델: ' + r.json.model + ' 호출 ' + JSON.stringify(seen));
  global.FAIL_FIRST = false;

  // 5) 입력 검사
  r = await call('POST', { company: 'samsung', resume: '짧음' }, '4.4.4.4');
  check(r.status === 400, '짧은 이력서는 400');
  r = await call('POST', { company: 'samsung', resume: 'ㄱ'.repeat(6001) }, '4.4.4.4');
  check(r.status === 400, '6,000자 넘으면 400');
  // 10/19: 카카오는 이제 분석 완료 기업이라, 결과 파일에 없는 기업 id로 시험합니다
  r = await call('POST', { company: 'no-such-company', resume: RESUME }, '4.4.4.4');
  check(r.status === 400, '분석 안 된(결과 파일에 없는) 기업은 400이어야 함, 받은 값 ' + r.status);

  // 6) 같은 주소 반복
  let last = 0;
  for (let i = 0; i < 7; i++) { last = (await call('POST', { company: 'samsung', resume: RESUME }, '9.9.9.9')).status; }
  check(last === 429, '같은 주소 7번째는 429, 받은 값 ' + last);

  if (problems.length) {
    console.log('이력서 연결 함수 검사 실패:');
    problems.forEach(function (p) { console.log(' -', p); });
    process.exit(1);
  }
  console.log('이력서 연결 함수 검사 통과');
})().catch(function (e) { console.log('검사 중 오류:', e); process.exit(1); });
