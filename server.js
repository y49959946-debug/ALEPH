const express = require("express");
const path = require("path");
const privateItemsRouter = require("./routes/privateItems");

const app = express();
const PORT = process.env.PORT || 3000;

// 비공개 데이터 API. 정적 파일보다 먼저 등록해서 /api/private/* 경로가
// 항상 이 라우터(=인증 미들웨어)를 거치도록 합니다.
app.use("/api/private", privateItemsRouter);

// 기존 정적 사이트(index.html 및 하위 폴더들)는 그대로 서빙합니다.
app.use(express.static(path.join(__dirname)));

app.listen(PORT, () => {
  console.log(`http://localhost:${PORT} 에서 서버가 실행 중입니다.`);
});
