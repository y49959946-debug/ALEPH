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

// requireAuth가 지금은 항상 401을 돌려주므로, 이 라우트는 실제로 동작하기 전까지
// 항상 막혀 있습니다. 패스키 로그인이 붙으면 자연스럽게 열립니다.
router.get("/items", requireAuth, (req, res) => {
  res.json({ items: PRIVATE_ITEMS });
});

module.exports = router;
