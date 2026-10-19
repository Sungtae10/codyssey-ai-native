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

   1019 Final v5 + 사실 맞춤 (김성태):
   - 첫 화면은 회사 검색이 중심. 검색 결과는 3가지 상태로 보여줘요:
     분석 완료(결과 열기) / 분석 준비 중(데이터에 있지만 약속이 아직 없음) / 상장 기업이지만 아직 분석 전.
     상장 기업 여부는 data/listed-companies.json(한국거래소 상장 종목, 기준일 표시)에서만 확인해요.
     실제로 없는 기능(즉석 분석 버튼 등)은 만들지 않아요.
   - 누가 했는지는 meta로 정해요: data_mode가 human_reviewed_demo면 '사람이 원문 대조',
     data_mode 없이 is_sample이면 '예시 데이터', 그 밖(엔진 결과)은 'AI 엔진'.
   - 화면 문구는 한국어로, 링크는 http(s) 주소만 만들어요.
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
  var LISTED = null;            // data/listed-companies.json (상장 기업 목록). 첫 화면 검색에서만 써요
  var LISTED_STATE = 'idle';    // idle, loading, ready, failed

  // 검색 별칭: 영어 이름이나 줄임말로 찾아도 나오게 (데이터에 있는 기업 id 기준)
  var COMPANY_ALIASES = {
    samsung: ['samsung', 'samsungelectronics'],
    skhynix: ['skhynix', 'hynix'],
    kakao: ['kakao'],
    shinhanbank: ['shinhan', 'shinhanbank'],
    naver: ['네이버']
  };
  // 상장 종목 이름이 흔히 부르는 이름과 다른 경우 (예: 현대자동차는 상장 종목 이름이 '현대차')
  var QUERY_ALIASES = {
    '현대자동차': '현대차', '기아자동차': '기아', '네이버': 'naver', '포스코': 'posco',
    '엘지': 'lg', '에스케이': 'sk', '케이티': 'kt', '신한금융': '신한지주', '케이비': 'kb'
  };

  /* ---------- 아이콘 ---------- */
  var ICON = {
    back: '<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" aria-hidden="true"><path d="M15 18l-6-6 6-6"/></svg>',
    chevron: '<svg class="chevron" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" aria-hidden="true"><path d="M9 6l6 6-6 6"/></svg>',
    shield: '<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M12 3l8 4v5c0 5-3.5 8-8 9-4.5-1-8-4-8-9V7z"/><path d="M8.5 12l2.5 2.5 4.5-5"/></svg>',
    sun: '<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" aria-hidden="true"><circle cx="12" cy="12" r="4"/><path d="M12 2v2M12 20v2M4.9 4.9l1.4 1.4M17.7 17.7l1.4 1.4M2 12h2M20 12h2M4.9 19.1l1.4-1.4M17.7 6.3l1.4-1.4"/></svg>',
    moon: '<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M20 14.5A8 8 0 1 1 9.5 4a6.5 6.5 0 0 0 10.5 10.5z"/></svg>',
    check: '<svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="3" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M5 12l5 5L20 7"/></svg>',
    dash: '<svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="3" stroke-linecap="round" aria-hidden="true"><path d="M6 12h12"/></svg>',
    search: '<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" aria-hidden="true"><circle cx="11" cy="11" r="7"/><path d="M20 20l-3.5-3.5"/></svg>',
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
  // http(s) 주소만 링크로 만들어요 (javascript: 같은 주소는 링크로 쓰지 않음)
  function safeUrl(u) { return /^https?:\/\//i.test(String(u || '')) ? String(u) : ''; }
  function docLink(src, label) {
    var url = safeUrl(src && src.url);
    if (url) {
      return '<a class="btn btn-secondary btn-sm" href="' + esc(url) + '" target="_blank" rel="noopener">' + esc(label) + ICON.external + '</a>';
    }
    return '<span class="btn btn-secondary btn-sm" aria-disabled="true" title="원문 링크가 아직 없어요">' + esc(label) + ICON.external + '</span>';
  }
  // 데이터 방식 3가지: 사람이 원문 대조한 검증용 데이터(human), 가상 예시(sample), 엔진 결과(engine)
  function dataMode() {
    var m = DATA.meta || {};
    if (m.data_mode === 'human_reviewed_demo') return 'human';
    if (m.is_sample && !m.data_mode) return 'sample';
    return 'engine';
  }
  function byMode(human, sample, engine) {
    var mode = dataMode();
    return mode === 'human' ? human : (mode === 'sample' ? sample : engine);
  }
  function isReady(c) { return (c.promises || []).length > 0; }

  /* ---------- 첫 화면 검색: 분석 완료 / 분석 준비 중 / 상장 기업(아직 분석 전) ---------- */
  function norm(s) { return String(s || '').toLowerCase().replace(/\(주\)|㈜|주식회사/g, '').replace(/\s+/g, ''); }
  function aliasQuery(q) {
    var out = q;
    Object.keys(QUERY_ALIASES).forEach(function (k) { if (out.indexOf(k) >= 0) out = out.replace(k, QUERY_ALIASES[k]); });
    return out === q ? '' : out;
  }
  function companyKeys(c) { return [norm(c.name)].concat(COMPANY_ALIASES[c.id] || []); }
  function hit(keys, q, q2) {
    return keys.some(function (k) { return k.indexOf(q) >= 0 || (q2 && k.indexOf(q2) >= 0); });
  }
  function loadListed() {
    if (LISTED_STATE !== 'idle') { refreshSearch(); return; }
    LISTED_STATE = 'loading';
    fetch('data/listed-companies.json')
      .then(function (res) { if (!res.ok) throw new Error('listed'); return res.json(); })
      .then(function (d) {
        if (!d || !Array.isArray(d.companies)) throw new Error('listed');
        LISTED = d; LISTED_STATE = 'ready'; refreshSearch();
      })
      .catch(function () { LISTED_STATE = 'failed'; refreshSearch(); });
  }
  function searchHelpText() {
    var ready = (DATA.companies || []).filter(isReady).length;
    var base = '분석 완료 ' + ready + '곳';
    if (LISTED_STATE === 'ready') {
      return base + ' · 상장 기업 ' + Number(LISTED.count || LISTED.companies.length).toLocaleString('ko-KR') + '곳에서 찾을 수 있어요 (한국거래소 ' + (LISTED.as_of || '') + ' 기준)';
    }
    if (LISTED_STATE === 'failed') return base + ' · 상장 기업 목록을 불러오지 못했어요';
    return base + ' · 상장 기업 목록을 불러오는 중이에요';
  }
  function resultItem(c) {
    if (isReady(c)) {
      var meta = '구체적 약속 ' + specifics(c).length + '개 · ' + byMode('사람이 원문 대조', '가상 예시', 'AI 엔진 결과');
      return '<li><a class="search-item" href="#/c/' + encodeURIComponent(c.id) + '">' +
        '<span class="search-main"><span class="search-name">' + esc(c.name) + '</span><span class="search-meta">' + esc(meta) + '</span></span>' +
        '<span class="status-badge is-ready">분석 완료</span>' + ICON.chevron + '</a></li>';
    }
    return '<li><div class="search-item" aria-disabled="true">' +
      '<span class="search-main"><span class="search-name">' + esc(c.name) + '</span><span class="search-meta">' + esc(c.check_note || '공시 수집과 분석을 준비하고 있어요') + '</span></span>' +
      '<span class="status-badge is-pending">분석 준비 중</span></div></li>';
  }
  function listedItem(row) {
    return '<li><div class="search-item" aria-disabled="true">' +
      '<span class="search-main"><span class="search-name">' + esc(row[1]) + '</span><span class="search-meta">' + esc(row[2] + ' 상장 · 사업보고서 제출 대상') + '</span></span>' +
      '<span class="status-badge is-listed">아직 분석 전</span></div></li>';
  }
  function searchResults(raw) {
    var q = norm(raw);
    if (!q) return '';
    var q2 = aliasQuery(q);
    var mine = (DATA.companies || []).filter(function (c) { return hit(companyKeys(c), q, q2); });
    mine.sort(function (a, b) { return (isReady(b) ? 1 : 0) - (isReady(a) ? 1 : 0); });
    var listed = [], note = '';
    if (LISTED_STATE === 'ready') {
      // 데이터에 이미 있는 기업(예: 삼성전자, NAVER)은 상장 목록 쪽에서 빼요
      var own = {};
      (DATA.companies || []).forEach(function (c) { companyKeys(c).forEach(function (k) { own[k] = true; }); });
      for (var i = 0; i < LISTED.companies.length && listed.length < 5; i++) {
        var row = LISTED.companies[i], n = norm(row[1]);
        if (!own[n] && hit([n], q, q2)) listed.push(row);
      }
      if (!mine.length && !listed.length) {
        return '<div class="search-empty" role="status"><strong>상장 기업 목록에서 찾지 못했어요.</strong>' +
          '<span>회사 이름을 다시 확인해 주세요. 상장하지 않은 회사는 사업보고서가 없을 수 있어요.</span></div>';
      }
      if (listed.length) {
        note = '<p class="search-note">상장 기업은 DART에 사업보고서를 내요. 엔진에 이 회사의 보고서 3개(약속 1, 근거 2)를 넣어 돌리면 같은 4단계로 분석해요. 지금은 분석을 마친 기업만 결과가 열려요.</p>';
      }
    } else if (LISTED_STATE === 'failed') {
      note = '<p class="search-note">상장 기업 목록을 불러오지 못해서, 이 서비스에 있는 기업만 찾았어요.</p>';
      if (!mine.length) return '<div class="search-empty" role="status"><strong>이 서비스에 있는 기업 중에서는 찾지 못했어요.</strong><span>' + esc(searchHelpText()) + '</span></div>';
    } else {
      note = '<p class="search-note">상장 기업 목록을 불러오는 중이에요.</p>';
    }
    return '<ul class="search-list">' + mine.map(resultItem).join('') + listed.map(listedItem).join('') + '</ul>' + note;
  }
  function refreshSearch() {
    var input = document.getElementById('company-search');
    var box = document.getElementById('search-results');
    var help = document.getElementById('search-help');
    if (help) help.textContent = searchHelpText();
    if (input && box) box.innerHTML = searchResults(input.value);
  }

  /* ---------- 화면 1: 회사 검색 (분석 완료 기업은 바로 열기) ---------- */
  function viewHome() {
    var readyList = (DATA.companies || []).filter(isReady);
    var pendingList = (DATA.companies || []).filter(function (c) { return !isReady(c); });
    var companies = readyList.map(function (c) {
      var spec = specifics(c);
      var reports = c.reports || {};
      return '<a class="company" href="#/c/' + encodeURIComponent(c.id) + '">' +
        '<div class="company-logo" aria-hidden="true">' + esc(c.name.charAt(0)) + '</div>' +
        '<div class="company-info"><div class="company-name">' + esc(c.name) + '</div>' +
        '<div class="company-reports">' + esc('약속: ' + reportTitles(reports.promise) + ' · 근거: ' + reportTitles(reports.evidence)) + '</div>' +
        (c.check_note ? '<div class="company-reports check-note">' + esc(c.check_note) + '</div>' : '') +
        '<div class="company-meta">' + esc('구체적 약속 ' + spec.length + '개 중 ' + countLine(spec)) + '</div></div>' + ICON.chevron +
      '</a>';
    }).join('');
    var pending = pendingList.map(function (c) {
      return '<li class="pending-chip"><span class="pending-name">' + esc(c.name) + '</span>' +
        '<span class="pending-note">' + esc(c.check_note || '공시 수집과 분석을 준비하고 있어요') + '</span></li>';
    }).join('');

    var allReports = [];
    var readyCompanies = readyList;
    var totalSpecific = readyCompanies.reduce(function (sum, c) { return sum + specifics(c).length; }, 0);
    var verifiedCitations = readyCompanies.reduce(function (sum, c) {
      return sum + (c.promises || []).reduce(function (s, p) {
        return s + (p.evidence || []).filter(function (e) { return e.citation_verified === true; }).length;
      }, 0);
    }, 0);
    (DATA.companies || []).forEach(function (c) {
      var r = c.reports || {};
      (r.promise || []).concat(r.evidence || []).forEach(function (x) {
        if (allReports.indexOf(x.title) < 0) allReports.push(x.title);
      });
    });

    var modeNote = byMode(
      '지금 보이는 판정은 사람이 공시 원문을 직접 읽고 대조한 검증용 데이터예요. 엔진은 같은 4단계로 같은 형식의 결과를 만들어요.',
      '지금 보이는 기업과 판정은 화면 형식을 보여 주는 가상 예시예요.',
      '지금 보이는 판정은 AI 엔진 결과예요. 원문 링크로 직접 확인해 주세요.');

    return topbar('<div class="brand">' + ICON.shield + esc(L.service_name) + '</div>') +
      '<main class="content">' + disclaimers() +
        '<section class="hero search-hero">' +
          '<p class="eyebrow">' + esc(L.service_subtitle) + ' · ' + esc(L.tagline) + '</p>' +
          '<h1 class="headline">어떤 기업의 AI 약속이<br><span class="hl">궁금한가요?</span></h1>' +
          '<p class="lead">사업보고서의 "하겠다"를 찾고, 다음 해 공시에서 "했다"는 근거를 찾아 원문과 함께 보여드려요.</p>' +
          '<label class="company-search">' +
            '<span class="sr-only">회사명 검색</span>' +
            '<span class="search-icon">' + ICON.search + '</span>' +
            '<input id="company-search" type="search" autocomplete="off" enterkeyhint="search" placeholder="회사명 검색 (예: 삼성전자, 현대자동차)" aria-controls="search-results" aria-describedby="search-help">' +
          '</label>' +
          '<p class="search-help" id="search-help">' + esc(searchHelpText()) + '</p>' +
          '<div class="search-results" id="search-results" aria-live="polite"></div>' +
          '<div class="tech-strip" aria-label="서비스 핵심 기술">' +
            '<span>DART 공시</span><span>하이브리드 RAG (키워드 + 의미 검색)</span><span>LLM 판정</span><span>원문 인용 검사</span>' +
          '</div>' +
          '<div class="hero-stats" aria-label="현재 분석 범위">' +
            '<div><strong>' + readyCompanies.length + '</strong><span>분석 완료 기업</span></div>' +
            '<div><strong>' + totalSpecific + '</strong><span>구체적 AI 약속</span></div>' +
            '<div><strong>' + verifiedCitations + '</strong><span>원문 대조 근거</span></div>' +
          '</div>' +
        '</section>' +
        '<section class="company-picker">' +
          '<h2 class="section-label">분석 완료</h2>' +
          '<div class="company-list">' + companies + '</div>' +
          (pending ? '<h2 class="section-label">분석 준비 중</h2><ul class="pending-list">' + pending + '</ul>' : '') +
        '</section>' +
        '<section class="card">' +
          '<h2 class="card-title" style="font-size:13px">이렇게 확인해요</h2>' +
          '<ol class="steps">' +
            '<li><span class="step-num">1</span>약속 찾기: 사업보고서에서 AI 약속 문장을 원문 그대로 골라요</li>' +
            '<li><span class="step-num">2</span>근거 찾기: 다음 보고서에서 키워드 검색과 의미 검색(RAG)으로 실행 근거를 찾아요</li>' +
            '<li><span class="step-num">3</span>판정: 판정기준 v2로 4가지 중 하나로 정해요</li>' +
            '<li><span class="step-num">4</span>원문 인용 검사: 근거 문장이 원문에 그대로 있는지 다시 확인해요</li>' +
          '</ol>' +
          '<p class="note">' + esc(modeNote) + ' 새 기업은 사업보고서 3개(약속 1, 근거 2)를 엔진에 넣으면 같은 순서로 분석해요.</p>' +
        '</section>' +
      '</main>' +
      '<footer class="bottombar"><p class="note">자료: 금융감독원 전자공시(DART)' + (allReports.length ? ' · ' + esc(allReports.join(', ')) : '') + ' · 상장 기업 목록: 한국거래소(KRX)</p></footer>';
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
          (company.check_note ? '<p class="note check-note">' + esc(company.check_note) + '</p>' : '') +
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
  function evidenceBlock(e, kindLabel, kicker) {
    var verified = e.citation_verified === true
      ? '<span class="verified">' + ICON.check + esc(L.citation_verified_label) + '</span>'
      : '';
    var url = safeUrl(e.source && e.source.url);
    var link = url
      ? '<a class="ev-link" href="' + esc(url) + '" target="_blank" rel="noopener">원문 보기' + ICON.external + '</a>'
      : '';
    return '<div class="timeline-connector"><span></span><em>후속 공시에서 근거 검색</em><span></span></div>' +
      '<div class="timeline-node evidence-node">' +
        '<div class="timeline-rail"><span class="timeline-index">02</span><span class="timeline-dot"></span></div>' +
        '<div class="timeline-body quote-block">' +
          '<div class="timeline-kicker">' + esc(kicker) + '</div>' +
          '<div class="quote-meta is-evidence"><span>' + esc(kindLabel) + '</span><span>' + esc(sourceLabel(e.source || {})) + '</span></div>' +
          '<p class="quote-text">"' + esc(e.sentence) + '"</p>' +
          '<div class="ev-foot">' + verified + link + '</div>' +
        '</div>' +
      '</div>';
  }

  function viewDetail(company, p) {
    var listHref = '#/c/' + encodeURIComponent(company.id);
    var evidence = p.evidence || [];
    var specific = isSpecific(p);
    var kindLabel = !specific ? '관련 활동' : (p.verdict === 'company_reported_not_pursued' ? '회사가 적은 문장' : '실행 근거');
    var emptyMsg = specific ? L.not_verifiable_message : L.no_related_activity_message;
    var evKicker = (specific ? '근거' : '관련 활동') + ' · 후속 공시';
    var promiseReport = (p.source || {}).report || '약속 보고서';

    var evidenceHtml = evidence.length
      ? evidence.map(function (e) { return evidenceBlock(e, kindLabel, evKicker); }).join('')
      : '<div class="timeline-connector"><span></span><em>후속 공시에서 근거 검색</em><span></span></div>' +
        '<div class="timeline-node evidence-node">' +
          '<div class="timeline-rail"><span class="timeline-index">02</span><span class="timeline-dot muted"></span></div>' +
          '<div class="timeline-body quote-block"><div class="timeline-kicker">' + esc(evKicker) + '</div><p class="quote-empty">' + esc(emptyMsg) + '</p></div>' +
        '</div>';

    // 화면에는 데이터로 확인되는 상태만 보여줘요. 단계마다 누가 했는지 함께 적어요 (사람 대조 데이터를 AI가 한 것처럼 보이지 않게)
    var verifiedCount = evidence.filter(function (e) { return e.citation_verified === true; }).length;
    var who2 = byMode('사람이 원문 대조', '예시 데이터', specific && p.search_attempts ? 'AI 검색 ' + p.search_attempts + '번' : 'AI 검색');
    var pipeline = [
      { n: '01', title: '약속 찾기', who: byMode('사람이 원문에서 고름', '예시 데이터', 'AI가 원문 문장을 고름'),
        desc: promiseReport + '의 AI 계획 문장', ok: true },
      { n: '02', title: specific ? '근거 찾기' : '관련 활동 찾기', who: who2,
        desc: evidence.length ? '후속 공시에서 ' + (specific ? '근거' : '관련 활동') + ' ' + evidence.length + '개' : '읽은 후속 공시 범위에서 찾지 못함', ok: evidence.length > 0 },
      { n: '03', title: '판정', who: specific ? byMode('판정기준 v2, 사람', '판정기준 v2, 예시', '판정기준 v2, AI') : '',
        desc: specific ? verdictLabel(p.verdict) : '방향성 약속이라 판정하지 않음', ok: specific ? !!p.verdict : true },
      { n: '04', title: '원문 인용 검사', who: byMode('사람이 원문과 대조', '예시 데이터', '코드가 원문과 대조'),
        desc: evidence.length ? (specific ? '근거 문장 ' : '찾은 문장 ') + evidence.length + '개 중 ' + verifiedCount + '개 ' + L.citation_verified_label : '확인할 문장이 없음', ok: evidence.length ? verifiedCount === evidence.length : false }
    ];
    var pipelineRows = pipeline.map(function (s) {
      return '<li class="pipeline-step ' + (s.ok ? 'is-done' : 'is-muted') + '">' +
        '<span class="pipeline-num">' + s.n + '</span>' +
        '<span class="pipeline-state">' + (s.ok ? ICON.check : ICON.dash) + '</span>' +
        '<span class="pipeline-copy"><span class="pipeline-head"><strong>' + esc(s.title) + '</strong>' +
          (s.who ? '<span class="pipeline-who">' + esc(s.who) + '</span>' : '') + '</span><small>' + esc(s.desc) + '</small></span>' +
      '</li>';
    }).join('');

    var pill = specific
      ? '<span class="verdict-pill">' + esc(verdictLabel(p.verdict)) + '</span>'
      : '<span class="verdict-pill">' + esc(L.promise_types.directional.label) + '</span>';
    var secondLink = evidence.length && evidence[0].source
      ? docLink(evidence[0].source, evidence[0].source.report + ' 원문')
      : '<a class="btn btn-secondary btn-sm" href="' + listHref + '">목록으로</a>';

    return topbar(backLink(listHref, '약속 목록')) +
      '<main class="content ' + vClass(p.verdict) + '">' + disclaimers() +
        '<section style="display:flex;flex-direction:column;gap:10px">' +
          pill +
          '<h1 class="detail-title">' + esc(p.title) + '</h1>' +
        '</section>' +
        '<section class="analysis-timeline" aria-label="약속과 후속 근거 타임라인">' +
          '<div class="timeline-node promise-node">' +
            '<div class="timeline-rail"><span class="timeline-index">01</span><span class="timeline-dot"></span></div>' +
            '<div class="timeline-body quote-block">' +
              '<div class="timeline-kicker">' + esc('약속 · ' + promiseReport) + '</div>' +
              '<div class="quote-meta"><span>회사가 밝힌 AI 계획</span><span>' + esc(sourceLabel(p.source || {})) + '</span></div>' +
              '<p class="quote-text">"' + esc(p.sentence) + '"</p>' +
            '</div>' +
          '</div>' +
          evidenceHtml +
          '<div class="timeline-connector verdict-connector"><span></span><em>약속과 근거를 판정기준 v2로 대조</em><span></span></div>' +
          '<div class="timeline-node verdict-node">' +
            '<div class="timeline-rail"><span class="timeline-index">03</span><span class="timeline-dot"></span></div>' +
            '<div class="timeline-body verdict-panel">' +
              '<div class="timeline-kicker">판정</div>' +
              pill +
              (specific ? (p.reason ? '<p class="reason">' + esc(p.reason) + '</p>' : '') : '<p class="note">' + esc(L.promise_types.directional.note) + '</p>') +
            '</div>' +
          '</div>' +
        '</section>' +
        '<details class="card pipeline-card" open>' +
          '<summary><span>확인 4단계</span><small>약속 찾기 → 근거 찾기(RAG) → 판정 → 원문 인용 검사</small></summary>' +
          '<ul class="pipeline-list">' + pipelineRows + '</ul>' +
          '<p class="pipeline-note">' + esc(byMode(
            '지금 화면의 판정은 사람이 공시 원문을 직접 읽고 대조한 검증용 데이터예요. 엔진은 같은 4단계로 같은 형식의 결과를 만들고, 엔진 정확도는 따로 평가해요.',
            '가상 예시 데이터라 실제 기업이나 실제 공시가 아니에요.',
            'AI 엔진 결과예요. 판정이 맞는지 원문 링크로 직접 확인해 주세요.')) + '</p>' +
        '</details>' +
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
      var url = safeUrl(a.evidence_url);
      var link = url
        ? '<a class="ev-link" href="' + esc(url) + '" target="_blank" rel="noopener">근거 원문' + ICON.external + '</a>'
        : '';
      return '<div class="answer insight-block">' +
        '<div class="insight-eyebrow">면접 포인트</div>' +
        '<a class="answer-tag" href="' + promiseHref(company, a.promise_id) + '">' + esc(titleOf(a.promise_id)) + '</a>' +
        '<div class="answer-text">' + esc(a.text) + '</div>' + link + '</div>';
    }).join('');
    var questions = qData.map(function (q) {
      var text = typeof q === 'string' ? q : q.text;
      var inner = '<span class="question-icon">' + ICON.chat + '</span><div><span class="insight-eyebrow">질문</span><span>' + esc(text) + '</span></div>';
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
        '<section class="card interview-section"><div class="section-title-row"><span class="insight-eyebrow">공시 확인</span><h2 class="card-title">공시에서 확인할 핵심 이슈 ' + issuesData.length + '</h2></div>' + issues + '</section>' +
        '<section class="card interview-section"><div class="section-title-row"><span class="insight-eyebrow">면접 포인트</span><h2 class="card-title">면접에서 활용할 소재 ' + tpData.length + '</h2></div>' + answers + '</section>' +
        '<section class="card interview-section"><div class="section-title-row"><span class="insight-eyebrow">질문</span><h2 class="card-title">회사에 물어볼 역질문 ' + qData.length + '</h2></div>' + questions + '</section>' +
      '</main>' +
      '<footer class="bottombar two">' +
        '<button type="button" class="btn btn-secondary" id="copy-btn">카드 복사하기</button>' +
        '<a class="btn btn-primary" href="#/">다른 기업 보기</a>' +
      '</footer>';
  }

  function cardAsText(company) {
    var card = company.interview_card || {};
    var lines = ['[' + company.name + ' 면접 카드]', L.interview_card_notice, '', '공시에서 확인할 핵심 이슈'];
    (card.issues || []).forEach(function (it, i) { lines.push((i + 1) + '. ' + it.text); });
    lines.push('', '면접에서 활용할 소재');
    (card.talking_points || []).forEach(function (a) {
      var u = safeUrl(a.evidence_url);
      lines.push('- ' + a.text + (u ? ' (근거: ' + u + ')' : ''));
    });
    lines.push('', '회사에 물어볼 역질문');
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

  // 그리는 중 오류가 나면 빈 화면 대신 안내를 보여주고, 오류는 그대로 던져서 검사(ui_check)에 잡히게 해요
  function render() {
    try { draw(); } catch (e) {
      appEl.innerHTML = '<main class="content"><p class="empty">화면을 그리지 못했어요. 새로고침해 주세요.</p></main>';
      throw e;
    }
  }

  function draw() {
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
    document.title = title === L.service_name ? L.service_name + ' | ' + L.service_subtitle : title + ' | ' + L.service_name;
    window.scrollTo(0, 0);

    var themeBtn = document.getElementById('theme-btn');
    if (themeBtn) themeBtn.addEventListener('click', toggleTheme);
    var searchInput = document.getElementById('company-search');
    if (searchInput) {
      searchInput.addEventListener('input', refreshSearch);
      // Enter: 분석 완료 기업이 검색 결과에 있으면 첫 번째를 열어요
      searchInput.addEventListener('keydown', function (e) {
        if (e.key !== 'Enter') return;
        var first = document.querySelector('#search-results a.search-item');
        if (first) {
          e.preventDefault();
          location.hash = first.getAttribute('href');
        }
      });
      loadListed();
    }
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

  // results.json을 못 읽을 때만 예시 데이터로 바꿔요. 그리는 중 오류는 예시 데이터로 덮지 않고 그대로 드러나게 해요
  fetch('data/results.json', { cache: 'no-store' })
    .then(function (res) { if (!res.ok) throw new Error('no results'); return res.json(); })
    .then(function (data) { start(data); }, function () { start(window.AI_PROMISE_SAMPLE); });
})();
