// 등록/로그인 흐름 디버그 로그. challenge/공개키처럼 비밀이 아닌 값은 그대로 남기고,
// 세션 식별자처럼 탈취 시 악용될 수 있는 값은 마스킹해서 남깁니다.
// 서버리스 환경에서는 로컬 파일이 요청 사이에 유지되지 않으므로, 콘솔(배포 플랫폼의 로그
// 뷰어에서 확인 가능)로 남깁니다.
function maskSecret(value) {
  if (!value || typeof value !== "string") return value;
  if (value.length <= 8) return "*".repeat(value.length);
  return `${value.slice(0, 4)}...${value.slice(-4)} (masked, len=${value.length})`;
}

function logEvent(event, fields = {}) {
  const entry = { timestamp: new Date().toISOString(), event, ...fields };
  console.log(JSON.stringify(entry));
  return entry;
}

module.exports = { logEvent, maskSecret };
