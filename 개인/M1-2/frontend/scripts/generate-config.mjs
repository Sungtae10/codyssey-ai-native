// Vercel 빌드 때 실행: 환경 변수 API_BASE_URL(백엔드 Render 주소)로 public/config.js를 만든다.
// 바닐라 HTML은 브라우저에서 환경 변수를 읽을 수 없어서, 빌드 단계에서 파일로 바꿔 넣는 방식이다.
// 로컬: API_BASE_URL을 안 주면 http://localhost:8000 으로 만든다.
import { writeFileSync } from "node:fs";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";

const here = dirname(fileURLToPath(import.meta.url));
const onVercel = process.env.VERCEL === "1";
const raw = (process.env.API_BASE_URL || "").trim();

if (!raw && onVercel) {
  console.error(
    "[config] API_BASE_URL 환경 변수가 없습니다. Vercel 프로젝트 Settings > Environment Variables에 " +
      "Render 백엔드 주소(예: https://내-서비스.onrender.com)를 넣고 다시 배포하세요.",
  );
  process.exit(1);
}

const url = (raw || "http://localhost:8000").replace(/\/+$/, "");
if (!/^https?:\/\/[^\s"'<>\\]+$/.test(url)) {
  console.error(`[config] API_BASE_URL 형식이 올바르지 않습니다: ${url}`);
  process.exit(1);
}
if (onVercel && url.startsWith("http://")) {
  console.warn("[config] 주의: https 사이트에서 http 주소를 부르면 브라우저가 막습니다. https 주소를 쓰세요.");
}

const out = join(here, "..", "public", "config.js");
const body =
  "// 자동 생성 파일 (scripts/generate-config.mjs). 직접 고치지 말고 API_BASE_URL 환경 변수를 바꾸세요.\n" +
  `window.APP_CONFIG = ${JSON.stringify({ API_BASE_URL: url }, null, 2)};\n`;
writeFileSync(out, body, "utf8");
console.log(`[config] public/config.js 생성 완료: API_BASE_URL=${url}`);
