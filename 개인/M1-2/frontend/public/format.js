// 숫자·날짜 표시와 AI 답변 글 꾸미기 (안전하게: 먼저 HTML 이스케이프)

const NUM2 = new Intl.NumberFormat("ko-KR", { minimumFractionDigits: 2, maximumFractionDigits: 2 });
const NUM0 = new Intl.NumberFormat("ko-KR", { maximumFractionDigits: 0 });

export function fmtNum(value, digits = 2) {
  if (value === null || value === undefined || Number.isNaN(Number(value))) return "-";
  return digits === 0 ? NUM0.format(value) : NUM2.format(value);
}

export function fmtSigned(value) {
  if (value === null || value === undefined) return "-";
  const sign = value > 0 ? "+" : value < 0 ? "-" : "";
  return sign + NUM2.format(Math.abs(value));
}

export function fmtPct(value, digits = 2) {
  if (value === null || value === undefined) return "-";
  const sign = value > 0 ? "+" : value < 0 ? "-" : "";
  return `${sign}${Math.abs(value).toFixed(digits)}%`;
}

// 상승 ▲(빨강), 하락 ▼(파랑), 보합 -  (한국 시장 관례)
export function direction(value) {
  if (value > 0) return { cls: "rise", mark: "▲", word: "상승" };
  if (value < 0) return { cls: "fall", mark: "▼", word: "하락" };
  return { cls: "", mark: "-", word: "보합" };
}

export function shortDate(iso) {
  // "2026-06-05" → "06.05"
  return iso ? `${iso.slice(5, 7)}.${iso.slice(8, 10)}` : "";
}

export function compactDate(iso) {
  // "2026-06-05" → "26.06.05" (좁은 칸에서 연도까지 보여 줄 때)
  return iso ? `${iso.slice(2, 4)}.${iso.slice(5, 7)}.${iso.slice(8, 10)}` : "";
}

export function fmtDateTime(iso) {
  if (!iso) return "";
  const d = new Date(iso);
  if (Number.isNaN(d.getTime())) return "";
  return d.toLocaleString("ko-KR", { month: "numeric", day: "numeric", hour: "2-digit", minute: "2-digit" });
}

export function escapeHtml(text) {
  return String(text ?? "")
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;")
    .replace(/'/g, "&#39;");
}

// AI 답변용 아주 작은 마크다운: **굵게**, 줄바꿈, "- " 목록, "1. " 목록만 지원
export function renderRichText(text) {
  const lines = escapeHtml(text).split(/\r?\n/);
  const out = [];
  let list = null;
  const inline = (s) => s.replace(/\*\*(.+?)\*\*/g, "<strong>$1</strong>").replace(/`([^`]+)`/g, "<strong>$1</strong>");
  const closeList = () => {
    if (list) { out.push(`<${list.tag}>${list.items.join("")}</${list.tag}>`); list = null; }
  };
  let para = [];
  const closePara = () => {
    if (para.length) { out.push(`<p>${para.map(inline).join("<br>")}</p>`); para = []; }
  };
  for (const raw of lines) {
    const line = raw.trim();
    const bullet = line.match(/^[-*•]\s+(.*)$/);
    const ordered = line.match(/^\d+[.)]\s+(.*)$/);
    if (bullet || ordered) {
      closePara();
      const tag = bullet ? "ul" : "ol";
      if (!list || list.tag !== tag) { closeList(); list = { tag, items: [] }; }
      list.items.push(`<li>${inline((bullet || ordered)[1])}</li>`);
    } else if (!line) {
      closePara();
      closeList();
    } else {
      closeList();
      para.push(line.replace(/^#{1,6}\s+/, ""));
    }
  }
  closePara();
  closeList();
  return out.join("");
}

export function todayKST() {
  // 브라우저 시간대와 관계없이 한국 날짜 (YYYY-MM-DD)
  const now = new Date(Date.now() + 9 * 3600 * 1000);
  return now.toISOString().slice(0, 10);
}
