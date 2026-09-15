// 패스키 로그인 세션 체크. 예전에는 항상 401을 돌려주는 스텁이었는데,
// 이제 routes/auth.js의 로그인(login/verify)이 req.session.isAuthenticated를 채워주므로
// 여기서는 그 값만 확인합니다.
function requireAuth(req, res, next) {
  if (req.session && req.session.isAuthenticated) return next();

  return res.status(401).json({
    error: "unauthorized",
    message: "로그인이 필요합니다.",
  });
}

module.exports = { requireAuth };
