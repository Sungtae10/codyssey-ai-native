/* =========================================================
   AI Promise 화면 4개
   1. 기업 고르기      #/
   2. 약속 목록        #/c/<기업id>
   3. 약속 자세히 보기  #/c/<기업id>/p/<약속id>
   4. 면접 카드        #/c/<기업id>/card

   데이터: data/results.json 이 있으면 그걸 쓰고,
           없으면 data/sample-data.js 의 예시 데이터를 써요.
   두 파일 모두 안내서 4장의 sample_data.json 형식이에요. (엔진 결과 파일과 같은 형식)

   1012 수정 (데이터 연결, 김성태): 안내서 형식을 그대로 읽게 바꾸고, 안내서 2장 규칙 9개에 맞췄어요.
   - 안내 문구 2개를 모든 화면에, 예시 데이터 안내를 맨 위에 (meta.is_sample)
   - 화면 문구는 데이터의 labels에서 읽기
   - 개수 요약은 구체적 약속만, 규칙 3의 형태로. 비율 막대는 뺌
   - 방향성 약속 묶음, "원문 확인됨" 표시, 면접 카드 안내 문구와 링크
   ========================================================= */
(function () {
  'use strict';

  /* ---------- 판정 4가지: 데이터 값 → 색 이름(css) ---------- */
  var VERDICT_ORDER = ['evidence_found', 'partial', 'not_verifiable', 'company_reported_not_pursued'];
  var CSS_NAME = {
    evidence_found: 'confirmed',
    partial: 'partial',
    not_verifiable: 'not_found',
    company_reported_not_pursued: 'not_pursued'
  };
  // labels가 없을 때만 쓰는 기본 문구 (안내서 2장과 같음)
  var DEFAULT_LABELS = {
    service_name: 'AI Promise',
    service_subtitle: '기업 AI 약속 검증',
    tagline: '면접 전 5분 기업 AI 체크',
    disclaimers: ['공시 범위 안에서 확인한 결과입니다.', 'AI가 생성한 분석입니다.'],
    verdicts: {
      evidence_found: { label: '근거 확인', short_label: '근거 확인' },
      partial: { label: '일부 확인', short_label: '일부 확인' },
      not_verifiable: { label: '공시에서 확인 불가', short_label: '확인 불가' },
      company_reported_not_pursued: { label: '회사가 미추진으로 공시', short_label: '미추진 공시' }
    },
    promise_types: {
      specific: { label: '구체적 약속', note: '' },
      directional: { label: '방향성 약속', note: '방향이 넓어 판정하지 않고 관련 활동만 보여줍니다. 개수에는 넣지 않습니다.' }
    },
    not_verifiable_message: '읽은 공시 범위에서 관련 내용을 찾지 못했습니다.',
    no_related_activity_message: '읽은 공시 범위에서 관련 활동을 찾지 못했습니다.',
    citation_verified_label: '원문 확인됨',
    interview_card_notice: '완성된 답변이 아니라 근거가 붙은 소재입니다. 자신의 말로 바꿔 쓰세요.'
  };

  var THEME_KEY = 'ai-promise-theme';
  var appEl = document.getElementById('app');
  var DATA = null;
  var L = DEFAULT_LABELS;

  /* ---------- 아이콘 ---------- */
  var ICON = {
    back: '<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" aria-hidden="true"><path d="M15 18l-6-6 6-6"/></svg>',
    chevron: '<svg class="chevron" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" aria-hidden="true"><path d="M9 6l6 6-6 6"/></svg>',
    shield: '<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M12 3l8 4v5c0 5-3.5 8-8 9-4.5-1-8-4-8-9V7z"/><path d="M8.5 12l2.5 2.5 4.5-5"/></svg>',
    sun: '<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" aria-hidden="true"><circle cx="12" cy="12" r="4"/><path d="M12 2v2M12 20v2M4.9 4.9l1.4 1.4M17.7 17.7l1.4 1.4M2 12h2M20 12h2M4.9 19.1l1.4-1.4M17.7 6.3l1.4-1.4"/></svg>',
    moon: '<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M20 14.5A8 8 0 1 1 9.5 4a6.5 6.5 0 0 0 10.5 10.5z"/></svg>',
    check: '<svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="3" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M5 12l5 5L20 7"/></svg>',
    dash: '<svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="3" stroke-linecap="round" aria-hidden="true"><path d="M6 12h12"/></svg>',
    down: '<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" aria-hidden="true"><path d="M12 5v14M6 13l6 6 6-6"/></svg>',
    external: '<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" aria-hidden="true"><path d="M14 4h6v6M20 4l-9 9"/></svg>',
    chat: '<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M21 12a8 8 0 0 1-11.5 7.2L4 20l1-4.6A8 8 0 1 1 21 12z"/></svg>'
  };

  /* ---------- 도구 ---------- */
  // 데이터 문장을 화면에 넣을 때 항상 거쳐요 (HTML로 해석되지 않게)
  function esc(value) {
    return String(value == null ? '' : value)
      .replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;')
      .replace(/"/g, '&quot;').replace(/'/g, '&#39;');
  }
  function verdictInfo(code) { return (L.verdicts && L.verdicts[code]) || DEFAULT_LABELS.verdicts[code] || null; }
  function verdictLabel(code) { var v = verdictInfo(code); return v ? v.label : ''; }
  function verdictShort(code) { var v = verdictInfo(code); return v ? (v.short_label || v.label) : ''; }
  function vClass(code) { return code && CSS_NAME[code] ? 'verdict-' + CSS_NAME[code] : 'verdict-none'; }
  function isSpecific(p) { return p.type !== 'directional'; }
  function specifics(company) { return (company.promises || []).filter(isSpecific); }
  function directionals(company) { return (company.promises || []).filter(function (p) { return !isSpecific(p); }); }
  function findCompany(id) {
    return (DATA.companies || []).filter(function (c) { return c.id === id; })[0] || null;
  }
  function findPromise(company, pid) {
    return (company.promises || []).filter(function (p) { return p.id === pid; })[0] || null;
  }
  function countVerdicts(promises) {
    var counts = {};
    VERDICT_ORDER.forEach(function (k) { counts[k] = 0; });
    (promises || []).forEach(function (p) { if (counts[p.verdict] != null) counts[p.verdict] += 1; });
    return counts;
  }
  // 규칙 3의 형태: "근거 확인 3, 일부 확인 1, 확인 불가 1, 미추진 공시 1"
  function countLine(promises) {
    var counts = countVerdicts(promises);
    return VERDICT_ORDER.map(function (k) { return verdictShort(k) + ' ' + counts[k]; }).join(', ');
  }
  function reportTitles(list) { return (list || []).map(function (r) { return r.title; }).join(', '); }
  function sourceLabel(src) {
    // 예: "2024 사업보고서 · II. 사업의 내용 · p.12" (쪽 번호가 있을 때만)
    var parts = [src.report];
    if (src.section) parts.push(src.section);
    if (src.page) parts.push('p.' + src.page);
    return parts.join(' · ');
  }
  function promiseHref(company, pid) {
    return '#/c/' + encodeURIComponent(company.id) + '/p/' + encodeURIComponent(pid);
  }

  /* ---------- 테마 ---------- */
  function currentTheme() { return document.documentElement.getAttribute('data-theme') || 'dark'; }
  function toggleTheme() {
    var next = currentTheme() === 'dark' ? 'light' : 'dark';
    document.documentElement.setAttribute('data-theme', next);
    try { localStorage.setItem(THEME_KEY, next); } catch (e) {}
    var btn = document.getElementById('theme-btn');
    if (btn) btn.innerHTML = themeIcon();
  }
  function themeIcon() { return currentTheme() === 'dark' ? ICON.sun : ICON.moon; }
  function themeButton() {
    return '<button type="button" class="icon-btn" id="theme-btn" aria-label="다크 모드와 라이트 모드 전환">' + themeIcon() + '</button>';
  }

  /* ---------- 공통 틀 ---------- */
  // 규칙 9: 예시 데이터일 때 화면 맨 위 안내
  function sampleBanner() {
    var meta = DATA.meta || {};
    if (!meta.is_sample) return '';
    return '<div class="sample-banner" role="note">' + esc(meta.notice || '예시 데이터입니다. 실제 기업이나 실제 공시 내용이 아닙니다.') + '</div>';
  }
  // 규칙 1: 안내 문구 2개를 모든 화면에
  function disclaimers() {
    return '<p class="disclaimer">' + (L.disclaimers || []).map(esc).join('<span aria-hidden="true"> · </span>') + '</p>';
  }
  function topbar(left) {
    return sampleBanner() + '<header class="topbar">' + left + themeButton() + '</header>';
  }
  function backLink(href, text) {
    return '<a class="back" href="' + href + '">' + ICON.back + esc(text) + '</a>';
  }
  function docLink(src, label) {
    if (src && src.url) {
      return '<a class="btn btn-secondary btn-sm" href="' + esc(src.url) + '" target="_blank" rel="noopener">' + esc(label) + ICON.external + '</a>';
    }
    return '<span class="btn btn-secondary btn-sm" aria-disabled="true" title="원문 링크가 아직 없어요">' + esc(label) + ICON.external + '</span>';
  }

  /* ---------- 화면 1: 기업 고르기 ---------- */
  function viewHome() {
    var companies = (DATA.companies || []).map(function (c) {
      var spec = specifics(c);
      var ready = (c.promises || []).length > 0;
      var reports = c.reports || {};
      var meta = ready
        ? '구체적 약속 ' + spec.length + '개 중 ' + countLine(spec)
        : '결과 준비 중';
      var inner =
        '<div class="company-logo" aria-hidden="true">' + esc(c.name.charAt(0)) + '</div>' +
        '<div class="company-info"><div class="company-name">' + esc(c.name) + '</div>' +
        '<div class="company-reports">' + esc('약속: ' + reportTitles(reports.promise) + ' · 근거: ' + reportTitles(reports.evidence)) + '</div>' +
        '<div class="company-meta">' + esc(meta) + '</div></div>' + ICON.chevron;
      return ready
        ? '<a class="company" href="#/c/' + encodeURIComponent(c.id) + '">' + inner + '</a>'
        : '<div class="company" aria-disabled="true">' + inner + '</div>';
    }).join('');

    var allReports = [];
    (DATA.companies || []).forEach(function (c) {
      var r = c.reports || {};
      (r.promise || []).concat(r.evidence || []).forEach(function (x) {
        if (allReports.indexOf(x.title) < 0) allReports.push(x.title);
      });
    });

    return topbar('<div class="brand">' + ICON.shield + esc(L.service_name) + '</div>') +
      '<main class="content">' + disclaimers() +
        '<section class="hero">' +
          '<p class="eyebrow">' + esc(L.service_subtitle) + ' · ' + esc(L.tagline) + '</p>' +
          '<h1 class="headline">면접 볼 회사의 AI 약속,<br><span class="hl">실제로 실행됐을까요?</span></h1>' +
          '<p class="lead">사업보고서 속 "하겠다"와 다음 해의 "했다"를 AI가 찾아 나란히 보여드려요.</p>' +
        '</section>' +
        '<section style="display:flex;flex-direction:column;gap:10px">' +
          '<h2 class="section-label">기업 고르기</h2>' +
          '<div class="company-list">' + companies + '</div>' +
        '</section>' +
        '<section class="card">' +
          '<h2 class="card-title" style="font-size:13px">이렇게 확인해요</h2>' +
          '<ol class="steps">' +
            '<li><span class="step-num">1</span>사업보고서에서 AI 약속 찾기</li>' +
            '<li><span class="step-num">2</span>다음 보고서에서 실행 근거 찾기</li>' +
            '<li><span class="step-num">3</span>근거 문장이 원문에 그대로 있는지 다시 확인</li>' +
          '</ol>' +
        '</section>' +
      '</main>' +
      '<footer class="bottombar"><p class="note">자료: 금융감독원 전자공시(DART)' + (allReports.length ? ' · ' + esc(allReports.join(', ')) : '') + '</p></footer>';
  }

  /* ---------- 화면 2: 약속 목록 ---------- */
  function promiseRow(company, p) {
    var tag = isSpecific(p)
      ? '<span class="verdict-text">' + esc(verdictLabel(p.verdict)) + '</span>'
      : '<span class="verdict-text">' + esc(L.promise_types.directional.label) + '</span>';
    return '<li><a class="promise-item ' + vClass(p.verdict) + '" href="' + promiseHref(company, p.id) + '">' +
      '<span class="verdict-dot" aria-hidden="true"></span>' +
      '<span class="promise-item-body"><span class="promise-item-title">' + esc(p.title) + '</span>' + tag + '</span>' + ICON.chevron +
    '</a></li>';
  }

  function viewList(company) {
    var spec = specifics(company);
    var dirs = directionals(company);
    var counts = countVerdicts(spec);
    var reports = company.reports || {};

    var grid = VERDICT_ORDER.map(function (k) {
      return '<div class="' + vClass(k) + '"><div class="summary-num">' + counts[k] + '</div>' +
        '<div class="summary-label">' + esc(verdictShort(k)) + '</div></div>';
    }).join('');
    var items = spec.map(function (p) { return promiseRow(company, p); }).join('');
    var dirBlock = dirs.length
      ? '<details class="directional">' +
          '<summary>' + esc(L.promise_types.directional.label) + ' ' + dirs.length + '개 (개수에 넣지 않음)</summary>' +
          '<p class="note">' + esc(L.promise_types.directional.note) + '</p>' +
          '<ul class="promise-list">' + dirs.map(function (p) { return promiseRow(company, p); }).join('') + '</ul>' +
        '</details>'
      : '';
    var nv = verdictInfo('not_verifiable') || {};

    return topbar(backLink('#/', '기업 선택')) +
      '<main class="content">' + disclaimers() +
        '<section style="display:flex;flex-direction:column;gap:6px">' +
          '<p class="eyebrow">' + esc(company.name) + '</p>' +
          '<p class="note">약속: ' + esc(reportTitles(reports.promise)) + ' · 근거: ' + esc(reportTitles(reports.evidence)) + '</p>' +
          '<h1 class="headline">구체적 약속 ' + spec.length + '개 중</h1>' +
          '<p class="count-line">' + esc(countLine(spec)) + '</p>' +
        '</section>' +
        '<section class="card" aria-label="판정별 개수">' +
          '<div class="summary-grid">' + grid + '</div>' +
        '</section>' +
        '<ul class="promise-list">' + items + '</ul>' +
        dirBlock +
        '<p class="note">' + esc(nv.label || '') + ': ' + esc(nv.meaning || '') + '</p>' +
      '</main>' +
      '<footer class="bottombar"><a class="btn btn-primary" href="#/c/' + encodeURIComponent(company.id) + '/card">면접 카드 보기</a></footer>';
  }

  /* ---------- 화면 3: 약속 자세히 보기 ---------- */
  function evidenceBlock(e, kindLabel) {
    var verified = e.citation_verified === true
      ? '<span class="verified">' + ICON.check + esc(L.citation_verified_label) + '</span>'
      : '';
    var link = e.source && e.source.url
      ? '<a class="ev-link" href="' + esc(e.source.url) + '" target="_blank" rel="noopener">원문 보기' + ICON.external + '</a>'
      : '';
    return '<div class="divider">' + ICON.down + '다음 보고서</div>' +
      '<div class="quote-block">' +
        '<div class="quote-meta is-evidence"><span>' + esc(kindLabel) + '</span><span>' + esc(sourceLabel(e.source || {})) + '</span></div>' +
        '<p class="quote-text">"' + esc(e.sentence) + '"</p>' +
        '<div class="ev-foot">' + verified + link + '</div>' +
      '</div>';
  }

  function viewDetail(company, p) {
    var listHref = '#/c/' + encodeURIComponent(company.id);
    var evidence = p.evidence || [];
    var specific = isSpecific(p);
    var kindLabel = !specific ? '관련 활동' : (p.verdict === 'company_reported_not_pursued' ? '회사가 적은 문장' : '실행 근거');
    var emptyMsg = specific ? L.not_verifiable_message : L.no_related_activity_message;

    var evidenceHtml = evidence.length
      ? evidence.map(function (e) { return evidenceBlock(e, kindLabel); }).join('')
      : '<div class="divider">' + ICON.down + '다음 보고서</div>' +
        '<div class="quote-block"><p class="quote-empty">' + esc(emptyMsg) + '</p></div>';

    // AI가 확인한 과정: 엔진이 실제로 남긴 값만 보여줘요 (검색 횟수, 원문 확인 개수)
    var verifiedCount = evidence.filter(function (e) { return e.citation_verified === true; }).length;
    var steps = [];
    if (p.search_attempts) steps.push([true, '근거를 찾으려고 검색 ' + p.search_attempts + '번']);
    if (evidence.length) {
      steps.push([verifiedCount === evidence.length, '찾은 문장 ' + evidence.length + '개 중 ' + verifiedCount + '개 ' + L.citation_verified_label]);
    } else {
      steps.push([false, '읽은 공시에서 ' + (specific ? '근거 문장' : '관련 활동') + '을 찾지 못함']);
    }
    var checkRows = steps.map(function (r) {
      return '<li><span class="check-icon ' + (r[0] ? 'ok' : 'no') + '">' + (r[0] ? ICON.check : ICON.dash) + '</span>' + esc(r[1]) + '</li>';
    }).join('');

    var pill = specific
      ? '<span class="verdict-pill">' + esc(verdictLabel(p.verdict)) + '</span>'
      : '<span class="verdict-pill">' + esc(L.promise_types.directional.label) + '</span>';
    var reasonHtml = specific && p.reason
      ? '<section style="display:flex;flex-direction:column;gap:6px">' +
          '<h2 class="card-title" style="font-size:13px">판정 이유</h2>' +
          '<p class="reason">' + esc(p.reason) + '</p>' +
        '</section>'
      : (!specific ? '<p class="note">' + esc(L.promise_types.directional.note) + '</p>' : '');

    var secondLink = evidence.length && evidence[0].source
      ? docLink(evidence[0].source, evidence[0].source.report + ' 원문')
      : '<a class="btn btn-secondary btn-sm" href="' + listHref + '">목록으로</a>';

    return topbar(backLink(listHref, '약속 목록')) +
      '<main class="content ' + vClass(p.verdict) + '">' + disclaimers() +
        '<section style="display:flex;flex-direction:column;gap:10px">' +
          pill +
          '<h1 class="detail-title">' + esc(p.title) + '</h1>' +
        '</section>' +
        '<section class="card compare" aria-label="약속과 근거 비교">' +
          '<div class="quote-block">' +
            '<div class="quote-meta"><span>약속</span><span>' + esc(sourceLabel(p.source || {})) + '</span></div>' +
            '<p class="quote-text">"' + esc(p.sentence) + '"</p>' +
          '</div>' + evidenceHtml +
        '</section>' +
        '<section class="card">' +
          '<h2 class="card-title" style="font-size:13px">AI가 확인한 과정</h2>' +
          '<ul class="checks">' + checkRows + '</ul>' +
        '</section>' +
        reasonHtml +
      '</main>' +
      '<footer class="bottombar two">' + docLink(p.source, ((p.source || {}).report || '약속') + ' 원문') + secondLink + '</footer>';
  }

  /* ---------- 화면 4: 면접 카드 ---------- */
  function viewCard(company) {
    var card = company.interview_card || {};
    var listHref = '#/c/' + encodeURIComponent(company.id);
    var issuesData = card.issues || [], tpData = card.talking_points || [], qData = card.questions || [];
    if (!issuesData.length && !tpData.length && !qData.length) {
      return topbar(backLink(listHref, '약속 목록')) +
        '<main class="content">' + disclaimers() + '<p class="empty">면접 카드를 준비하고 있어요.</p></main>';
    }
    function titleOf(pid) { var p = findPromise(company, pid); return p ? p.title : ''; }
    function verdictOf(pid) { var p = findPromise(company, pid); return p ? p.verdict : null; }

    var issues = issuesData.map(function (it, i) {
      var v = verdictOf(it.promise_id);
      return '<a class="issue ' + vClass(v) + '" href="' + promiseHref(company, it.promise_id) + '"><span class="issue-num">' + (i + 1) + '</span>' +
        '<div class="issue-body"><div class="issue-text">' + esc(it.text) + '</div></div>' + ICON.chevron + '</a>';
    }).join('');
    var answers = tpData.map(function (a) {
      var link = a.evidence_url
        ? '<a class="ev-link" href="' + esc(a.evidence_url) + '" target="_blank" rel="noopener">근거 원문' + ICON.external + '</a>'
        : '';
      return '<div class="answer">' +
        '<a class="answer-tag" href="' + promiseHref(company, a.promise_id) + '">' + esc(titleOf(a.promise_id)) + '</a>' +
        '<div class="answer-text">' + esc(a.text) + '</div>' + link + '</div>';
    }).join('');
    var questions = qData.map(function (q) {
      var text = typeof q === 'string' ? q : q.text;
      var inner = ICON.chat + '<div>' + esc(text) + '</div>';
      return q && q.promise_id
        ? '<a class="question" href="' + promiseHref(company, q.promise_id) + '">' + inner + '</a>'
        : '<div class="question">' + inner + '</div>';
    }).join('');

    return topbar(backLink(listHref, '약속 목록')) +
      '<main class="content">' + disclaimers() +
        '<section style="display:flex;flex-direction:column;gap:6px">' +
          '<p class="eyebrow">' + esc(company.name) + ' 면접 카드</p>' +
          '<h1 class="headline">면접 5분 전,<br>이것만 보고 들어가세요</h1>' +
          '<p class="note">' + esc(L.interview_card_notice) + '</p>' +
        '</section>' +
        '<section class="card"><h2 class="card-title">핵심 이슈 ' + issuesData.length + '</h2>' + issues + '</section>' +
        '<section class="card"><h2 class="card-title">답변 소재 ' + tpData.length + '</h2>' + answers + '</section>' +
        '<section class="card"><h2 class="card-title">면접관에게 할 역질문 ' + qData.length + '</h2>' + questions + '</section>' +
      '</main>' +
      '<footer class="bottombar two">' +
        '<button type="button" class="btn btn-secondary" id="copy-btn">카드 복사하기</button>' +
        '<a class="btn btn-primary" href="#/">다른 기업 보기</a>' +
      '</footer>';
  }

  function cardAsText(company) {
    var card = company.interview_card || {};
    var lines = ['[' + company.name + ' 면접 카드]', L.interview_card_notice, '', '핵심 이슈'];
    (card.issues || []).forEach(function (it, i) { lines.push((i + 1) + '. ' + it.text); });
    lines.push('', '답변 소재');
    (card.talking_points || []).forEach(function (a) {
      lines.push('- ' + a.text + (a.evidence_url ? ' (근거: ' + a.evidence_url + ')' : ''));
    });
    lines.push('', '역질문');
    (card.questions || []).forEach(function (q) { lines.push('- ' + (typeof q === 'string' ? q : q.text)); });
    lines.push('', (L.disclaimers || []).join(' '));
    return lines.join('\n');
  }

  function copyText(text) {
    if (navigator.clipboard && window.isSecureContext) return navigator.clipboard.writeText(text);
    return new Promise(function (resolve, reject) {
      var ta = document.createElement('textarea');
      ta.value = text; ta.setAttribute('readonly', ''); ta.style.position = 'fixed'; ta.style.opacity = '0';
      document.body.appendChild(ta); ta.select();
      try { document.execCommand('copy') ? resolve() : reject(); } catch (e) { reject(e); }
      document.body.removeChild(ta);
    });
  }

  function toast(message) {
    var el = document.createElement('div');
    el.className = 'toast'; el.setAttribute('role', 'status'); el.textContent = message;
    document.body.appendChild(el);
    setTimeout(function () { el.remove(); }, 1800);
  }

  /* ---------- 주소(#)에 맞는 화면 그리기 ---------- */
  function notFound() {
    return topbar(backLink('#/', '처음으로')) + '<main class="content">' + disclaimers() + '<p class="empty">찾는 화면이 없어요.</p></main>';
  }

  function render() {
    var parts = (location.hash.replace(/^#\/?/, '') || '').split('/').filter(Boolean).map(decodeURIComponent);
    var html, title = L.service_name;
    var company = parts[0] === 'c' ? findCompany(parts[1]) : null;

    if (parts.length === 0) {
      html = viewHome();
    } else if (company && parts.length === 2) {
      html = viewList(company); title = company.name + ' 약속 목록';
    } else if (company && parts[2] === 'p' && findPromise(company, parts[3])) {
      var p = findPromise(company, parts[3]);
      html = viewDetail(company, p); title = p.title;
    } else if (company && parts[2] === 'card') {
      html = viewCard(company); title = company.name + ' 면접 카드';
    } else {
      html = notFound();
    }

    appEl.innerHTML = html;
    document.title = title + ' | ' + L.service_name;
    window.scrollTo(0, 0);

    var themeBtn = document.getElementById('theme-btn');
    if (themeBtn) themeBtn.addEventListener('click', toggleTheme);
    var copyBtn = document.getElementById('copy-btn');
    if (copyBtn && company) {
      copyBtn.addEventListener('click', function () {
        copyText(cardAsText(company))
          .then(function () { toast('면접 카드를 복사했어요'); })
          .catch(function () { toast('복사하지 못했어요. 직접 선택해 주세요'); });
      });
    }
  }

  /* ---------- 시작: 결과 파일 → 없으면 예시 데이터 ---------- */
  function start(data) {
    DATA = data || { companies: [] };
    var labels = DATA.labels || {};
    L = {};
    Object.keys(DEFAULT_LABELS).forEach(function (k) { L[k] = labels[k] != null ? labels[k] : DEFAULT_LABELS[k]; });
    if (!L.promise_types.directional) L.promise_types = DEFAULT_LABELS.promise_types;
    window.addEventListener('hashchange', render);
    render();
  }

  fetch('data/results.json', { cache: 'no-store' })
    .then(function (res) { if (!res.ok) throw new Error('no results'); return res.json(); })
    .then(function (data) { start(data); })
    .catch(function () { start(window.AI_PROMISE_SAMPLE); });
})();
