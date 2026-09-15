// cookie-session에는 express-session의 req.sessionID 같은 "서버가 발급한 식별자"가 없습니다
// (세션 데이터 자체가 서버가 아니라 서명된 쿠키 안에 있기 때문입니다).
// 로그에서 같은 방문자의 요청들을 묶어볼 수 있도록, 세션 안에 무작위 값을 하나 만들어
// 재사용합니다. 이 값은 비밀도 아니고 인증에도 쓰이지 않으며, 오직 로그 상관관계 확인용입니다.
const crypto = require("crypto");

function ensureLogId(req) {
  if (!req.session) return "no-session";
  if (!req.session._logId) {
    req.session._logId = crypto.randomBytes(16).toString("hex");
  }
  return req.session._logId;
}

module.exports = { ensureLogId };
