// WebAuthn Relying Party 설정을 한 곳에 모아둡니다.
// 배포 도메인이 정해지면 RP_ID / ORIGIN만 바꾸면 됩니다.
const PORT = process.env.PORT || 3000;

const RP_NAME = "행로 (HR)";
const RP_ID = process.env.WEBAUTHN_RP_ID || "localhost";
const ORIGIN = process.env.WEBAUTHN_ORIGIN || `http://localhost:${PORT}`;

// 등록 챌린지가 세션에 살아있을 수 있는 최대 시간.
// 이 시간이 지나면 verify 요청이 와도 만료 처리하고 challenge를 버립니다.
// (테스트용으로 짧게 보고 싶으면 WEBAUTHN_CHALLENGE_TTL_MS 환경변수로 덮어쓸 수 있습니다.)
const CHALLENGE_TTL_MS = Number(process.env.WEBAUTHN_CHALLENGE_TTL_MS) || 5 * 60 * 1000;

module.exports = { PORT, RP_NAME, RP_ID, ORIGIN, CHALLENGE_TTL_MS };
