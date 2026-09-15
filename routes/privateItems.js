const express = require("express");
const { requireAuth } = require("../middleware/authStub");

const router = express.Router();

// 실제로는 로그인한 사용자 소유의 데이터를 DB에서 조회해야 하지만,
// 지금은 화면 구조만 잡는 단계라 예시 데이터를 그대로 둡니다.
const PRIVATE_ITEMS = [
  { id: 1, title: "비공개 메모 1", detail: "아직 공개하지 않은 프로젝트 아이디어 초안." },
  { id: 2, title: "비공개 메모 2", detail: "다음 학기 계획을 정리 중인 개인 메모." },
  { id: 3, title: "비공개 메모 3", detail: "혼자 보는 회고 기록." },
  { id: 4, title: "비공개 메모 4", detail: "정리 안 된 링크 모음." },
];

// requireAuth는 req.session.isAuthenticated만 확인하고, 이 응답은 세션이 "누구"인지와 무관하게
// 항상 같은 PRIVATE_ITEMS를 돌려줍니다. 즉 쿼리·헤더·바디로 다른 계정의 자료를 지정해도
// 서버가 그 값을 아예 읽지 않으므로 위조가 통할 방법이 없습니다.
router.get("/items", requireAuth, (req, res) => {
  res.json({ items: PRIVATE_ITEMS });
});

module.exports = router;
