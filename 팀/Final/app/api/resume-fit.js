/* =========================================================
   내 경험 연결 (이력서 × 기업 AI 약속), Vercel 서버 함수
   주소: /api/resume-fit

   GET  /api/resume-fit           → 준비 상태 (키가 들어 있는지, 쓸 모델). 모델을 부르지 않음
   GET  /api/resume-fit?check=1   → 짧은 시험 문장으로 모델 호출이 되는지 확인 (10분에 한 번만 실제 호출)
   POST /api/resume-fit           → { company: "samsung", resume: "이력서 글", role: "지원 직무(선택)" }

   10/20 v2: 이력서 경험 → 지원 직무에서 쓰는 역량 → 회사 AI 약속 순서로 잇고, 직접 연결과 간접 연결(한계 문장 필수)을 나누며,
   근거가 약하면 연결하지 않고 '이력서에 없는 부분'으로 보냅니다 (고친 화면을 본 사용자 후기 FB-08 반영).

   지키는 것
   - 이력서는 저장하지 않고 로그에도 남기지 않습니다. 분석을 위해 OpenAI API로만 보냅니다.
   - 회사 쪽 내용은 결과 파일(data/results.json)의 약속과 근거만 씁니다.
   - 근거 검사: 모델이 고른 약속 번호가 결과 파일에 있는지, 인용한 이력서 문장이 보낸 글에 그대로 있는지
     코드로 확인하고, 통과하지 못한 항목은 돌려주지 않습니다. 점수나 퍼센트가 든 문장도 뺍니다.
   - 환경 변수: OPENAI_API_KEY (필수), RESUME_MODEL (기본 gpt-6.1-sol), RESUME_FALLBACK_MODEL (기본 gpt-4o-mini)
   ========================================================= */
'use strict';

const fs = require('fs');
const path = require('path');

const MIN_CHARS = 80;
const MAX_CHARS = 6000;
const ROLE_MAX = 30;
const DEFAULT_LIMIT = '이 제품이나 기술을 직접 다룬 경험은 아니고, 지원 직무의 역량으로 옮겨 쓸 수 있는 경험입니다.';
const CALL_TIMEOUT_MS = 90000;
const RATE_WINDOW_MS = 10 * 60 * 1000;
const RATE_MAX = 6;                    // 같은 주소에서 10분에 6번까지 (서버 한 대 기준)
const FORBIDDEN = ['AI 워싱', 'AI워싱', '거짓', '약속을 어김', '약속을 어겼', '실행하지 않음', '실행하지 않았'];
const SCORE_RE = /\d+(\.\d+)?\s*(%|퍼센트|점\b|점입니다|점으로)|합격\s*(확률|가능성)|적합도\s*\d/;
const VERDICT_KO = {
  evidence_found: '근거 확인', partial: '일부 확인',
  not_verifiable: '공시에서 확인 불가', company_reported_not_pursued: '회사가 미추진으로 공시'
};

function model() { return process.env.RESUME_MODEL || 'gpt-6.1-sol'; }
function fallbackModel() { return process.env.RESUME_FALLBACK_MODEL || 'gpt-4o-mini'; }

const SCHEMA = {
  type: 'object', additionalProperties: false,
  required: ['summary', 'connections', 'gaps', 'talking_points', 'questions'],
  properties: {
    summary: { type: 'string' },
    connections: {
      type: 'array',
      items: {
        type: 'object', additionalProperties: false,
        required: ['level', 'promise_id', 'resume_quote', 'competency', 'role_link', 'why', 'limit'],
        properties: {
          level: { type: 'string', enum: ['direct', 'indirect'] },
          promise_id: { type: 'string' },
          resume_quote: { type: 'string' },
          competency: { type: 'string' },
          role_link: { type: 'string' },
          why: { type: 'string' },
          limit: { type: 'string' }
        }
      }
    },
    gaps: {
      type: 'array',
      items: {
        type: 'object', additionalProperties: false,
        required: ['promise_id', 'title', 'why', 'prepare'],
        properties: {
          promise_id: { type: 'string' },
          title: { type: 'string' },
          why: { type: 'string' },
          prepare: { type: 'array', items: { type: 'string' } }
        }
      }
    },
    talking_points: {
      type: 'array',
      items: {
        type: 'object', additionalProperties: false,
        required: ['promise_id', 'text'],
        properties: { promise_id: { type: 'string' }, text: { type: 'string' } }
      }
    },
    questions: {
      type: 'array',
      items: {
        type: 'object', additionalProperties: false,
        required: ['promise_id', 'text'],
        properties: { promise_id: { type: 'string' }, text: { type: 'string' } }
      }
    }
  }
};

const SYSTEM = [
  '당신은 취업 준비생의 면접 준비를 돕는 조수입니다.',
  '아래 [회사 AI 약속] 자료, [지원 직무], [이력서]만 근거로 씁니다.',
  '연결은 이 순서로 생각합니다: 이력서 경험 → 지원 직무에서 쓰는 역량 → 회사 AI 약속 → 면접에서 할 이야기.',
  '규칙:',
  '1. 회사에 대해서는 자료에 있는 약속, 판정, 근거 문장만 씁니다. 자료에 없는 실적, 계획, 숫자를 지어내지 않습니다.',
  '2. 판정이 "공시에서 확인 불가"인 약속은 실행됐다고 쓰지 않습니다. "회사가 미추진으로 공시"인 약속은 추진 중이라고 쓰지 않습니다.',
  '3. 경험을 회사 약속에 억지로 잇지 않습니다. 지원자가 그 제품이나 기술을 직접 다룬 것처럼 쓰지 않습니다. 경험이 특정 제품 약속과 직접 이어지지 않으면 그 제품에 붙이지 말고, 지원 직무에서 쓰는 역량(예: 사업성 검토, 시장 분석)이 회사의 AI 전략을 이해하고 검토하는 데 어떻게 쓰이는지로 씁니다.',
  '4. level은 둘 중 하나입니다. direct는 경험이 지원 직무에서 바로 쓰이고 약속 내용과도 직접 맞닿을 때만 씁니다. indirect는 직무 역량은 이어지지만 그 제품이나 기술을 다룬 경험은 아닐 때 씁니다. indirect의 limit에는 한계를 한 문장으로 적습니다(예: "갤럭시 제품을 개발한 경험은 아니고, 신규 사업의 사업성을 검토한 경험입니다."). direct의 limit은 빈 문자열입니다.',
  '5. 근거가 약한 연결은 넣지 않습니다. 이어지는 경험이 없으면 connections를 비워 두고 그 내용을 gaps에 적습니다.',
  '6. resume_quote는 이력서 글에서 그대로 복사한 연속된 한 구절(10~120자)입니다. 바꾸거나 요약하지 않습니다.',
  '7. promise_id는 자료에 있는 번호만 씁니다.',
  '8. competency는 옮겨 쓸 수 있는 역량 이름(20자 이내, 예: "시장·경쟁사 분석"), role_link는 지원 직무에서 그 역량이 어떻게 쓰이는지 한 문장, why는 회사 AI 약속과 어떻게 이어지는지 한 문장입니다.',
  '9. gaps는 최대 3개입니다. title은 이력서에서 확인되지 않은 경험이나 지식(20자 이내), why는 이 회사 약속과 지원 직무에서 왜 필요한지 한 문장, prepare는 면접 전에 준비할 것 2~4개(각 40자 이내, 자료의 약속과 근거로 공부할 거리)입니다.',
  '10. summary는 두 문장입니다. 첫 문장은 자료에서 이 회사가 강조하는 AI 방향, 둘째 문장은 지원자 경험이 지원 직무 기준으로 어디까지 이어지고 어디부터는 넓혀 말하면 안 되는지입니다. 지원 직무가 "선택하지 않음"이면 이력서 전체를 기준으로 씁니다.',
  '11. talking_points는 3개(면접에서 말할 1인칭 문장, 합니다체, 경험을 부풀리지 않음), questions는 2개(회사에 물어볼 질문, "~궁금합니다"로 끝냄)입니다.',
  '12. 점수, 퍼센트, 합격 가능성, 적합도 숫자를 쓰지 않습니다. "거짓", "AI 워싱" 같은 단정 표현을 쓰지 않습니다. 공시 내용을 회사의 "인재상"이라고 단정하지 않습니다.',
  '13. 이름, 연락처, 주소, 생년월일 같은 개인 정보는 결과에 옮기지 않습니다.',
  '출력은 지정한 JSON 형식 하나만.'
].join('\n');

/* ---------- 회사 자료 ---------- */
let RESULTS_CACHE = null;
async function loadResults(req) {
  if (RESULTS_CACHE) return RESULTS_CACHE;
  const candidates = [
    path.join(__dirname, '..', 'data', 'results.json'),
    path.join(process.cwd(), 'data', 'results.json'),
    path.join(process.cwd(), 'app', 'data', 'results.json')
  ];
  for (const p of candidates) {
    try { RESULTS_CACHE = JSON.parse(fs.readFileSync(p, 'utf8')); return RESULTS_CACHE; } catch (e) { /* 다음 후보 */ }
  }
  // 함수 묶음에 파일이 없으면 같은 배포의 정적 파일을 읽습니다
  const host = req && req.headers && req.headers.host;
  if (!host) throw new Error('results.json을 찾지 못했습니다');
  const r = await fetch('https://' + host + '/data/results.json');
  if (!r.ok) throw new Error('results.json을 읽지 못했습니다: HTTP ' + r.status);
  RESULTS_CACHE = await r.json();
  return RESULTS_CACHE;
}

function companyContext(c) {
  const lines = ['회사: ' + c.name];
  (c.promises || []).forEach(function (p) {
    const kind = p.type === 'directional' ? '방향성 약속(판정 없음)' : '구체적 약속, 판정: ' + (VERDICT_KO[p.verdict] || p.verdict);
    lines.push('');
    lines.push('[' + p.id + '] ' + p.title + ' (' + kind + ')');
    lines.push('약속 원문: ' + p.sentence);
    if (p.reason) lines.push('판정 이유: ' + p.reason);
    (p.evidence || []).filter(function (e) { return e.citation_verified === true; }).forEach(function (e) {
      lines.push('근거 원문(' + ((e.source || {}).report || '') + '): ' + e.sentence);
    });
  });
  return lines.join('\n');
}

/* ---------- 근거 검사 ---------- */
function squash(s) { return String(s || '').replace(/\s+/g, ' ').trim(); }
// 인용 비교는 띄어쓰기를 모두 빼고 합니다 (PDF에서 뽑은 글은 "했습니다 ." 처럼 띄어쓰기가 달라질 수 있어서)
function nospace(s) { return String(s || '').replace(/\s+/g, ''); }
function clean(s, max) { return squash(s).slice(0, max); }
// 지원 직무: 30자까지, 줄바꿈·꺾쇠 같은 글자는 빼요
function cleanRole(s) { return String(s || '').replace(/[\u0000-\u001f\u007f<>]/g, ' ').replace(/\s+/g, ' ').trim().slice(0, ROLE_MAX); }
function bad(text) {
  const t = String(text || '');
  return FORBIDDEN.some(function (w) { return t.indexOf(w) >= 0; }) || SCORE_RE.test(t);
}

function validate(raw, company, resume) {
  const byId = {};
  (company.promises || []).forEach(function (p) { byId[p.id] = p; });
  const resumeFlat = nospace(resume);
  let dropped = 0;
  function promiseInfo(pid) {
    const p = byId[pid];
    return p ? { promise_id: p.id, promise_title: p.title, verdict: p.verdict || null, type: p.type } : null;
  }
  function keep(list, max, test, build) {
    const out = [];
    (Array.isArray(list) ? list : []).forEach(function (it) {
      if (out.length >= max) { dropped += 1; return; }
      if (!it || !byId[it.promise_id] || !test(it)) { dropped += 1; return; }
      out.push(build(it));
    });
    return out;
  }
  const connections = keep(raw.connections, 3, function (it) {
    const q = nospace(it.resume_quote);
    return (it.level === 'direct' || it.level === 'indirect') && q.length >= 6 && resumeFlat.indexOf(q) >= 0 &&
      !bad(it.why) && !bad(it.role_link) && !bad(it.competency) && !bad(it.limit);
  }, function (it) {
    // 간접 연결에는 한계 문장이 꼭 붙어요. 모델이 비워 두면 기본 문장을 넣습니다
    const limit = it.level === 'indirect' ? (clean(it.limit, 200) || DEFAULT_LIMIT) : '';
    return Object.assign({
      level: it.level, competency: clean(it.competency, 40), resume_quote: clean(it.resume_quote, 160),
      role_link: clean(it.role_link, 300), why: clean(it.why, 300), limit: limit
    }, promiseInfo(it.promise_id));
  });
  const gaps = keep(raw.gaps, 3, function (it) { return squash(it.title).length > 0 && !bad(it.title) && !bad(it.why); }, function (it) {
    const list = Array.isArray(it.prepare) ? it.prepare : (it.prepare ? [it.prepare] : []);
    const prepare = list.map(function (s) { return clean(s, 120); }).filter(function (s) { return s && !bad(s); }).slice(0, 4);
    return Object.assign({ title: clean(it.title, 40), why: clean(it.why, 300), prepare: prepare }, promiseInfo(it.promise_id));
  });
  const talking = keep(raw.talking_points, 3, function (it) { return squash(it.text).length > 0 && !bad(it.text); }, function (it) {
    return Object.assign({ text: clean(it.text, 400) }, promiseInfo(it.promise_id));
  });
  const questions = keep(raw.questions, 2, function (it) { return squash(it.text).length > 0 && !bad(it.text); }, function (it) {
    return Object.assign({ text: clean(it.text, 300) }, promiseInfo(it.promise_id));
  });
  const summary = bad(raw.summary) ? '' : clean(raw.summary, 400);
  return { summary: summary, connections: connections, gaps: gaps, talking_points: talking, questions: questions, dropped: dropped };
}

/* ---------- 모델 호출 (Responses API) ---------- */
function outputText(j) {
  if (j && typeof j.output_text === 'string' && j.output_text) return j.output_text;
  const parts = [];
  ((j && j.output) || []).forEach(function (item) {
    (item.content || []).forEach(function (c) { if (c && c.type === 'output_text' && c.text) parts.push(c.text); });
  });
  return parts.join('');
}
function parseJson(text) {
  try { return JSON.parse(text); } catch (e) { /* 아래에서 다시 */ }
  const m = String(text || '').match(/\{[\s\S]*\}/);
  if (!m) return null;
  try { return JSON.parse(m[0]); } catch (e) { return null; }
}

async function callModel(name, system, user, withSchema, maxTokens) {
  const body = { model: name, input: [{ role: 'system', content: system }, { role: 'user', content: user }], max_output_tokens: maxTokens || 6000 };
  if (withSchema) body.text = { format: { type: 'json_schema', name: 'resume_fit', schema: SCHEMA, strict: true } };
  const ctrl = new AbortController();
  const timer = setTimeout(function () { ctrl.abort(); }, CALL_TIMEOUT_MS);
  try {
    const r = await fetch('https://api.openai.com/v1/responses', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json', Authorization: 'Bearer ' + process.env.OPENAI_API_KEY },
      body: JSON.stringify(body),
      signal: ctrl.signal
    });
    const j = await r.json().catch(function () { return {}; });
    if (!r.ok) {
      const err = new Error((j.error && j.error.message) || ('HTTP ' + r.status));
      err.status = r.status;
      throw err;
    }
    return outputText(j);
  } finally {
    clearTimeout(timer);
  }
}

// 설정한 모델(형식 지정) → 같은 모델(형식 없이) → 대체 모델(형식 지정) → 대체 모델(형식 없이)
async function runWithFallback(system, user, maxTokens) {
  const plan = [[model(), true], [model(), false], [fallbackModel(), true], [fallbackModel(), false]];
  const errors = [];
  for (let i = 0; i < plan.length; i++) {
    const name = plan[i][0], withSchema = plan[i][1];
    if (i > 0 && plan[i][0] === plan[i - 1][0] && plan[i][1] === plan[i - 1][1]) continue;
    try {
      const text = await callModel(name, system, user, withSchema, maxTokens);
      const data = parseJson(text);
      if (data) return { data: data, model: name };
      errors.push(name + ': JSON 아님');
    } catch (e) {
      errors.push(name + ': ' + String(e.message || e).slice(0, 160));
      if (e.status === 401) break;   // 키 문제는 다른 모델로도 안 됨
    }
  }
  const err = new Error('모델 호출 실패: ' + errors.join(' / '));
  err.errors = errors;
  throw err;
}

/* ---------- 같은 주소의 잦은 요청 막기 (서버 한 대 기준, 저장하지 않음) ---------- */
const hits = new Map();
function rateLimited(ip, now) {
  const list = (hits.get(ip) || []).filter(function (t) { return now - t < RATE_WINDOW_MS; });
  if (list.length >= RATE_MAX) { hits.set(ip, list); return true; }
  list.push(now); hits.set(ip, list);
  if (hits.size > 5000) hits.clear();
  return false;
}

let lastCheck = null;   // { at, result }

function send(res, status, payload) {
  res.statusCode = status;
  res.setHeader('Content-Type', 'application/json; charset=utf-8');
  res.setHeader('Cache-Control', 'no-store');
  res.end(JSON.stringify(payload));
}

async function readBody(req) {
  let given;
  try { given = req.body; } catch (e) { return null; }   // Vercel이 먼저 읽다가 형식 오류가 나면 여기로
  if (given && typeof given === 'object' && !Buffer.isBuffer(given)) return given;
  if (typeof given === 'string') { try { return JSON.parse(given); } catch (e) { return null; } }
  if (Buffer.isBuffer(given)) { try { return JSON.parse(given.toString('utf8')); } catch (e) { return null; } }
  const chunks = [];
  let size = 0;
  for await (const ch of req) {
    size += ch.length;
    if (size > 64 * 1024) return null;
    chunks.push(ch);
  }
  try { return JSON.parse(Buffer.concat(chunks).toString('utf8')); } catch (e) { return null; }
}

async function handler(req, res) {
  const configured = Boolean(process.env.OPENAI_API_KEY);
  if (req.method === 'GET') {
    const url = new URL(req.url, 'http://x');
    if (url.searchParams.get('check') !== '1') {
      return send(res, 200, { ok: true, configured: configured, model: model(), fallback_model: fallbackModel(), max_chars: MAX_CHARS });
    }
    if (!configured) return send(res, 200, { ok: false, configured: false, error: 'OPENAI_API_KEY가 없습니다' });
    const now = Date.now();
    if (lastCheck && now - lastCheck.at < RATE_WINDOW_MS) return send(res, 200, Object.assign({ cached: true }, lastCheck.result));
    let result;
    try {
      const out = await runWithFallback('JSON만 출력합니다.', '{"summary":"","connections":[],"gaps":[],"talking_points":[],"questions":[]} 와 같은 형식으로 빈 결과를 출력하세요.', 800);
      result = { ok: true, configured: true, model_used: out.model, checked_at: new Date(now).toISOString() };
    } catch (e) {
      result = { ok: false, configured: true, errors: e.errors || [String(e.message || e)], checked_at: new Date(now).toISOString() };
    }
    lastCheck = { at: now, result: result };
    return send(res, 200, result);
  }
  if (req.method !== 'POST') return send(res, 405, { ok: false, error: 'GET 또는 POST만 받아요' });
  if (!configured) return send(res, 503, { ok: false, error: '이 기능은 아직 준비 중이에요 (서버에 API 키가 없음)' });

  const ip = String((req.headers['x-forwarded-for'] || '').split(',')[0] || (req.socket && req.socket.remoteAddress) || 'unknown').trim();
  if (rateLimited(ip, Date.now())) return send(res, 429, { ok: false, error: '요청이 많아요. 10분 뒤에 다시 시도해 주세요.' });

  const body = await readBody(req);
  if (!body) return send(res, 400, { ok: false, error: '요청 형식이 맞지 않아요' });
  const resume = String(body.resume || '');
  if (resume.trim().length < MIN_CHARS) return send(res, 400, { ok: false, error: '이력서 내용을 ' + MIN_CHARS + '자 이상 넣어 주세요' });
  if (resume.length > MAX_CHARS) return send(res, 400, { ok: false, error: '이력서는 ' + MAX_CHARS.toLocaleString('ko-KR') + '자까지 넣을 수 있어요' });

  let data;
  try { data = await loadResults(req); } catch (e) { return send(res, 500, { ok: false, error: '회사 자료를 읽지 못했어요' }); }
  const company = (data.companies || []).filter(function (c) { return c.id === body.company; })[0];
  if (!company || !(company.promises || []).length) return send(res, 400, { ok: false, error: '분석을 마친 기업에서만 쓸 수 있어요' });

  const role = cleanRole(body.role);
  const user = '[회사 AI 약속]\n' + companyContext(company) + '\n\n[지원 직무]\n' + (role || '선택하지 않음') + '\n\n[이력서]\n' + resume;
  try {
    const out = await runWithFallback(SYSTEM, user);
    const result = validate(out.data, company, resume);
    return send(res, 200, Object.assign({ ok: true, company: company.id, role: role, model: out.model }, result));
  } catch (e) {
    // 이력서 내용은 남기지 않고, 실패 이유만 남깁니다
    console.error('[resume-fit] 모델 호출 실패', (e.errors || [String(e.message || e)]).join(' | ').slice(0, 500));
    return send(res, 502, { ok: false, error: '분석하지 못했어요. 잠시 뒤 다시 시도해 주세요.' });
  }
}

module.exports = handler;
module.exports._test = { validate: validate, companyContext: companyContext, outputText: outputText, parseJson: parseJson, rateLimited: rateLimited, SCHEMA: SCHEMA, runWithFallback: runWithFallback, cleanRole: cleanRole, DEFAULT_LIMIT: DEFAULT_LIMIT };
