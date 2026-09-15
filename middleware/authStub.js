// 패스키 로그인 세션 체크.
// isAuthenticated뿐 아니라 accountId까지 있어야 통과시킵니다 — accountId는 "누구로"
// 로그인했는지를 나타내는 값이라, 이게 없으면 어느 계정 데이터를 돌려줘야 할지 알 수 없기
// 때문입니다(라우트들이 항상 req.session.accountId만 보고 자기 계정 데이터만 다루도록 하는
// 전제 조건이기도 합니다).
function requireAuth(req, res, next) {
  if (req.session && req.session.isAuthenticated && req.session.accountId) return next();

  return res.status(401).json({
    error: "unauthorized",
    message: "로그인이 필요합니다.",
  });
}

module.exports = { requireAuth };
