const express = require("express");
const { requireAuth } = require("../middleware/authStub");
const { findAccountById, getPrivateNote, savePrivateNote } = require("../webauthn/passkeyStore");

const router = express.Router();

// 데모용 고정 카드(로그인만 하면 누구에게나 같은 내용). 실제로 "계정마다 다른" 비공개
// 데이터인지 증명하는 건 아래 note(비공개 메모) 쪽입니다.
const PRIVATE_ITEMS = [
  { id: 1, title: "비공개 메모 1", detail: "아직 공개하지 않은 프로젝트 아이디어 초안." },
  { id: 2, title: "비공개 메모 2", detail: "다음 학기 계획을 정리 중인 개인 메모." },
  { id: 3, title: "비공개 메모 3", detail: "혼자 보는 회고 기록." },
  { id: 4, title: "비공개 메모 4", detail: "정리 안 된 링크 모음." },
];

// [계정 격리의 핵심] 아래 두 라우트 모두 "누구 것을 보여줄지"를 오직
// req.session.accountId(서버가 로그인 검증 때 서명된 쿠키에 심어둔 값)로만 정합니다.
// 클라이언트가 쿼리스트링/바디/헤더로 다른 계정의 id를 보내도 서버는 그 값을 아예 읽지
// 않으므로, 로그인한 계정 자신의 데이터 외에는 절대 조회·수정할 방법이 없습니다.
router.get("/items", requireAuth, async (req, res) => {
  try {
    const [account, note] = await Promise.all([
      findAccountById(req.session.accountId),
      getPrivateNote(req.session.accountId),
    ]);

    if (!account) {
      // 세션에 남은 accountId가 가리키는 계정이 더 이상 없는 경우(예: DB를 초기화한 경우).
      req.session = null;
      return res.status(401).json({ error: "unauthorized", message: "로그인이 필요합니다." });
    }

    res.json({
      account: { username: account.username, displayName: account.displayName },
      items: PRIVATE_ITEMS,
      note: { content: note.content },
    });
  } catch (error) {
    console.error("비공개 데이터 조회 실패", error);
    res.status(500).json({ error: "server_error", message: "비공개 데이터를 불러오지 못했어요." });
  }
});

router.put("/note", requireAuth, async (req, res) => {
  try {
    const { content } = req.body || {};
    if (typeof content !== "string" || content.length > 2000) {
      return res.status(400).json({ error: "invalid_input", message: "메모 내용을 확인해주세요. (최대 2000자)" });
    }

    const saved = await savePrivateNote(req.session.accountId, content);
    res.json({ saved: true, note: { content: saved.content } });
  } catch (error) {
    console.error("비공개 메모 저장 실패", error);
    res.status(500).json({ error: "server_error", message: "메모 저장에 실패했어요." });
  }
});

module.exports = router;
