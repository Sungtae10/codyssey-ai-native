// 원/달러 환율 비서: 화면 동작 (바닐라 JS, 프레임워크 없음)
import { api, ApiError, API_BASE } from "./api.js";
import { drawLineChart, drawSparkline, movingAverage } from "./chart.js";
import {
  compactDate, direction, escapeHtml, fmtDateTime, fmtNum, fmtPct, fmtSigned, renderRichText, shortDate, todayKST,
} from "./format.js";

const $ = (selector) => document.querySelector(selector);

const SUGGESTIONS = [
  "이번 달 환율 흐름 어때?",
  "최근 1년 중 가장 높았던 날은?",
  "월별로 보면 언제 가장 낮았어?",
  "하루에 가장 크게 오른 날 3개 알려줘",
  "9월 첫째 주 값을 날짜별로 보여줘",
];

const BUSY_MESSAGE = "답변을 받는 중이에요. 답이 온 뒤에 다시 눌러 주세요.";

const state = {
  summary: null,
  stats: null,
  records: [], // 날짜 오름차순
  conversations: [],
  conv: { id: null, title: "새 대화", messages: [] },
  sending: false,
  range: "all",
  showMA: true,
  filter: "",
  editingId: null,
  highlightId: null,
  online: false,
};

/* ---------------- 공통 ---------------- */
let toastTimer;
function toast(message, tone = "ok") {
  const box = $("#toast");
  box.textContent = message;
  box.dataset.tone = tone;
  box.classList.add("show");
  clearTimeout(toastTimer);
  toastTimer = setTimeout(() => box.classList.remove("show"), 3200);
}

function setStatus(stateName, text) {
  const pill = $("#server-status");
  pill.dataset.state = stateName;
  pill.querySelector(".status-text").textContent = text;
  pill.title = text;
}

function showBanner(text, { tone = "info", retry = false } = {}) {
  $("#banner").hidden = false;
  $("#banner").dataset.tone = tone;
  $("#banner-text").textContent = text;
  $("#banner-retry").hidden = !retry;
}
function hideBanner() { $("#banner").hidden = true; }

/* ---------------- 테마 ---------------- */
const MOON = '<path d="M21 12.8A9 9 0 1 1 11.2 3a7 7 0 0 0 9.8 9.8z"/>';
const SUN = '<circle cx="12" cy="12" r="4"/><path d="M12 2v2M12 20v2M4.9 4.9l1.4 1.4M17.7 17.7l1.4 1.4M2 12h2M20 12h2M4.9 19.1l1.4-1.4M17.7 6.3l1.4-1.4"/>';

function currentTheme() {
  const set = document.documentElement.getAttribute("data-theme");
  if (set === "light" || set === "dark") return set;
  return window.matchMedia("(prefers-color-scheme: dark)").matches ? "dark" : "light";
}
function paintThemeButton() {
  const dark = currentTheme() === "dark";
  const btn = $("#theme-toggle");
  btn.querySelector("svg").innerHTML = dark ? SUN : MOON;
  btn.setAttribute("aria-label", dark ? "라이트 모드로 바꾸기" : "다크 모드로 바꾸기");
  btn.title = btn.getAttribute("aria-label");
}
function setupTheme() {
  paintThemeButton();
  $("#theme-toggle").addEventListener("click", () => {
    const next = currentTheme() === "dark" ? "light" : "dark";
    document.documentElement.setAttribute("data-theme", next);
    try { localStorage.setItem("theme", next); } catch { /* 저장 못 해도 이번 화면에는 적용 */ }
    paintThemeButton();
  });
}

/* ---------------- 탭 ---------------- */
function selectTab(name, { focus = false } = {}) {
  const tabs = { chat: $("#tab-chat"), data: $("#tab-data") };
  for (const [key, tab] of Object.entries(tabs)) {
    const on = key === name;
    tab.setAttribute("aria-selected", String(on));
    tab.tabIndex = on ? 0 : -1;
    $(`#view-${key}`).hidden = !on;
    if (on && focus) tab.focus();
  }
  document.body.classList.toggle("lock", name === "chat");
  if (location.hash !== `#${name}`) window.history.replaceState(null, "", `#${name}`);
  if (name === "data") renderChart();
}
function setupTabs() {
  $("#tab-chat").addEventListener("click", () => selectTab("chat"));
  $("#tab-data").addEventListener("click", () => selectTab("data"));
  $(".tabs").addEventListener("keydown", (e) => {
    if (e.key !== "ArrowLeft" && e.key !== "ArrowRight") return;
    const next = $("#tab-chat").getAttribute("aria-selected") === "true" ? "data" : "chat";
    selectTab(next, { focus: true });
    e.preventDefault();
  });
  selectTab(location.hash === "#data" ? "data" : "chat");
}

/* ---------------- 서버 깨우기 (Render 무료 서버 대응) ---------------- */
async function wakeServer() {
  setStatus("waking", "서버 확인 중");
  const started = Date.now();
  const ticker = setInterval(() => {
    const sec = Math.round((Date.now() - started) / 1000);
    if (sec >= 3) {
      setStatus("waking", `서버 깨우는 중 ${sec}초`);
      showBanner(
        `서버를 깨우는 중이에요 (${sec}초). 무료 서버(Render)는 15분 동안 요청이 없으면 잠들어서, ` +
          "처음 열 때 1분 정도 걸릴 수 있어요. 창을 닫지 말고 잠시 기다려 주세요.",
      );
    }
  }, 1000);
  try {
    let health = null;
    for (let attempt = 1; attempt <= 2 && !health; attempt += 1) {
      try {
        health = await api.health({ timeout: 75000 });
      } catch (error) {
        if (attempt === 2) throw error;
      }
    }
    clearInterval(ticker);
    state.online = true;
    if (!health.storage.ready) {
      setStatus("warn", "저장소 설정 필요");
      showBanner(`서버는 켜졌지만 데이터베이스 연결에 문제가 있어요: ${health.storage.error}`, { tone: "error" });
    } else if (!health.openai.configured) {
      setStatus("warn", "AI 키 설정 필요");
      showBanner("서버에 OPENAI_API_KEY가 없어 AI 채팅은 쓸 수 없어요. 데이터 관리는 쓸 수 있어요.", { tone: "error" });
    } else {
      setStatus("ok", "서버 연결됨");
      hideBanner();
    }
    return true;
  } catch (error) {
    clearInterval(ticker);
    state.online = false;
    setStatus("down", "연결 안 됨");
    showBanner(`서버(${API_BASE})에 연결하지 못했어요. ${error.message}`, { tone: "error", retry: true });
    return false;
  }
}

/* ---------------- 요약 보드 ---------------- */
async function loadSummary() {
  const board = $("#board");
  board.classList.add("is-loading");
  try {
    state.summary = await api.summary();
    renderBoard();
  } catch (error) {
    board.innerHTML = `<p class="board-empty">요약을 불러오지 못했어요: ${escapeHtml(error.message)}</p>`;
  } finally {
    board.classList.remove("is-loading");
    board.setAttribute("aria-busy", "false");
  }
}

function renderBoard() {
  const s = state.summary;
  const board = $("#board");
  if (!s || !s.metrics) {
    board.innerHTML = '<p class="board-empty">아직 데이터가 없어요. 데이터 관리에서 값을 추가하세요.</p>';
    return;
  }
  const m = s.metrics;
  const unit = s.dataset.unit || "";
  const recent = s.recent || [];
  const prev = recent.length > 1 ? recent[recent.length - 2] : null;
  const diff = prev ? m.latest - prev.value : null;
  const dir = direction(diff ?? 0);
  const pct = prev && prev.value ? (diff / prev.value) * 100 : null;
  const t = s.trend_detail;
  const trendDir = t ? t.direction : "판단 불가";
  const trendTitle = t
    ? `최근 ${t.window}개 평균 ${fmtNum(t.recent_average)}${unit}, 직전 ${t.window}개 평균 ${fmtNum(t.previous_average)}${unit}. ` +
      `변화 ${fmtPct(t.change_pct)} (±${t.threshold_pct}%를 넘으면 상승·하락으로 봐요)`
    : s.trend;

  board.innerHTML = `
    <div class="board-rate">
      <span class="board-label">${escapeHtml(s.dataset.name)} 최신값</span>
      <span class="board-value"><strong>${fmtNum(m.latest)}</strong><span class="unit">${escapeHtml(unit)}</span></span>
      <span class="delta ${dir.cls}">${diff === null ? "" : `${dir.mark} ${fmtNum(Math.abs(diff))} (${fmtPct(pct)}) 전일 대비`}</span>
      <span class="board-label">${escapeHtml(m.latest_date)} 기준</span>
    </div>
    <dl class="board-stats">
      <div><dt>데이터 기간</dt><dd class="num">${escapeHtml(s.period)}</dd></div>
      <div><dt>개수</dt><dd class="num">${fmtNum(s.count, 0)}개</dd></div>
      <div><dt>평균</dt><dd class="num">${fmtNum(m.average)}</dd></div>
      <div><dt>최고</dt><dd class="num">${fmtNum(m.max)} <small>${shortDate(m.max_date)}</small></dd></div>
      <div><dt>최저</dt><dd class="num">${fmtNum(m.min)} <small>${shortDate(m.min_date)}</small></dd></div>
      <div><dt>최근 추세</dt><dd title="${escapeHtml(trendTitle)}"><span class="trend-tag" data-dir="${escapeHtml(trendDir)}">${escapeHtml(trendDir)}</span>
        ${t ? `<small>${fmtPct(t.change_pct)}</small>` : ""}</dd></div>
    </dl>
    <div class="board-spark-wrap" id="spark"></div>`;
  if (state.records.length) drawSparkline($("#spark"), state.records.map((r) => r.value));
}

/* ---------------- 대화 기록 ---------------- */
async function loadConversations() {
  try {
    const res = await api.listConversations();
    state.conversations = res.items;
    renderConversations();
  } catch (error) {
    $("#conv-list").innerHTML = "";
    $("#conv-empty").hidden = false;
    $("#conv-empty").textContent = `대화 목록을 불러오지 못했어요: ${error.message}`;
  }
}

const TRASH = '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" aria-hidden="true"><path d="M4 7h16M10 11v6M14 11v6M6 7l1 13h10l1-13M9 7V4h6v3"/></svg>';

function renderConversations() {
  const list = $("#conv-list");
  list.replaceChildren();
  $("#conv-empty").hidden = state.conversations.length > 0;
  $("#conv-empty").textContent = "아직 저장된 대화가 없어요. 질문하면 자동으로 저장돼요.";
  for (const conv of state.conversations) {
    const li = document.createElement("li");
    li.className = "conv-row";
    if (conv.id === state.conv.id) li.setAttribute("aria-current", "true");

    const open = document.createElement("button");
    open.type = "button";
    open.className = "conv-open";
    const title = document.createElement("span");
    title.className = "conv-title";
    title.textContent = conv.title;
    const meta = document.createElement("span");
    meta.className = "conv-meta";
    meta.textContent = `${fmtDateTime(conv.updated_at)} | 메시지 ${conv.message_count}개`;
    open.append(title, meta);
    open.addEventListener("click", () => openConversation(conv.id));

    const del = document.createElement("button");
    del.type = "button";
    del.className = "conv-del";
    del.innerHTML = TRASH;
    del.setAttribute("aria-label", `대화 삭제: ${conv.title}`);
    del.title = "대화 삭제";
    del.addEventListener("click", () => removeConversation(conv));

    li.append(open, del);
    list.appendChild(li);
  }
}

async function openConversation(id) {
  if (state.sending) { toast(BUSY_MESSAGE, "error"); return; }
  closeDrawer();
  try {
    const conv = await api.getConversation(id);
    state.conv = { id: conv.id, title: conv.title, messages: conv.messages };
    renderMessages();
    renderConversations();
    $("#prompt").focus();
  } catch (error) {
    toast(`대화를 불러오지 못했어요: ${error.message}`, "error");
  }
}

async function removeConversation(conv) {
  if (state.sending) { toast(BUSY_MESSAGE, "error"); return; }
  if (!window.confirm(`'${conv.title}' 대화를 삭제할까요? 되돌릴 수 없어요.`)) return;
  try {
    await api.deleteConversation(conv.id);
    if (state.conv.id === conv.id) newConversation();
    toast("대화를 삭제했어요");
    await loadConversations();
  } catch (error) {
    toast(`삭제하지 못했어요: ${error.message}`, "error");
  }
}

function newConversation() {
  if (state.sending) { toast(BUSY_MESSAGE, "error"); return; }
  state.conv = { id: null, title: "새 대화", messages: [] };
  renderMessages();
  renderConversations();
  closeDrawer();
}

/* ---------------- 채팅 ---------------- */
function messageNode(msg, index) {
  const wrap = document.createElement("div");
  if (msg.role === "user") {
    wrap.className = "msg msg-user";
    const bubble = document.createElement("div");
    bubble.className = "bubble";
    bubble.textContent = msg.content;
    wrap.appendChild(bubble);
    return wrap;
  }
  if (msg.role === "error") {
    wrap.className = "msg msg-error";
    const bubble = document.createElement("div");
    bubble.className = "bubble";
    bubble.textContent = msg.content;
    wrap.appendChild(bubble);
    const foot = document.createElement("div");
    foot.className = "msg-foot";
    const retry = document.createElement("button");
    retry.type = "button";
    retry.className = "btn btn-small";
    retry.textContent = "다시 보내기";
    retry.addEventListener("click", () => {
      if (state.sending) { toast(BUSY_MESSAGE, "error"); return; }
      state.conv.messages.splice(index - 1, 2); // 실패한 질문과 오류 표시를 지우고 다시 보냄
      send(msg.retryText);
    });
    foot.appendChild(retry);
    wrap.appendChild(foot);
    return wrap;
  }
  wrap.className = "msg msg-ai";
  const bubble = document.createElement("div");
  bubble.className = "bubble";
  bubble.innerHTML = renderRichText(msg.content);
  wrap.appendChild(bubble);

  const foot = document.createElement("div");
  foot.className = "msg-foot";
  if (msg.summary_used && msg.summary_used.period) {
    const note = document.createElement("span");
    note.className = "context-note";
    note.textContent = `내 데이터 요약 반영: ${msg.summary_used.period}, ${msg.summary_used.count}개, 추세 ${String(msg.summary_used.trend).split(" ")[0]}`;
    foot.appendChild(note);
  }
  for (const call of msg.tool_calls || []) {
    const chip = document.createElement("span");
    chip.className = "chip";
    chip.dataset.ok = String(call.ok !== false);
    const name = document.createElement("b");
    name.textContent = call.name;
    chip.appendChild(name);
    const args = Object.entries(call.arguments || {}).map(([k, v]) => `${k}=${v}`).join(", ");
    if (args) chip.append(` (${args})`);
    if (call.reason) chip.append(` 이유: ${call.reason}`);
    if (call.ok === false) chip.append(" (실패)");
    chip.title = call.reason ? `호출 이유: ${call.reason}` : "도구 호출";
    foot.appendChild(chip);
  }
  if (msg.model) {
    const model = document.createElement("span");
    model.textContent = msg.model;
    foot.appendChild(model);
  }
  if (foot.childNodes.length) wrap.appendChild(foot);
  return wrap;
}

function renderIntro() {
  const intro = document.createElement("div");
  intro.className = "intro";
  const s = state.summary;
  const period = s && s.metrics ? `${s.period}, ${s.count}개` : "저장된 데이터";
  intro.innerHTML = `
    <h2>내 환율 데이터로 답하는 AI 비서</h2>
    <p>${escapeHtml(period)}의 원/달러 환율 요약을 매 질문마다 AI에게 함께 보내요.
    그래서 일반적인 설명이 아니라 이 데이터의 숫자로 답해요. 요약에 없는 날짜는 AI가 직접 조회해서 확인해요.</p>
    <div class="suggestions" role="group" aria-label="질문 예시"></div>`;
  const wrap = intro.querySelector(".suggestions");
  for (const text of SUGGESTIONS) {
    const btn = document.createElement("button");
    btn.type = "button";
    btn.className = "suggestion";
    btn.textContent = text;
    btn.addEventListener("click", () => send(text));
    wrap.appendChild(btn);
  }
  return intro;
}

let typingTimer;
function renderMessages() {
  const box = $("#messages");
  box.replaceChildren();
  $("#chat-title").textContent = state.conv.title || "새 대화";
  const real = state.conv.messages.filter((m) => m.role === "user" || m.role === "assistant");
  $("#save-copy").disabled = real.length === 0 || state.sending;
  if (!state.conv.messages.length) {
    box.appendChild(renderIntro());
    return;
  }
  state.conv.messages.forEach((msg, i) => box.appendChild(messageNode(msg, i)));
  if (state.sending) {
    const wrap = document.createElement("div");
    wrap.className = "msg msg-ai";
    wrap.innerHTML = '<div class="bubble"><span class="typing"><span class="dots" aria-hidden="true"><i></i><i></i><i></i></span><span id="typing-text">내 데이터 요약을 넣어 답을 만드는 중이에요</span></span></div>';
    box.appendChild(wrap);
  }
  // 넓은 화면은 메시지 칸이, 좁은 화면은 페이지 전체가 스크롤된다
  if (window.matchMedia("(max-width: 760px)").matches) {
    window.scrollTo({ top: document.documentElement.scrollHeight });
  } else {
    box.scrollTop = box.scrollHeight;
  }
}

function startTypingTimer() {
  const started = Date.now();
  clearInterval(typingTimer);
  typingTimer = setInterval(() => {
    const label = document.getElementById("typing-text");
    if (!label) return;
    const sec = Math.round((Date.now() - started) / 1000);
    label.textContent = sec < 12
      ? `내 데이터 요약을 넣어 답을 만드는 중이에요 (${sec}초)`
      : `아직 만드는 중이에요 (${sec}초). 서버가 잠들어 있었다면 1분 정도 걸릴 수 있어요.`;
  }, 1000);
}

function updateComposer() {
  const text = $("#prompt").value;
  $("#char-count").textContent = `${text.length}/1000`;
  $("#send").disabled = state.sending || !text.trim();
  $("#send").textContent = state.sending ? "답변 중" : "보내기";
}

async function send(textArg) {
  const text = (textArg ?? $("#prompt").value).trim();
  if (!text || state.sending) return;
  state.sending = true;
  const conv = state.conv; // 답이 오는 동안 화면의 대화가 바뀌어도 답은 질문한 대화에 붙인다
  conv.messages.push({ role: "user", content: text });
  $("#prompt").value = "";
  autosize();
  updateComposer();
  renderMessages();
  startTypingTimer();
  try {
    const res = await api.chat({ message: text, conversation_id: conv.id });
    conv.id = res.conversation_id;
    conv.title = res.conversation_title;
    conv.messages.push({
      role: "assistant",
      content: res.reply,
      model: res.model,
      tool_calls: res.tool_calls,
      summary_used: res.summary_used,
    });
    loadConversations();
  } catch (error) {
    let hint = error.status === 429 ? "" : " 저장되지 않았어요.";
    if (error.status === 404 && conv.id) {
      // 다른 곳에서 이 대화가 삭제된 경우: 다시 보내면 새 대화로 저장되게 한다
      conv.id = null;
      hint = " 이 대화가 삭제되어, 다시 보내면 새 대화로 저장돼요.";
      loadConversations();
    }
    conv.messages.push({ role: "error", content: `답을 받지 못했어요: ${error.message}${hint}`, retryText: text });
  } finally {
    state.sending = false;
    clearInterval(typingTimer);
    renderMessages();
    updateComposer();
  }
}

function autosize() {
  const area = $("#prompt");
  area.style.height = "auto";
  area.style.height = `${Math.min(area.scrollHeight, 160)}px`;
}

function closeDrawer() {
  $("#history").classList.remove("open");
  $("#backdrop").classList.remove("open");
  $("#history-toggle").setAttribute("aria-expanded", "false");
}

function setupChat() {
  $("#composer").addEventListener("submit", (e) => { e.preventDefault(); send(); });
  $("#prompt").addEventListener("keydown", (e) => {
    if (e.key === "Enter" && !e.shiftKey && !e.isComposing) { e.preventDefault(); send(); }
  });
  $("#prompt").addEventListener("input", () => { autosize(); updateComposer(); });
  $("#new-chat").addEventListener("click", () => { newConversation(); $("#prompt").focus(); });
  $("#history-toggle").addEventListener("click", () => {
    const open = !$("#history").classList.contains("open");
    $("#history").classList.toggle("open", open);
    $("#backdrop").classList.toggle("open", open);
    $("#history-toggle").setAttribute("aria-expanded", String(open));
  });
  $("#backdrop").addEventListener("click", closeDrawer);
  document.addEventListener("keydown", (e) => { if (e.key === "Escape") closeDrawer(); });
  $("#banner-retry").addEventListener("click", () => start());
  updateComposer();
  renderMessages();
}

/* ---------------- 사본 저장 (POST /api/conversations) ---------------- */
function setupCopyDialog() {
  const dialog = $("#copy-dialog");
  $("#save-copy").addEventListener("click", () => {
    $("#copy-name").value = `${state.conv.title} (사본)`.slice(0, 100);
    dialog.showModal();
    $("#copy-name").select();
  });
  $("#copy-cancel").addEventListener("click", () => dialog.close());
  $("#copy-form").addEventListener("submit", async (e) => {
    e.preventDefault();
    const title = $("#copy-name").value.trim();
    if (!title) return;
    const messages = state.conv.messages
      .filter((m) => m.role === "user" || m.role === "assistant")
      .map((m) => ({ role: m.role, content: m.content }));
    try {
      await api.saveConversation({ title, messages });
      dialog.close();
      toast("사본으로 저장했어요");
      loadConversations();
    } catch (error) {
      toast(`저장하지 못했어요: ${error.message}`, "error");
    }
  });
}

/* ---------------- 데이터 관리 ---------------- */
async function loadRecords() {
  $("#chart").classList.add("is-loading");
  try {
    const res = await api.listData();
    state.records = res.items;
    renderTable();
    renderChart();
    if (state.summary) renderBoard();
  } catch (error) {
    $("#data-body").innerHTML = `<tr><td colspan="5">데이터를 불러오지 못했어요: ${escapeHtml(error.message)}</td></tr>`;
  } finally {
    $("#chart").classList.remove("is-loading");
  }
}

async function loadStats() {
  try {
    state.stats = await api.statistics();
    renderStats();
  } catch (error) {
    $("#stats-body").innerHTML = `<p class="empty" style="padding:0">통계를 불러오지 못했어요: ${escapeHtml(error.message)}</p>`;
  }
}

async function refreshAll() {
  await Promise.all([loadRecords(), loadSummary(), loadStats()]);
}

function rangeStart() {
  // 마지막 날짜에서 N개월 전 (3월 31일의 1개월 전은 2월 말일: 달마다 일수가 달라 넘치지 않게 맞춤)
  if (state.range === "all" || !state.records.length) return null;
  const [y, m, d] = state.records[state.records.length - 1].date.split("-").map(Number);
  let year = y;
  let month = m - Number(state.range);
  while (month <= 0) { month += 12; year -= 1; }
  const lastDay = new Date(Date.UTC(year, month, 0)).getUTCDate();
  const day = Math.min(d, lastDay);
  return `${year}-${String(month).padStart(2, "0")}-${String(day).padStart(2, "0")}`;
}

function renderChart() {
  if ($("#view-data").hidden) return; // 보이지 않을 때는 그리지 않음 (크기 계산 때문)
  const all = state.records;
  const ma = movingAverage(all.map((r) => r.value), 20);
  const from = rangeStart();
  const startIndex = from ? Math.max(0, all.findIndex((r) => r.date > from)) : 0;
  $("#legend-ma").hidden = !state.showMA;
  drawLineChart($("#chart"), all.slice(startIndex), {
    ma: ma.slice(startIndex),
    showMA: state.showMA,
    unit: (state.summary && state.summary.dataset.unit) || "원",
  });
}

function renderStats() {
  const st = state.stats;
  if (!st || !st.count) {
    $("#stats-body").innerHTML = '<p class="empty" style="padding:0">데이터가 없어요.</p>';
    return;
  }
  const v = st.volatility;
  const dd = st.max_drawdown;
  const up = st.max_rally;
  const rise = st.top_rises[0];
  const fall = st.top_falls[0];
  const vsMa = st.latest_vs_ma20_pct;
  const vsDir = direction(vsMa ?? 0);
  const rows = st.monthly
    .map((m) => {
      const d = direction(m.change_pct ?? 0);
      return `<tr><td>${escapeHtml(m.month)}</td><td>${fmtNum(m.average)}</td><td>${fmtNum(m.last)}</td>
        <td class="${m.change_pct === null ? "" : d.cls}">${m.change_pct === null ? "-" : fmtPct(m.change_pct)}</td></tr>`;
    })
    .join("");
  $("#stats-body").innerHTML = `
    <dl class="stat-list">
      <div><dt>20일 이동평균</dt><dd class="num">${fmtNum(st.moving_averages.ma20)}원
        <small class="${vsDir.cls}">최신값이 ${vsMa === null ? "-" : fmtPct(vsMa)} ${vsMa > 0 ? "위" : vsMa < 0 ? "아래" : ""}</small></dd></div>
      <div><dt>일간 변동률 표준편차</dt><dd class="num">${v.daily_std_pct === null ? "-" : `${v.daily_std_pct}%`}
        <small>하루 평균 ${fmtNum(v.avg_abs_change)}원 움직임</small></dd></div>
      <div><dt>고점 대비 최대 하락</dt><dd class="num fall">${dd ? fmtPct(dd.pct) : "-"}
        <small>${dd ? `${compactDate(dd.start_date)} → ${compactDate(dd.end_date)}` : ""}</small></dd></div>
      <div><dt>저점 대비 최대 상승</dt><dd class="num rise">${up ? fmtPct(up.pct) : "-"}
        <small>${up ? `${compactDate(up.start_date)} → ${compactDate(up.end_date)}` : ""}</small></dd></div>
      <div><dt>하루 최대 상승</dt><dd class="num rise">${rise ? `${fmtSigned(rise.change)}원` : "-"}
        <small>${rise ? `${compactDate(rise.date)} (${fmtPct(rise.change_pct)})` : ""}</small></dd></div>
      <div><dt>하루 최대 하락</dt><dd class="num fall">${fall ? `${fmtSigned(fall.change)}원` : "-"}
        <small>${fall ? `${compactDate(fall.date)} (${fmtPct(fall.change_pct)})` : ""}</small></dd></div>
      <div><dt>오른 날 / 내린 날</dt><dd class="num">${st.up_days}일 / ${st.down_days}일</dd></div>
    </dl>
    <table class="month-table">
      <caption class="sr-only">월별 평균, 마지막 값, 전월 대비</caption>
      <thead><tr><th scope="col">월</th><th scope="col">평균</th><th scope="col">마지막 값</th><th scope="col">전월 대비</th></tr></thead>
      <tbody>${rows}</tbody>
    </table>`;
}

function renderTable() {
  const body = $("#data-body");
  body.replaceChildren();
  const prevByDate = new Map();
  state.records.forEach((r, i) => prevByDate.set(r.id, i > 0 ? state.records[i - 1].value : null));
  const q = state.filter.trim();
  const rows = state.records
    .filter((r) => !q || r.date.includes(q) || (r.memo || "").includes(q))
    .slice()
    .reverse();
  $("#data-count").textContent = q ? `(${rows.length} / ${state.records.length}개)` : `(${state.records.length}개)`;
  if (!rows.length) {
    body.innerHTML = '<tr><td colspan="5" class="empty">조건에 맞는 데이터가 없어요.</td></tr>';
    return;
  }
  for (const r of rows) body.appendChild(state.editingId === r.id ? editRow(r) : viewRow(r, prevByDate.get(r.id)));
}

function viewRow(r, prev) {
  const tr = document.createElement("tr");
  if (r.id === state.highlightId) tr.className = "is-new";
  const diff = prev === null || prev === undefined ? null : r.value - prev;
  const d = direction(diff ?? 0);
  tr.innerHTML = `
    <td class="c-date">${escapeHtml(r.date)}</td>
    <td class="c-num">${fmtNum(r.value)}</td>
    <td class="c-num ${diff === null ? "" : d.cls}">${diff === null ? "-" : `${d.mark} ${fmtNum(Math.abs(diff))}`}</td>
    <td class="c-memo"></td>
    <td class="c-act">
      <button class="btn btn-small btn-quiet" type="button" data-act="edit">수정</button>
      <button class="btn btn-small btn-quiet btn-danger" type="button" data-act="delete">삭제</button>
    </td>`;
  const memo = tr.querySelector(".c-memo");
  memo.textContent = r.memo || "";
  memo.title = r.memo || "";
  tr.querySelector('[data-act="edit"]').setAttribute("aria-label", `${r.date} 데이터 수정`);
  tr.querySelector('[data-act="delete"]').setAttribute("aria-label", `${r.date} 데이터 삭제`);
  tr.querySelector('[data-act="edit"]').addEventListener("click", () => {
    state.editingId = r.id;
    renderTable();
    const first = document.querySelector(".data-table input");
    if (first) first.focus();
  });
  tr.querySelector('[data-act="delete"]').addEventListener("click", () => removeRecord(r));
  return tr;
}

function editRow(r) {
  const tr = document.createElement("tr");
  tr.innerHTML = `
    <td><input type="date" aria-label="날짜" value="${escapeHtml(r.date)}" max="${todayKST()}"></td>
    <td class="c-num"><input class="cell-num" type="number" step="0.01" min="0.01" aria-label="값" value="${escapeHtml(r.value)}"></td>
    <td class="c-num">-</td>
    <td><input type="text" maxlength="200" aria-label="메모"></td>
    <td class="c-act">
      <button class="btn btn-small btn-primary" type="button" data-act="save">저장</button>
      <button class="btn btn-small btn-quiet" type="button" data-act="cancel">취소</button>
    </td>`;
  const [dateInput, valueInput, memoInput] = tr.querySelectorAll("input");
  memoInput.value = r.memo || "";
  const save = async () => {
    const changes = {};
    if (dateInput.value && dateInput.value !== r.date) changes.date = dateInput.value;
    const num = Number(valueInput.value);
    if (valueInput.value === "" || !Number.isFinite(num) || num <= 0) { toast("값에 0보다 큰 숫자를 넣어 주세요", "error"); return; }
    if (num !== r.value) changes.value = num;
    if (memoInput.value.trim() !== (r.memo || "")) changes.memo = memoInput.value.trim();
    if (!Object.keys(changes).length) { state.editingId = null; renderTable(); return; }
    try {
      const updated = await api.updateData(r.id, changes);
      state.editingId = null;
      state.highlightId = r.id;
      // 서버가 돌려준 값으로 표를 바로 바꾸고, 요약·통계·그래프는 이어서 다시 불러온다
      state.records = state.records
        .map((item) => (item.id === updated.id ? updated : item))
        .sort((a, b) => a.date.localeCompare(b.date));
      renderTable();
      toast(`${updated.date} 데이터를 수정했어요`);
      await refreshAll();
    } catch (error) {
      toast(`수정하지 못했어요: ${error.message}`, "error");
    }
  };
  tr.querySelector('[data-act="save"]').addEventListener("click", save);
  tr.querySelector('[data-act="cancel"]').addEventListener("click", () => { state.editingId = null; renderTable(); });
  tr.addEventListener("keydown", (e) => {
    if (e.key === "Enter") { e.preventDefault(); save(); }
    if (e.key === "Escape") { state.editingId = null; renderTable(); }
  });
  return tr;
}

async function removeRecord(r) {
  if (!window.confirm(`${r.date} (${fmtNum(r.value)}원) 데이터를 삭제할까요?`)) return;
  try {
    await api.deleteData(r.id);
    toast(`${r.date} 데이터를 삭제했어요`);
    await refreshAll();
  } catch (error) {
    toast(`삭제하지 못했어요: ${error.message}`, "error");
  }
}

async function exportFile(format) {
  try {
    const res = await api.exportData(format);
    const blob = await res.blob();
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `usdkrw_data_${todayKST().replaceAll("-", "")}.${format}`;
    document.body.appendChild(a);
    a.click();
    a.remove();
    setTimeout(() => URL.revokeObjectURL(url), 1000);
    toast(`${format.toUpperCase()} 파일을 내려받았어요`);
  } catch (error) {
    toast(`내려받지 못했어요: ${error.message}`, "error");
  }
}

function setupData() {
  $("#add-date").max = todayKST();
  $("#add-form").addEventListener("submit", async (e) => {
    e.preventDefault();
    const date = $("#add-date").value;
    const value = Number($("#add-value").value);
    const memo = $("#add-memo").value.trim();
    const err = $("#add-error");
    err.textContent = "";
    if (!date) { err.textContent = "날짜를 골라 주세요."; $("#add-date").focus(); return; }
    if ($("#add-value").value === "" || !Number.isFinite(value) || value <= 0) { err.textContent = "값에 0보다 큰 숫자를 넣어 주세요."; $("#add-value").focus(); return; }
    try {
      const rec = await api.createData({ date, value, memo });
      state.highlightId = rec.id;
      state.filter = "";
      $("#data-filter").value = "";
      $("#add-form").reset();
      toast(`${rec.date} 데이터를 추가했어요`);
      await refreshAll();
    } catch (error) {
      err.textContent = error instanceof ApiError ? error.message : "추가하지 못했어요.";
    }
  });
  $("#data-filter").addEventListener("input", (e) => { state.filter = e.target.value; renderTable(); });
  document.querySelectorAll("[data-export]").forEach((btn) => btn.addEventListener("click", () => exportFile(btn.dataset.export)));
  document.querySelectorAll("[data-range]").forEach((btn) => {
    btn.addEventListener("click", () => {
      state.range = btn.dataset.range;
      document.querySelectorAll("[data-range]").forEach((b) => b.setAttribute("aria-pressed", String(b === btn)));
      renderChart();
    });
  });
  $("#ma-toggle").addEventListener("change", (e) => { state.showMA = e.target.checked; renderChart(); });
  let resizeTimer;
  window.addEventListener("resize", () => { clearTimeout(resizeTimer); resizeTimer = setTimeout(renderChart, 150); });
}

/* ---------------- 시작 ---------------- */
async function start() {
  const ok = await wakeServer();
  if (!ok) return;
  await Promise.allSettled([loadSummary(), loadRecords(), loadConversations(), loadStats()]);
  renderMessages();
}

setupTheme();
setupTabs();
setupChat();
setupCopyDialog();
setupData();
start();
