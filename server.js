require("dotenv").config();

const express = require("express");
const cookieSession = require("cookie-session");
const path = require("path");
const privateItemsRouter = require("./routes/privateItems");
const authRouter = require("./routes/auth");
const { PORT } = require("./webauthn/rpConfig");

const app = express();

// Vercel 같은 프록시 뒤에서 돌아갈 때 필요한 설정입니다. 이게 없으면 실제로는 HTTPS로
// 들어온 요청인데도 Express/쿠키 라이브러리가 "암호화 안 된 연결"로 오해해서, secure 쿠키
// (등록/로그인 challenge, 로그인 상태를 담은 세션 쿠키)가 제대로 저장되지 않을 수 있습니다.
app.set("trust proxy", 1);

app.use(express.json());

const SESSION_SECRET = process.env.SESSION_SECRET;
if (!SESSION_SECRET && process.env.NODE_ENV === "production") {
  throw new Error(
    "SESSION_SECRET 환경변수가 설정되지 않았습니다. 배포 환경에서는 반드시 지정해야 합니다."
  );
}

// 세션 데이터(등록/로그인 중 발급한 challenge, 로그인 상태)를 서버가 들고 있지 않고
// 서명된 쿠키 안에 직접 담습니다(cookie-session). 요청마다 다른 서버 인스턴스가 응답할 수
// 있는 서버리스 환경(Vercel 등)에서도 그대로 동작하게 하기 위한 선택입니다.
app.use(
  cookieSession({
    name: "session",
    secret: SESSION_SECRET || "dev-only-change-me", // 개발 편의용 기본값. 배포 시엔 위에서 막습니다.
    httpOnly: true,
    sameSite: "lax",
    secure: process.env.NODE_ENV === "production", // HTTPS로 배포됐을 때만 Secure 쿠키를 씁니다.
    maxAge: 15 * 60 * 1000,
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

// 서버 내부 파일(소스 코드, .env, supabase 스키마 등)이 정적 서빙으로 그대로 노출되지 않도록 차단.
const BLOCKED_STATIC_PREFIXES = [
  "/server.js",
  "/package.json",
  "/package-lock.json",
  "/middleware",
  "/routes",
  "/webauthn",
  "/node_modules",
  "/.git",
  "/.env",
  "/supabase",
];

app.use((req, res, next) => {
  const isBlockedPrefix = BLOCKED_STATIC_PREFIXES.some((prefix) => req.path === prefix || req.path.startsWith(`${prefix}/`));
  if (isBlockedPrefix) return res.status(404).end();
  next();
});

// 기존 정적 사이트(index.html 및 하위 폴더들)는 그대로 서빙합니다.
app.use(express.static(path.join(__dirname)));

// Vercel 같은 서버리스 환경에서는 이 파일을 require만 하고(api/index.js) 직접 listen하지 않습니다.
// `node server.js`로 로컬에서 직접 실행했을 때만 listen 합니다.
if (require.main === module) {
  app.listen(PORT, () => {
    console.log(`http://localhost:${PORT} 에서 서버가 실행 중입니다.`);
  });
}

module.exports = app;
