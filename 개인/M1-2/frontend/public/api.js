// 백엔드 API 호출. 주소는 config.js(배포 때 Vercel 환경 변수 API_BASE_URL로 만들어짐)에서 읽는다.

const configured = (window.APP_CONFIG && window.APP_CONFIG.API_BASE_URL) || "http://localhost:8000";
export const API_BASE = String(configured).replace(/\/+$/, "");

export class ApiError extends Error {
  constructor(message, status = 0) {
    super(message);
    this.status = status;
  }
}

async function request(path, { method = "GET", body, timeout = 30000, raw = false } = {}) {
  const controller = new AbortController();
  const timer = setTimeout(() => controller.abort(), timeout);
  let response;
  try {
    response = await fetch(API_BASE + path, {
      method,
      headers: body !== undefined ? { "Content-Type": "application/json" } : undefined,
      body: body !== undefined ? JSON.stringify(body) : undefined,
      signal: controller.signal,
    });
  } catch (error) {
    if (error.name === "AbortError") {
      throw new ApiError("서버 응답이 너무 늦어요. 잠시 뒤 다시 시도하세요.");
    }
    throw new ApiError("서버에 연결하지 못했어요. 인터넷 연결과 서버 주소를 확인하세요.");
  } finally {
    clearTimeout(timer);
  }

  if (raw && response.ok) return response;
  const text = await response.text();
  let data = null;
  if (text) {
    try {
      data = JSON.parse(text);
    } catch {
      data = null;
    }
  }
  if (!response.ok) {
    const detail = data && typeof data.detail === "string" ? data.detail : `요청이 실패했어요 (HTTP ${response.status}).`;
    throw new ApiError(detail, response.status);
  }
  return data;
}

const enc = encodeURIComponent;

export const api = {
  health: (opts) => request("/health", opts),
  summary: () => request("/api/data/summary"),
  statistics: () => request("/api/data/statistics"),
  listData: () => request("/api/data?order=asc"),
  createData: (body) => request("/api/data", { method: "POST", body }),
  updateData: (id, body) => request(`/api/data/${enc(id)}`, { method: "PUT", body }),
  deleteData: (id) => request(`/api/data/${enc(id)}`, { method: "DELETE" }),
  exportData: (format) => request(`/api/data/export?format=${enc(format)}`, { raw: true }),
  listConversations: () => request("/api/conversations?limit=100"),
  getConversation: (id) => request(`/api/conversations/${enc(id)}`),
  saveConversation: (body) => request("/api/conversations", { method: "POST", body }),
  deleteConversation: (id) => request(`/api/conversations/${enc(id)}`, { method: "DELETE" }),
  // 서버는 한 질문을 75초 안에 끝내고, 잠든 무료 서버가 깨는 시간(약 1분)까지 더해 150초 기다린다
  chat: (body) => request("/api/chat", { method: "POST", body, timeout: 150000 }),
};
