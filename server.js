const express = require("express");
const session = require("express-session");
const path = require("path");
const privateItemsRouter = require("./routes/privateItems");
const authRouter = require("./routes/auth");

const app = express();
const PORT = process.env.PORT || 3000;

app.use(express.json());

// 이 세션은 두 가지 용도로 씁니다: (1) 등록/로그인 중 "지금 발급한 challenge"를 검증 전까지
// 임시로 들고 있는 것, (2) 로그인에 성공한 뒤 req.session.isAuthenticated로 로그인 상태를 유지하는 것.
// SESSION_SECRET은 실제 배포 전에 환경변수로 반드시 바꿔주세요.
app.use(
  session({
    secret: process.env.SESSION_SECRET || "dev-only-change-me",
    resave: false,
    saveUninitialized: false,
    cookie: {
      httpOnly: true,
      sameSite: "lax",
      secure: false, // HTTPS 배포 시 true로 바꿀 것 (localhost는 http여도 WebAuthn이 동작하는 예외 도메인)
      maxAge: 15 * 60 * 1000,
    },
  })
);

// 비공개 데이터 API. 정적 파일보다 먼저 등록해서 /api/private/* 경로가
// 항상 이 라우터(=인증 미들웨어)를 거치도록 합니다.
app.use("/api/private", privateItemsRouter);

// 패스키 등록/로그인/로그아웃 API.
app.use("/api/auth", authRouter);

// 브라우저용 @simplewebauthn/browser 번들만 콕 집어 내려줍니다.
// (node_modules 전체를 정적 서빙하면 서버 소스/의존성이 그대로 노출되므로 아래 static 설정에서 막아뒀습니다)
app.get("/vendor/simplewebauthn-browser.js", (req, res) => {
  res.type("application/javascript");
  res.sendFile(path.join(__dirname, "node_modules/@simplewebauthn/browser/dist/bundle/index.umd.min.js"));
});

// 서버 내부 파일(소스 코드, 저장된 공개키, 로그 등)이 정적 서빙으로 그대로 노출되지 않도록 차단.
const BLOCKED_STATIC_PREFIXES = [
  "/server.js",
  "/package.json",
  "/package-lock.json",
  "/middleware",
  "/routes",
  "/webauthn",
  "/data",
  "/logs",
  "/node_modules",
  "/.git",
];

app.use((req, res, next) => {
  const isBlocked = BLOCKED_STATIC_PREFIXES.some((prefix) => req.path === prefix || req.path.startsWith(`${prefix}/`));
  if (isBlocked) return res.status(404).end();
  next();
});

// 기존 정적 사이트(index.html 및 하위 폴더들)는 그대로 서빙합니다.
app.use(express.static(path.join(__dirname)));

app.listen(PORT, () => {
  console.log(`http://localhost:${PORT} 에서 서버가 실행 중입니다.`);
});
