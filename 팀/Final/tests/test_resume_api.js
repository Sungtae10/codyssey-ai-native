/* 내 경험 연결 서버 함수 검사 (인터넷, API 키 없이 몇 초)
   실행: node tests/test_resume_api.js   (마지막 줄 "이력서 연결 함수 검사 통과")

   1. 근거 검사: 없는 약속 번호, 이력서에 없는 인용, 점수·단정 표현이 든 항목은 빠지고 개수 제한을 지키는지
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

// 1) 근거 검사
const raw = {
  connections: [
    { category: 'strong', promise_id: 'samsung-p2', resume_quote: '반도체 기업 전략팀 인턴으로 HBM 시장 자료를 정리하고', why: 'HBM 양산 약속과 시장 자료 정리 경험이 이어집니다.' },
    { category: 'related', promise_id: 'samsung-p1', resume_quote: '이력서에 없는 문장입니다', why: 'x' },
    { category: 'related', promise_id: 'samsung-p9', resume_quote: 'Python으로 데이터 파이프라인을 만들고', why: 'x' },
    { category: 'related', promise_id: 'samsung-p1', resume_quote: 'Python으로   데이터 파이프라인을\n만들고', why: '적합도 90점입니다' },
    { category: 'related', promise_id: 'samsung-p1', resume_quote: 'Python으로   데이터 파이프라인을\n만들고', why: '데이터 경험을 AI 기능 확대에 연결합니다.' },
    { category: 'weird', promise_id: 'samsung-p1', resume_quote: 'Python으로 데이터 파이프라인을 만들고', why: 'x' }
  ],
  gaps: [{ promise_id: 'samsung-p1', why: '모바일 제품 경험이 적습니다.', prepare: '갤럭시 AI 기능을 직접 써 보고 정리합니다.' }],
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
check(v.connections.every(function (c) { return RESUME.replace(/\s+/g, '').indexOf(c.resume_quote.replace(/\s+/g, '')) >= 0; }), '남은 인용은 이력서에 그대로 있어야 함 (띄어쓰기 무시)');
const v2 = T.validate({ connections: [{ category: 'strong', promise_id: 'samsung-p2', resume_quote: '정리했습니다. Python으로', why: 'PDF 띄어쓰기' }], gaps: [], talking_points: [], questions: [] }, COMPANY, '자료를 정리했습니다 . Python 으로 만들었습니다');
check(v2.connections.length === 1, 'PDF에서 띄어쓰기가 달라진 인용도 같은 글자면 통과해야 함');
check(v.talking_points.length === 3, '포인트는 3개로 제한: ' + v.talking_points.length);
check(v.talking_points.every(function (t) { return t.text.indexOf('거짓') < 0 && t.text.indexOf('합격') < 0; }), '단정 표현·합격 표현 포인트는 빠져야 함');
check(v.questions.length === 2, '질문은 2개로 제한');
check(v.gaps.length === 1, '보완할 점 1개');
check(v.dropped === 4 + 3 + 1, '빠진 항목 수(연결 4, 포인트 3, 질문 1): ' + v.dropped);

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
    seen.push({ model: body.model, schema: Boolean(body.text) });
    const realIds = require(path.join(__dirname, '..', 'app', 'data', 'results.json')).companies.filter(function (c) { return c.id === 'samsung'; })[0].promises.map(function (p) { return p.id; });
    const out = { connections: [{ category: 'strong', promise_id: realIds[1], resume_quote: '반도체 기업 전략팀 인턴으로 HBM 시장 자료를 정리하고', why: 'HBM 관련 경험이 이어집니다.' }],
      gaps: [], talking_points: [{ promise_id: realIds[1], text: '저는 HBM 시장 자료를 정리했습니다.' }], questions: [{ promise_id: realIds[1], text: '양산 계획이 궁금합니다.' }] };
    if (global.FAIL_FIRST && seen.length <= 2) return { ok: false, status: 404, json: async function () { return { error: { message: 'model not found' } }; } };
    return { ok: true, status: 200, json: async function () { return { output: [{ type: 'message', content: [{ type: 'output_text', text: JSON.stringify(out) }] }] }; } };
  };
  r = await call('POST', { company: 'samsung', resume: RESUME }, '2.2.2.2');
  check(r.status === 200 && r.json.ok === true, 'POST 정상: 200, 받은 값 ' + r.status + ' ' + JSON.stringify(r.json).slice(0, 200));
  check(r.json.model === 'gpt-6.1-sol', '기본 모델 gpt-6.1-sol: ' + r.json.model);
  check(r.json.connections && r.json.connections.length === 1 && r.json.connections[0].promise_title, '결과에 약속 제목이 붙어야 함');
  check(seen[0].schema === true, '첫 호출은 JSON 형식 지정');

  // 4) 대체 모델
  global.FAIL_FIRST = true; seen.length = 0;
  r = await call('POST', { company: 'samsung', resume: RESUME }, '3.3.3.3');
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
