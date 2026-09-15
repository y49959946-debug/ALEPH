const express = require("express");
const { requireAuth } = require("../middleware/authStub");
const {
  findAccountById,
  listPrivateNotes,
  createPrivateNote,
  updatePrivateNote,
  deletePrivateNote,
} = require("../webauthn/passkeyStore");

const router = express.Router();

// [계정 격리의 핵심] 아래 모든 라우트는 "누구 것을 보여줄지·바꿀지"를 오직
// req.session.accountId(서버가 로그인 검증 때 서명된 쿠키에 심어둔 값)로만 정합니다.
// URL의 :id는 "어느 메모인지"만 가리킬 뿐, 그 메모가 진짜 내 계정 것인지는
// webauthn/passkeyStore.js의 updatePrivateNote/deletePrivateNote가 account_id까지
// 조건에 함께 걸어서 다시 확인합니다 — 그래서 남의 메모 id를 알아내 요청해도
// 수정·삭제가 아예 먹히지 않습니다(계정 A로 로그인한 채 계정 B의 메모 id를 넣어도 404).
function isValidContent(content) {
  return typeof content === "string" && content.trim().length > 0 && content.length <= 2000;
}

router.get("/items", requireAuth, async (req, res) => {
  try {
    const [account, items] = await Promise.all([
      findAccountById(req.session.accountId),
      listPrivateNotes(req.session.accountId),
    ]);

    if (!account) {
      // 세션에 남은 accountId가 가리키는 계정이 더 이상 없는 경우(예: DB를 초기화한 경우).
      req.session = null;
      return res.status(401).json({ error: "unauthorized", message: "로그인이 필요합니다." });
    }

    res.json({
      account: { username: account.username, displayName: account.displayName },
      items,
    });
  } catch (error) {
    console.error("비공개 메모 조회 실패", error);
    res.status(500).json({ error: "server_error", message: "비공개 메모를 불러오지 못했어요." });
  }
});

router.post("/items", requireAuth, async (req, res) => {
  try {
    const { content } = req.body || {};
    if (!isValidContent(content)) {
      return res.status(400).json({ error: "invalid_input", message: "메모 내용을 입력해주세요. (최대 2000자)" });
    }

    const item = await createPrivateNote(req.session.accountId, content.trim());
    res.status(201).json({ created: true, item });
  } catch (error) {
    console.error("비공개 메모 추가 실패", error);
    res.status(500).json({ error: "server_error", message: "메모 추가에 실패했어요." });
  }
});

router.put("/items/:id", requireAuth, async (req, res) => {
  try {
    const { content } = req.body || {};
    if (!isValidContent(content)) {
      return res.status(400).json({ error: "invalid_input", message: "메모 내용을 입력해주세요. (최대 2000자)" });
    }

    const item = await updatePrivateNote(req.params.id, req.session.accountId, content.trim());
    if (!item) {
      return res.status(404).json({ error: "not_found", message: "그 메모를 찾지 못했어요." });
    }
    res.json({ updated: true, item });
  } catch (error) {
    console.error("비공개 메모 수정 실패", error);
    res.status(500).json({ error: "server_error", message: "메모 수정에 실패했어요." });
  }
});

router.delete("/items/:id", requireAuth, async (req, res) => {
  try {
    const result = await deletePrivateNote(req.params.id, req.session.accountId);
    if (!result.deleted) {
      return res.status(404).json({ error: "not_found", message: "그 메모를 찾지 못했어요." });
    }
    res.json({ deleted: true });
  } catch (error) {
    console.error("비공개 메모 삭제 실패", error);
    res.status(500).json({ error: "server_error", message: "메모 삭제에 실패했어요." });
  }
});

module.exports = router;
