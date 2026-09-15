// 인증 미들웨어 자리(스텁). 지금은 패스키 로그인이 아직 없어서
// 어떤 요청이 와도 무조건 401을 돌려줍니다.
// 나중에 패스키(WebAuthn) 검증을 붙일 때, 이 함수 내부만 실제 세션/토큰 검사로
// 바꿔치기하면 됩니다. 라우트 쪽 코드(routes/privateItems.js)는 손댈 필요 없습니다.
function requireAuth(req, res, next) {
  // TODO(패스키 로그인 붙일 때): 여기서 세션 쿠키 또는 인증 토큰을 검증하고,
  // 성공하면 req.user를 채운 뒤 next()를 호출하도록 바꾼다.
  return res.status(401).json({
    error: "unauthorized",
    message: "로그인이 필요합니다. (아직 로그인 기능이 준비되지 않아 항상 거절됩니다)",
  });
}

module.exports = { requireAuth };
