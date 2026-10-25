// SVG 선 그래프 (라이브러리 없이 바닐라 JS)
// - 환율 선 + 20일 이동평균 선, 최고·최저 표시, 끝 값 직접 표시
// - 마우스·터치: 세로 보조선이 가장 가까운 날짜에 붙고, 툴팁에 두 선의 값을 함께 보여 줌
// - 키보드: 그래프에 초점을 두고 ← → Home End로 날짜 이동

import { fmtNum, direction } from "./format.js";

const NS = "http://www.w3.org/2000/svg";

function el(name, attrs = {}, parent) {
  const node = document.createElementNS(NS, name);
  for (const [key, value] of Object.entries(attrs)) node.setAttribute(key, String(value));
  if (parent) parent.appendChild(node);
  return node;
}

export function movingAverage(values, size) {
  const out = new Array(values.length).fill(null);
  let sum = 0;
  for (let i = 0; i < values.length; i += 1) {
    sum += values[i];
    if (i >= size) sum -= values[i - size];
    if (i >= size - 1) out[i] = sum / size;
  }
  return out;
}

function niceTicks(min, max, count = 5) {
  const span = max - min || 1;
  const raw = span / count;
  const mag = 10 ** Math.floor(Math.log10(raw));
  const norm = raw / mag;
  const step = (norm < 1.5 ? 1 : norm < 3 ? 2 : norm < 7 ? 5 : 10) * mag;
  const ticks = [];
  for (let v = Math.ceil(min / step) * step; v <= max + 1e-9; v += step) ticks.push(Number(v.toFixed(6)));
  return ticks;
}

function pathFrom(points) {
  let d = "";
  let pen = false;
  for (const p of points) {
    if (!p) { pen = false; continue; }
    d += `${pen ? "L" : "M"}${p[0].toFixed(1)},${p[1].toFixed(1)}`;
    pen = true;
  }
  return d;
}

/**
 * @param {HTMLElement} root  그래프를 넣을 곳 (position: relative)
 * @param {{date:string,value:number}[]} records  날짜 오름차순
 * @param {{ma:(number|null)[], showMA:boolean, unit:string}} options  ma는 records와 같은 길이 (전체 데이터로 미리 계산)
 */
export function drawLineChart(root, records, { ma = [], showMA = true, unit = "원" } = {}) {
  root.replaceChildren();
  if (records.length < 2) {
    const p = document.createElement("p");
    p.className = "empty";
    p.textContent = "그래프를 그리려면 데이터가 2개 이상 필요해요.";
    root.appendChild(p);
    return;
  }

  // 그래프를 실제 칸 너비로 그려 글자 크기가 화면 크기와 상관없이 읽히게 한다 (좁은 화면에서 축소되지 않도록)
  const W = Math.round(Math.max(300, Math.min(900, root.clientWidth || 760)));
  const H = W < 560 ? 240 : 300;
  const m = { t: 22, r: W < 560 ? 72 : 92, b: 34, l: W < 560 ? 44 : 56 };
  const pw = W - m.l - m.r;
  const ph = H - m.t - m.b;
  const n = records.length;
  const values = records.map((r) => r.value);
  const maVals = showMA ? ma : [];
  const visible = values.concat(maVals.filter((v) => v !== null));
  const lo = Math.min(...visible);
  const hi = Math.max(...visible);
  const pad = (hi - lo) * 0.1 || 1;
  const y0 = lo - pad;
  const y1 = hi + pad;
  const x = (i) => m.l + (n === 1 ? pw / 2 : (i / (n - 1)) * pw);
  const y = (v) => m.t + (1 - (v - y0) / (y1 - y0)) * ph;

  const first = records[0].date;
  const last = records[n - 1].date;
  const maxI = values.indexOf(Math.max(...values));
  const minI = values.indexOf(Math.min(...values));

  const svg = el("svg", {
    viewBox: `0 0 ${W} ${H}`,
    role: "img",
    tabindex: 0,
    "aria-label": `${first}부터 ${last}까지 환율 ${n}개. 최고 ${fmtNum(values[maxI])}${unit}(${records[maxI].date}), ` +
      `최저 ${fmtNum(values[minI])}${unit}(${records[minI].date}), 마지막 ${fmtNum(values[n - 1])}${unit}. ` +
      "왼쪽, 오른쪽 화살표로 날짜별 값을 읽을 수 있어요.",
  });

  // 가로 눈금선과 y축 값
  for (const t of niceTicks(y0, y1, 5)) {
    el("line", { x1: m.l, x2: m.l + pw, y1: y(t), y2: y(t), class: "grid-line" }, svg);
    el("text", { x: m.l - 8, y: y(t) + 4, "text-anchor": "end", class: "axis-text" }, svg).textContent = fmtNum(t, 0);
  }

  // x축: 기간이 길면 달마다, 짧으면 며칠마다
  const ticks = [];
  if (n > 70) {
    // 달이 바뀌는 날에만 눈금 (첫 달은 중간부터 시작하는 경우가 많아 빼고, 첫 눈금에 연도를 붙임)
    records.forEach((r, i) => {
      if (i > 0 && r.date.slice(0, 7) !== records[i - 1].date.slice(0, 7)) ticks.push(i);
    });
    if (!ticks.length) ticks.push(0);
  } else {
    const every = Math.max(1, Math.round(n / 6));
    for (let i = 0; i < n; i += every) ticks.push(i);
  }
  let lastX = -Infinity;
  let firstLabel = true;
  for (const i of ticks) {
    if (x(i) - lastX < 44) continue;
    lastX = x(i);
    const d = records[i].date;
    const month = Number(d.slice(5, 7));
    const label = n > 70
      ? (month === 1 || firstLabel ? `${d.slice(2, 4)}.${month}` : `${month}월`)
      : `${month}.${Number(d.slice(8, 10))}`;
    firstLabel = false;
    el("text", { x: x(i), y: H - 10, "text-anchor": "middle", class: "axis-text" }, svg).textContent = label;
  }

  // 선과 옅은 면
  const pts = values.map((v, i) => [x(i), y(v)]);
  el("path", { d: `${pathFrom(pts)}L${x(n - 1).toFixed(1)},${(m.t + ph).toFixed(1)}L${x(0).toFixed(1)},${(m.t + ph).toFixed(1)}Z`, class: "area-1" }, svg);
  if (showMA) {
    el("path", { d: pathFrom(maVals.map((v, i) => (v === null ? null : [x(i), y(v)]))), class: "series-2" }, svg);
  }
  el("path", { d: pathFrom(pts), class: "series-1" }, svg);

  // 최고·최저 (빨강=높음, 파랑=낮음), 글자는 글자 색으로
  const mark = (i, kind, text) => {
    const cx = x(i);
    const cy = y(values[i]);
    el("circle", { cx, cy, r: 5, class: `extreme-dot ${kind}` }, svg);
    const anchor = cx < m.l + 70 ? "start" : cx > m.l + pw - 70 ? "end" : "middle";
    const ty = kind === "max" ? cy - 11 : cy + 20;
    el("text", { x: cx, y: ty, "text-anchor": anchor, class: "label-text" }, svg).textContent = text;
  };
  if (maxI !== n - 1) mark(maxI, "max", `최고 ${fmtNum(values[maxI])}`);
  if (minI !== n - 1 && minI !== maxI) mark(minI, "min", `최저 ${fmtNum(values[minI])}`);

  // 끝 값 직접 표시 (두 선의 끝이 가까우면 이동평균 글자는 생략하고 범례·툴팁에 맡김)
  const endY = y(values[n - 1]);
  el("circle", { cx: x(n - 1), cy: endY, r: 4.5, class: "end-dot-1" }, svg);
  el("text", { x: x(n - 1) + 10, y: endY + 4, class: "label-text" }, svg).textContent = fmtNum(values[n - 1]);
  const lastMa = showMA ? maVals[n - 1] : null;
  if (lastMa !== null && lastMa !== undefined) {
    const maY = y(lastMa);
    el("circle", { cx: x(n - 1), cy: maY, r: 4, class: "end-dot-2" }, svg);
    if (Math.abs(maY - endY) >= 16) {
      el("text", { x: x(n - 1) + 10, y: maY + 4, class: "label-muted" }, svg).textContent = `평균 ${fmtNum(lastMa)}`;
    }
  }

  // 마우스 반응 층
  const cross = el("line", { y1: m.t, y2: m.t + ph, class: "crosshair", visibility: "hidden" }, svg);
  const dot2 = el("circle", { r: 4, class: "hover-dot-2", visibility: "hidden" }, svg);
  const dot1 = el("circle", { r: 5, class: "hover-dot-1", visibility: "hidden" }, svg);
  const hit = el("rect", { x: m.l, y: m.t, width: pw, height: ph, fill: "transparent" }, svg);

  const tip = document.createElement("div");
  tip.className = "tooltip";
  tip.hidden = true;
  root.append(svg, tip);

  let current = n - 1;
  const show = (i) => {
    current = Math.max(0, Math.min(n - 1, i));
    const cx = x(current);
    cross.setAttribute("x1", cx);
    cross.setAttribute("x2", cx);
    cross.setAttribute("visibility", "visible");
    dot1.setAttribute("cx", cx);
    dot1.setAttribute("cy", y(values[current]));
    dot1.setAttribute("visibility", "visible");
    const mv = showMA ? maVals[current] : null;
    if (mv !== null && mv !== undefined) {
      dot2.setAttribute("cx", cx);
      dot2.setAttribute("cy", y(mv));
      dot2.setAttribute("visibility", "visible");
    } else {
      dot2.setAttribute("visibility", "hidden");
    }

    tip.replaceChildren();
    const date = document.createElement("div");
    date.className = "t-date";
    date.textContent = records[current].date;
    tip.appendChild(date);
    const row = (value, keyVar, label) => {
      const r = document.createElement("div");
      r.className = "t-row";
      const key = document.createElement("span");
      key.className = "t-key";
      key.style.background = `var(${keyVar})`;
      const strong = document.createElement("strong");
      strong.textContent = `${fmtNum(value)}${unit}`;
      const name = document.createElement("span");
      name.textContent = label;
      r.append(key, strong, name);
      tip.appendChild(r);
    };
    row(values[current], "--series-1", "환율");
    if (mv !== null && mv !== undefined) row(mv, "--series-2", "20일 평균");
    if (current > 0) {
      const diff = values[current] - values[current - 1];
      const dir = direction(diff);
      const delta = document.createElement("div");
      delta.className = `t-delta ${dir.cls}`;
      delta.textContent = `전일 대비 ${dir.mark} ${fmtNum(Math.abs(diff))}${unit}`;
      tip.appendChild(delta);
    }
    tip.hidden = false;

    // 툴팁 위치: 화면 크기에 맞춰 좌우로
    const box = svg.getBoundingClientRect();
    const scale = box.width / W;
    const px = cx * scale;
    const tipW = tip.offsetWidth || 170;
    const left = px + 14 + tipW > box.width ? px - 14 - tipW : px + 14;
    tip.style.left = `${Math.max(0, left)}px`;
    tip.style.top = `${Math.max(0, m.t * scale)}px`;
  };
  const hide = () => {
    cross.setAttribute("visibility", "hidden");
    dot1.setAttribute("visibility", "hidden");
    dot2.setAttribute("visibility", "hidden");
    tip.hidden = true;
  };
  const indexFromEvent = (event) => {
    const box = svg.getBoundingClientRect();
    const vx = ((event.clientX - box.left) / box.width) * W;
    return Math.round(((vx - m.l) / pw) * (n - 1));
  };

  hit.addEventListener("pointermove", (e) => show(indexFromEvent(e)));
  hit.addEventListener("pointerdown", (e) => show(indexFromEvent(e)));
  hit.addEventListener("pointerleave", () => { if (document.activeElement !== svg) hide(); });
  svg.addEventListener("focus", () => show(current));
  svg.addEventListener("blur", hide);
  svg.addEventListener("keydown", (e) => {
    const step = e.shiftKey ? 5 : 1;
    if (e.key === "ArrowLeft") { show(current - step); e.preventDefault(); }
    else if (e.key === "ArrowRight") { show(current + step); e.preventDefault(); }
    else if (e.key === "Home") { show(0); e.preventDefault(); }
    else if (e.key === "End") { show(n - 1); e.preventDefault(); }
    else if (e.key === "Escape") { hide(); }
  });
}

/** 요약 보드용 작은 그래프 (장식이 아니라 1년 모양을 보여 주는 용도, 숫자는 보드 글자가 담당) */
export function drawSparkline(root, values) {
  root.replaceChildren();
  if (values.length < 2) return;
  const W = 220;
  const H = 56;
  const pad = 6;
  const lo = Math.min(...values);
  const hi = Math.max(...values);
  const x = (i) => pad + (i / (values.length - 1)) * (W - pad * 2);
  const y = (v) => pad + (1 - (v - lo) / (hi - lo || 1)) * (H - pad * 2);
  const svg = el("svg", { viewBox: `0 0 ${W} ${H}`, class: "board-spark", "aria-hidden": "true", focusable: "false" });
  const pts = values.map((v, i) => [x(i), y(v)]);
  el("path", { d: `${pathFrom(pts)}L${x(values.length - 1)},${H}L${x(0)},${H}Z`, class: "spark-area" }, svg);
  el("path", { d: pathFrom(pts), class: "spark-line" }, svg);
  const maxI = values.indexOf(hi);
  const minI = values.indexOf(lo);
  el("circle", { cx: x(maxI), cy: y(hi), r: 4, class: "spark-dot max" }, svg);
  el("circle", { cx: x(minI), cy: y(lo), r: 4, class: "spark-dot min" }, svg);
  root.appendChild(svg);
}
