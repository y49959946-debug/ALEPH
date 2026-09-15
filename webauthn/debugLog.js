// 등록 흐름 디버그 로그. challenge/공개키처럼 비밀이 아닌 값은 그대로 남기고,
// 세션 ID처럼 탈취 시 악용될 수 있는 값은 마스킹해서 남깁니다.
const fs = require("fs");
const path = require("path");
const { DATA_DIR } = require("./rpConfig");

// DATA_DIR 밑에 두어서, 인스턴스별로 DATA_DIR만 바꾸면 로그도 같이 분리됩니다.
const LOG_DIR = path.join(DATA_DIR, "logs");
const LOG_FILE = path.join(LOG_DIR, "webauthn-debug.log");

function maskSecret(value) {
  if (!value || typeof value !== "string") return value;
  if (value.length <= 8) return "*".repeat(value.length);
  return `${value.slice(0, 4)}...${value.slice(-4)} (masked, len=${value.length})`;
}

function logEvent(event, fields = {}) {
  fs.mkdirSync(LOG_DIR, { recursive: true });
  const entry = { timestamp: new Date().toISOString(), event, ...fields };
  fs.appendFileSync(LOG_FILE, `${JSON.stringify(entry)}\n`, "utf8");
  return entry;
}

module.exports = { logEvent, maskSecret, LOG_FILE };
