const express = require("express");
const {
  generateRegistrationOptions,
  verifyRegistrationResponse,
  generateAuthenticationOptions,
  verifyAuthenticationResponse,
} = require("@simplewebauthn/server");
const { isoBase64URL } = require("@simplewebauthn/server/helpers");
const { RP_NAME, RP_ID, ORIGIN, CHALLENGE_TTL_MS } = require("../webauthn/rpConfig");
const {
  getOwner,
  listCredentials,
  listCredentialRefs,
  countCredentials,
  findCredentialById,
  addCredential,
  updateCredentialCounter,
  deleteCredential,
} = require("../webauthn/passkeyStore");
const { logEvent, maskSecret } = require("../webauthn/debugLog");
const { ensureLogId } = require("../webauthn/sessionLog");
const { requireAuth } = require("../middleware/authStub");

const router = express.Router();

// Supabase(postgrest) 에러는 message/details/hint/code를 갖고 있어서, 콘솔에 최대한
// 자세히 남겨야 Vercel Logs에서 원인을 바로 알아볼 수 있습니다 (RLS 위반이면 code 42501 등).
function describeError(error) {
  if (!error) return "unknown_error";
  const parts = [error.message, error.details, error.hint, error.code].filter(Boolean);
  return parts.length ? parts.join(" | ") : String(error);
}

// =========================================================
// 등록 (registration)
// =========================================================

// 등록 게이트: 패스키가 하나도 없으면(=사이트를 막 세팅하는 중) 누구나 최초 1명을 등록할 수 있게
// 열어두고, 이미 하나라도 있으면 그때부터는 "이미 로그인한 사람만" 새 기기를 추가할 수 있습니다.
// 이게 없으면 로그인 기능이 있어도 아무나 자기 패스키를 몰래 등록해서 남의 계정으로 로그인할 수 있습니다.
// (Supabase 조회가 비동기라 이 함수도 비동기입니다 — 예전 파일 버전과 달라진 부분)
async function canStartRegistration(req) {
  const existing = await countCredentials();
  if (existing === 0) return true;
  return Boolean(req.session && req.session.isAuthenticated);
}

// ---- 1) 등록 옵션 발급 ----
// 매 요청마다 @simplewebauthn/server가 새 challenge를 만들어줍니다(직접 고정값을 넘기지 않음).
// 그 challenge는 verify에서 다시 확인해야 하므로, 검증 전까지 서버 쪽 세션(쿠키)에 잠깐 보관합니다.
router.post("/register/options", async (req, res) => {
  try {
    if (!(await canStartRegistration(req))) {
      logEvent("register_blocked_not_authenticated", { sessionId: maskSecret(ensureLogId(req)) });
      return res.status(401).json({
        error: "unauthorized",
        message: "이미 등록된 패스키가 있어서, 로그인한 상태에서만 새 기기를 추가할 수 있어요.",
      });
    }

    const owner = await getOwner();

    const options = await generateRegistrationOptions({
      rpName: RP_NAME,
      rpID: RP_ID,
      userName: owner.name,
      userDisplayName: owner.displayName,
      userID: isoBase64URL.toBuffer(owner.id),
      attestationType: "none",
      excludeCredentials: await listCredentialRefs(),
      authenticatorSelection: {
        residentKey: "preferred",
        userVerification: "preferred",
      },
    });

    // 세션에 "지금 진행 중인 등록 챌린지"를 저장. verify 요청이 오면 이 값과 대조하고,
    // 성공/실패/만료 어떤 경우든 1회용이므로 바로 지웁니다.
    req.session.currentRegistration = {
      challenge: options.challenge,
      userID: owner.id,
      createdAt: Date.now(),
    };

    logEvent("register_options_issued", {
      sessionId: maskSecret(ensureLogId(req)),
      challenge: options.challenge,
    });

    res.json(options);
  } catch (error) {
    console.error("등록 옵션 생성 실패", error);
    logEvent("register_options_error", { sessionId: maskSecret(ensureLogId(req)), detail: describeError(error) });
    res.status(500).json({ error: "server_error", message: "등록 옵션을 만들지 못했어요." });
  }
});

// ---- 2) 등록 검증 ----
// 브라우저가 navigator.credentials.create()로 만든 attestation을 여기서 검증합니다.
// 이 핸들러 전체를 try/catch로 감싸서, Supabase 저장 단계에서 나는 에러(예: RLS 정책 위반)도
// 화면에 깔끔한 에러로 나오고 Vercel Logs에도 상세히 남도록 했습니다.
router.post("/register/verify", async (req, res) => {
  try {
    // options 발급 시점과 상태가 바뀌었을 수 있어서(예: 그 사이 로그아웃) 여기서도 다시 확인합니다.
    if (!(await canStartRegistration(req))) {
      delete req.session.currentRegistration;
      logEvent("register_blocked_not_authenticated", { sessionId: maskSecret(ensureLogId(req)) });
      return res.status(401).json({
        error: "unauthorized",
        message: "이미 등록된 패스키가 있어서, 로그인한 상태에서만 새 기기를 추가할 수 있어요.",
      });
    }

    const { attestationResponse, label } = req.body || {};
    const pending = req.session.currentRegistration;

    if (!attestationResponse) {
      return res.status(400).json({ verified: false, error: "missing_response", message: "등록 응답이 없어요." });
    }

    if (!pending) {
      return res.status(400).json({
        verified: false,
        error: "no_pending_challenge",
        message: "등록 요청 기록이 없어요. 처음부터 다시 시도해주세요.",
      });
    }

    // 임시 challenge 만료 처리: 시간이 지났으면 검증 자체를 진행하지 않고 바로 버립니다.
    const isExpired = Date.now() - pending.createdAt > CHALLENGE_TTL_MS;
    if (isExpired) {
      delete req.session.currentRegistration;
      logEvent("register_challenge_expired", { sessionId: maskSecret(ensureLogId(req)) });
      return res.status(400).json({ verified: false, error: "challenge_expired", message: "등록 시간이 지났어요. 다시 시도해주세요." });
    }

    let verification;
    try {
      verification = await verifyRegistrationResponse({
        response: attestationResponse,
        expectedChallenge: pending.challenge,
        expectedOrigin: ORIGIN,
        expectedRPID: RP_ID,
      });
    } catch (error) {
      delete req.session.currentRegistration;
      logEvent("register_verify_error", { sessionId: maskSecret(ensureLogId(req)), detail: describeError(error) });
      return res.status(400).json({ verified: false, error: "verification_failed", message: error.message });
    }

    // challenge는 성공하든 실패하든 1회용이라 여기서 확실히 지웁니다(재사용 공격 방지).
    delete req.session.currentRegistration;

    if (!verification.verified || !verification.registrationInfo) {
      logEvent("register_not_verified", { sessionId: maskSecret(ensureLogId(req)) });
      return res.status(400).json({ verified: false, error: "not_verified", message: "등록을 확인하지 못했어요." });
    }

    const { credential, credentialDeviceType, credentialBackedUp } = verification.registrationInfo;

    // credential.publicKey는 이름 그대로 "공개키"입니다(COSE 형식의 바이트열).
    // 이 값과 credential.id(공개 식별자)만 저장하고, 개인키에 해당하는 값은
    // attestation 응답 어디에도 담겨 오지 않으므로 저장할 방법 자체가 없습니다.
    const record = {
      id: credential.id,
      publicKey: isoBase64URL.fromBuffer(credential.publicKey),
      counter: credential.counter,
      transports: credential.transports || [],
      label: (typeof label === "string" && label.trim()) || "이름 없는 패스키",
      deviceType: credentialDeviceType,
      backedUp: credentialBackedUp,
    };

    await addCredential(record);

    logEvent("register_verified", {
      sessionId: maskSecret(ensureLogId(req)),
      credentialId: record.id,
      publicKey: record.publicKey,
      label: record.label,
    });

    res.json({ verified: true, credential: { id: record.id, label: record.label } });
  } catch (error) {
    // Supabase insert 실패(RLS 정책 위반 등) 같이 위에서 못 잡은 에러는 전부 여기서 잡습니다.
    console.error("패스키 등록 처리 실패", error);
    logEvent("register_verify_unexpected_error", { sessionId: maskSecret(ensureLogId(req)), detail: describeError(error) });
    res.status(500).json({ verified: false, error: "server_error", message: "등록 처리 중 서버 오류가 발생했어요. 잠시 후 다시 시도해주세요." });
  }
});

// ---- 등록된 패스키 목록 (이름 + 등록일만, 공개키는 내려주지 않음) ----
router.get("/passkeys", async (req, res) => {
  try {
    res.json({ passkeys: await listCredentials() });
  } catch (error) {
    console.error("패스키 목록 조회 실패", error);
    logEvent("passkeys_list_error", { detail: describeError(error) });
    res.status(500).json({ error: "server_error", message: "패스키 목록을 불러오지 못했어요." });
  }
});

// ---- 패스키 삭제 ----
// 로그인한 상태에서만 지울 수 있습니다. (지금 로그인에 쓴 패스키 본인을 지우는 것도 허용 —
// 그 경우 지금 세션은 로그아웃 전까지 유지되지만, 다음 로그인부터는 그 패스키를 못 씁니다.)
router.delete("/passkeys/:id", requireAuth, async (req, res) => {
  try {
    const result = await deleteCredential(req.params.id);

    if (!result.deleted) {
      return res.status(404).json({ deleted: false, error: "not_found", message: "그 패스키를 찾지 못했어요." });
    }

    logEvent("passkey_deleted", {
      sessionId: maskSecret(ensureLogId(req)),
      credentialId: req.params.id,
      remainingCount: result.remainingCount,
    });

    res.json({ deleted: true, remainingCount: result.remainingCount });
  } catch (error) {
    console.error("패스키 삭제 실패", error);
    logEvent("passkey_delete_error", { sessionId: maskSecret(ensureLogId(req)), detail: describeError(error) });
    res.status(500).json({ deleted: false, error: "server_error", message: "패스키 삭제 중 오류가 발생했어요." });
  }
});

// =========================================================
// 로그인 (authentication)
// =========================================================

// ---- 3) 로그인 옵션 발급 ----
// 등록 때와 마찬가지로 매 요청마다 새 challenge가 생기고, 검증 전까지 세션(쿠키)에 잠깐 둡니다.
router.post("/login/options", async (req, res) => {
  try {
    const allowCredentials = await listCredentialRefs();
    if (!allowCredentials.length) {
      return res.status(400).json({ error: "no_passkeys", message: "등록된 패스키가 없어요. 먼저 패스키를 등록해주세요." });
    }

    const options = await generateAuthenticationOptions({
      rpID: RP_ID,
      allowCredentials,
      userVerification: "preferred",
    });

    req.session.currentLogin = {
      challenge: options.challenge,
      createdAt: Date.now(),
    };

    logEvent("login_options_issued", {
      sessionId: maskSecret(ensureLogId(req)),
      challenge: options.challenge,
    });

    res.json(options);
  } catch (error) {
    console.error("로그인 옵션 생성 실패", error);
    logEvent("login_options_error", { sessionId: maskSecret(ensureLogId(req)), detail: describeError(error) });
    res.status(500).json({ error: "server_error", message: "로그인 옵션을 만들지 못했어요." });
  }
});

// ---- 4) 로그인 검증 ----
// 브라우저가 navigator.credentials.get()으로 만든 서명을, 등록 때 저장해둔 공개키로 검증합니다.
// 요구사항대로 실패하는 모든 경우에 401을 돌려줍니다.
router.post("/login/verify", async (req, res) => {
  try {
    const { authenticationResponse } = req.body || {};
    const pending = req.session.currentLogin;

    const fail = (errorCode, message, extra = {}) => {
      logEvent("login_failed", { sessionId: maskSecret(ensureLogId(req)), error: errorCode, ...extra });
      return res.status(401).json({ verified: false, error: errorCode, message });
    };

    if (!authenticationResponse) {
      return fail("missing_response", "로그인 응답이 없어요.");
    }

    if (!pending) {
      return fail("no_pending_challenge", "로그인 요청 기록이 없어요. 처음부터 다시 시도해주세요.");
    }

    // 임시 challenge 만료 + 재사용 방지: 한 번 쓴(또는 시간이 지난) challenge는 다시 통과시키지 않습니다.
    const isExpired = Date.now() - pending.createdAt > CHALLENGE_TTL_MS;
    delete req.session.currentLogin; // 성공/실패/만료 관계없이 1회용이므로 바로 폐기
    if (isExpired) {
      return fail("challenge_expired", "로그인 시간이 지났어요. 다시 시도해주세요.");
    }

    const storedCredential = await findCredentialById(authenticationResponse.id);
    if (!storedCredential) {
      return fail("unknown_credential", "등록되지 않은 패스키예요.");
    }

    let verification;
    try {
      verification = await verifyAuthenticationResponse({
        response: authenticationResponse,
        expectedChallenge: pending.challenge,
        expectedOrigin: ORIGIN,
        expectedRPID: RP_ID,
        credential: {
          id: storedCredential.id,
          publicKey: isoBase64URL.toBuffer(storedCredential.publicKey),
          counter: storedCredential.counter,
          transports: storedCredential.transports,
        },
      });
    } catch (error) {
      return fail("verification_failed", "서명 검증에 실패했어요.", { detail: describeError(error) });
    }

    if (!verification.verified) {
      return fail("not_verified", "서명 검증에 실패했어요.");
    }

    // 다음 로그인 때 재사용 탐지를 위해 이번에 인증기가 보고한 사용 횟수로 갱신.
    await updateCredentialCounter(storedCredential.id, verification.authenticationInfo.newCounter);

    req.session.isAuthenticated = true;
    req.session.credentialId = storedCredential.id;

    logEvent("login_verified", {
      sessionId: maskSecret(ensureLogId(req)),
      credentialId: storedCredential.id,
      label: storedCredential.label,
      newCounter: verification.authenticationInfo.newCounter,
    });

    res.json({ verified: true, user: { label: storedCredential.label } });
  } catch (error) {
    console.error("로그인 처리 실패", error);
    logEvent("login_verify_unexpected_error", { sessionId: maskSecret(ensureLogId(req)), detail: describeError(error) });
    res.status(500).json({ verified: false, error: "server_error", message: "로그인 처리 중 서버 오류가 발생했어요." });
  }
});

// ---- 5) 로그아웃 ----
// cookie-session은 세션 데이터를 서버가 아니라 쿠키에 들고 있어서, express-session의
// req.session.destroy()가 없습니다. req.session = null로 지우면 미들웨어가 알아서
// 빈 값으로 쿠키를 다시 내려줍니다.
router.post("/logout", (req, res) => {
  const sessionId = maskSecret(ensureLogId(req));
  req.session = null;
  logEvent("logout", { sessionId });
  res.json({ ok: true });
});

// ---- 현재 로그인 여부 확인 (버튼 상태 등 화면 초기화용) ----
router.get("/session", (req, res) => {
  res.json({ authenticated: Boolean(req.session && req.session.isAuthenticated) });
});

module.exports = router;
