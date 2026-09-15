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
  generateAccountUserHandle,
  findAccountByUsername,
  findAccountById,
  createAccount,
  listCredentials,
  listCredentialRefs,
  listCredentialRefsForAccount,
  countCredentialsForAccount,
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
// 자세히 남겨야 Vercel Logs에서 원인을 바로 알아볼 수 있습니다 (RLS 위반이면 code 42501,
// unique 제약 위반이면 code 23505 등).
function describeError(error) {
  if (!error) return "unknown_error";
  const parts = [error.message, error.details, error.hint, error.code].filter(Boolean);
  return parts.length ? parts.join(" | ") : String(error);
}

function isUniqueViolation(error) {
  return Boolean(error && error.code === "23505");
}

// =========================================================
// 등록 (registration) — 두 가지 모드가 있습니다.
//   1) mode: "signup"     — 계정이 아예 없는 사람이 아이디를 정해서 "패스키로 계정 만들기".
//                            로그인 상태와 무관하게 항상 열려 있습니다(=누구나 새 계정을 만들 수 있음).
//   2) mode: "add-device" — 이미 로그인한 사람이 "내 계정에 새 기기(패스키) 추가"(기본값).
//                            반드시 로그인한 상태여야 하고, 추가되는 패스키는 지금 로그인한
//                            계정(req.session.accountId)에만 연결됩니다.
// 이 구분이 계정 격리의 시작점입니다: signup은 새 account_id를 만들고, add-device는
// 절대로 새 계정을 만들지 않고 기존 내 계정에만 붙습니다 — 로그인 없이 남의 계정에
// 패스키를 슬쩍 추가할 방법이 없습니다.
// =========================================================

// ---- 1) 등록 옵션 발급 ----
// 매 요청마다 @simplewebauthn/server가 새 challenge를 만들어줍니다(직접 고정값을 넘기지 않음).
// 그 challenge는 verify에서 다시 확인해야 하므로, 검증 전까지 서버 쪽 세션(쿠키)에 잠깐 보관합니다.
router.post("/register/options", async (req, res) => {
  try {
    const { mode, username, displayName } = req.body || {};

    if (mode === "signup") {
      const trimmedUsername = typeof username === "string" ? username.trim() : "";
      const trimmedDisplayName = typeof displayName === "string" ? displayName.trim() : "";

      if (!trimmedUsername || !trimmedDisplayName) {
        return res.status(400).json({ error: "invalid_input", message: "아이디와 표시 이름을 모두 입력해주세요." });
      }
      if (trimmedUsername.length > 30 || trimmedDisplayName.length > 30) {
        return res.status(400).json({ error: "invalid_input", message: "아이디와 표시 이름은 30자 이하로 입력해주세요." });
      }

      const existing = await findAccountByUsername(trimmedUsername);
      if (existing) {
        return res.status(409).json({ error: "username_taken", message: "이미 사용 중인 아이디예요. 다른 아이디를 입력해주세요." });
      }

      const userHandle = await generateAccountUserHandle();

      const options = await generateRegistrationOptions({
        rpName: RP_NAME,
        rpID: RP_ID,
        userName: trimmedUsername,
        userDisplayName: trimmedDisplayName,
        userID: isoBase64URL.toBuffer(userHandle),
        attestationType: "none",
        excludeCredentials: [], // 아직 존재하지 않는 계정이라 제외할 목록이 없습니다.
        authenticatorSelection: {
          residentKey: "preferred",
          userVerification: "preferred",
        },
      });

      // 계정은 아직 DB에 만들지 않았습니다 — verify에서 등록(attestation) 검증까지
      // 끝나야 실제로 만듭니다. 그래야 등록을 중간에 취소해도 빈 계정이 남지 않습니다.
      req.session.currentRegistration = {
        mode: "signup",
        challenge: options.challenge,
        userHandle,
        username: trimmedUsername,
        displayName: trimmedDisplayName,
        createdAt: Date.now(),
      };

      logEvent("register_options_issued", {
        sessionId: maskSecret(ensureLogId(req)),
        mode: "signup",
        challenge: options.challenge,
      });

      return res.json(options);
    }

    // mode === "add-device" (기본값)
    if (!(req.session && req.session.isAuthenticated && req.session.accountId)) {
      logEvent("register_blocked_not_authenticated", { sessionId: maskSecret(ensureLogId(req)) });
      return res.status(401).json({
        error: "unauthorized",
        message: "로그인한 상태에서만 내 계정에 새 기기를 추가할 수 있어요.",
      });
    }

    const account = await findAccountById(req.session.accountId);
    if (!account) {
      req.session = null;
      return res.status(401).json({ error: "unauthorized", message: "계정을 찾지 못했어요. 다시 로그인해주세요." });
    }

    const options = await generateRegistrationOptions({
      rpName: RP_NAME,
      rpID: RP_ID,
      userName: account.username,
      userDisplayName: account.displayName,
      userID: isoBase64URL.toBuffer(account.userHandle),
      attestationType: "none",
      excludeCredentials: await listCredentialRefsForAccount(account.id),
      authenticatorSelection: {
        residentKey: "preferred",
        userVerification: "preferred",
      },
    });

    req.session.currentRegistration = {
      mode: "add-device",
      challenge: options.challenge,
      accountId: account.id,
      createdAt: Date.now(),
    };

    logEvent("register_options_issued", {
      sessionId: maskSecret(ensureLogId(req)),
      mode: "add-device",
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
// 이 핸들러 전체를 try/catch로 감싸서, Supabase 저장 단계에서 나는 에러(예: RLS 정책 위반,
// 아이디 중복)도 화면에 깔끔한 에러로 나오고 Vercel Logs에도 상세히 남도록 했습니다.
router.post("/register/verify", async (req, res) => {
  try {
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

    // add-device 모드는 options 발급 시점과 상태가 바뀌었을 수 있어서(예: 그 사이 로그아웃)
    // 여기서도 다시 로그인 + 같은 계정인지 확인합니다.
    if (pending.mode === "add-device") {
      const stillSameAccount =
        req.session && req.session.isAuthenticated && req.session.accountId === pending.accountId;
      if (!stillSameAccount) {
        delete req.session.currentRegistration;
        logEvent("register_blocked_not_authenticated", { sessionId: maskSecret(ensureLogId(req)) });
        return res.status(401).json({
          error: "unauthorized",
          message: "로그인한 상태에서만 내 계정에 새 기기를 추가할 수 있어요.",
        });
      }
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
        requireUserVerification: false,
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

    let accountId;
    let account;

    if (pending.mode === "signup") {
      // options 발급과 verify 사이에 같은 아이디로 다른 사람이 먼저 가입했을 수 있어 한 번 더 확인.
      try {
        account = await createAccount({
          userHandle: pending.userHandle,
          username: pending.username,
          displayName: pending.displayName,
        });
      } catch (error) {
        if (isUniqueViolation(error)) {
          logEvent("register_username_taken", { sessionId: maskSecret(ensureLogId(req)), username: pending.username });
          return res.status(409).json({
            verified: false,
            error: "username_taken",
            message: "그 사이 이미 사용된 아이디예요. 처음부터 다시 시도해주세요.",
          });
        }
        throw error;
      }
      accountId = account.id;
    } else {
      accountId = pending.accountId;
      account = await findAccountById(accountId);
    }

    // credential.publicKey는 이름 그대로 "공개키"입니다(COSE 형식의 바이트열).
    // 이 값과 credential.id(공개 식별자)만 저장하고, 개인키에 해당하는 값은
    // attestation 응답 어디에도 담겨 오지 않으므로 저장할 방법 자체가 없습니다.
    const record = {
      id: credential.id,
      accountId,
      publicKey: isoBase64URL.fromBuffer(credential.publicKey),
      counter: credential.counter,
      transports: credential.transports || [],
      label: (typeof label === "string" && label.trim()) || "이름 없는 패스키",
      deviceType: credentialDeviceType,
      backedUp: credentialBackedUp,
    };

    await addCredential(record);

    // 방금 등록을 마친 패스키의 주인이 지금 이 브라우저인 게 확실하므로(등록 = 이 기기에서
    // 개인키를 막 만든 것) 바로 그 계정으로 로그인 상태를 만들어줍니다.
    req.session.isAuthenticated = true;
    req.session.accountId = accountId;
    req.session.credentialId = record.id;

    logEvent("register_verified", {
      sessionId: maskSecret(ensureLogId(req)),
      mode: pending.mode,
      accountId,
      credentialId: record.id,
      publicKey: record.publicKey,
      label: record.label,
    });

    res.json({
      verified: true,
      credential: { id: record.id, label: record.label },
      account: { username: account.username, displayName: account.displayName },
    });
  } catch (error) {
    // Supabase insert 실패(RLS 정책 위반 등) 같이 위에서 못 잡은 에러는 전부 여기서 잡습니다.
    console.error("패스키 등록 처리 실패", error);
    logEvent("register_verify_unexpected_error", { sessionId: maskSecret(ensureLogId(req)), detail: describeError(error) });
    res.status(500).json({ verified: false, error: "server_error", message: "등록 처리 중 서버 오류가 발생했어요. 잠시 후 다시 시도해주세요." });
  }
});

// ---- 등록된 패스키 목록 (이름 + 등록일만, 공개키는 내려주지 않음) ----
// 로그인하지 않았으면 "누구 것"을 보여줘야 할지 알 수 없으므로 빈 목록을 돌려줍니다.
// (다른 계정이 몇 개의 기기를 등록했는지조차 로그인 없이는 알 수 없게 합니다.)
router.get("/passkeys", async (req, res) => {
  try {
    if (!(req.session && req.session.isAuthenticated && req.session.accountId)) {
      return res.json({ passkeys: [] });
    }
    res.json({ passkeys: await listCredentials(req.session.accountId) });
  } catch (error) {
    console.error("패스키 목록 조회 실패", error);
    logEvent("passkeys_list_error", { detail: describeError(error) });
    res.status(500).json({ error: "server_error", message: "패스키 목록을 불러오지 못했어요." });
  }
});

// ---- 패스키 삭제 ----
// 로그인한 상태에서만, 그리고 "내 계정" 소유의 패스키만 지울 수 있습니다
// (webauthn/passkeyStore.js의 deleteCredential이 account_id까지 조건에 걸어서 이중으로 막습니다).
// 마지막 남은 패스키는 삭제를 막습니다 — 그것까지 지우면 그 계정은 로그인할 방법이 없어지기 때문입니다.
router.delete("/passkeys/:id", requireAuth, async (req, res) => {
  try {
    const remaining = await countCredentialsForAccount(req.session.accountId);
    if (remaining <= 1) {
      return res.status(400).json({
        deleted: false,
        error: "last_passkey",
        message: "마지막 남은 패스키는 삭제할 수 없어요. 먼저 다른 기기로 패스키를 하나 더 등록해주세요.",
      });
    }

    const result = await deleteCredential(req.params.id, req.session.accountId);

    if (!result.deleted) {
      return res.status(404).json({ deleted: false, error: "not_found", message: "그 패스키를 찾지 못했어요." });
    }

    logEvent("passkey_deleted", {
      sessionId: maskSecret(ensureLogId(req)),
      accountId: req.session.accountId,
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
// allowCredentials는 계정과 무관하게 사이트 전체 패스키 목록입니다 — "usernameless" 로그인이라
// 브라우저가 그중 이 기기에 있는 패스키를 사용자에게 고르게 하고, 어느 계정인지는 다음
// verify 단계에서 credential.id로 서버가 역으로 찾아냅니다.
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
// 요구사항대로 실패하는 모든 경우에 401을 돌려줍니다. 검증에 성공하면, 그 패스키에 저장된
// account_id를 그대로 세션에 심습니다 — 로그인은 항상 "이 패스키가 어느 계정 것인지"를
// 서버가 DB에서 찾은 값으로만 정하고, 클라이언트가 계정을 지정할 방법은 없습니다.
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
          requireUserVerification: false,
      });
    } catch (error) {
      return fail("verification_failed", `서명 검증에 실패했어요. (${describeError(error)})`, { detail: describeError(error) });
    }

    if (!verification.verified) {
      return fail("not_verified", "서명 검증에 실패했어요.");
    }

    // 다음 로그인 때 재사용 탐지를 위해 이번에 인증기가 보고한 사용 횟수로 갱신.
    await updateCredentialCounter(storedCredential.id, verification.authenticationInfo.newCounter);

    const account = await findAccountById(storedCredential.accountId);
    if (!account) {
      return fail("server_error", "이 패스키가 연결된 계정을 찾지 못했어요.");
    }

    req.session.isAuthenticated = true;
    req.session.accountId = storedCredential.accountId;
    req.session.credentialId = storedCredential.id;

    logEvent("login_verified", {
      sessionId: maskSecret(ensureLogId(req)),
      accountId: storedCredential.accountId,
      credentialId: storedCredential.id,
      label: storedCredential.label,
      newCounter: verification.authenticationInfo.newCounter,
    });

    res.json({
      verified: true,
      user: { label: storedCredential.label, username: account.username, displayName: account.displayName },
    });
  } catch (error) {
    console.error("로그인 처리 실패", error);
    logEvent("login_verify_unexpected_error", { sessionId: maskSecret(ensureLogId(req)), detail: describeError(error) });
    res.status(500).json({ verified: false, error: "server_error", message: "로그인 처리 중 서버 오류가 발생했어요." });
  }
});

// ---- 5) 로그아웃 ----
// cookie-session은 세션 데이터를 서버가 아니라 쿠키에 들고 있어서, express-session의
// req.session.destroy()가 없습니다. req.session = null로 지우면 미들웨어가 알아서
// 빈 값으로 쿠키를 다시 내려줍니다(accountId 포함 전부 삭제).
router.post("/logout", (req, res) => {
  const sessionId = maskSecret(ensureLogId(req));
  req.session = null;
  logEvent("logout", { sessionId });
  res.json({ ok: true });
});

// ---- 현재 로그인 여부 확인 (버튼 상태, 화면 초기화용) ----
// 로그인한 상태면 어느 계정인지(username/displayName)도 같이 돌려줘서 화면에 표시합니다.
router.get("/session", async (req, res) => {
  try {
    if (!(req.session && req.session.isAuthenticated && req.session.accountId)) {
      return res.json({ authenticated: false });
    }

    const account = await findAccountById(req.session.accountId);
    if (!account) {
      req.session = null;
      return res.json({ authenticated: false });
    }

    res.json({
      authenticated: true,
      account: { username: account.username, displayName: account.displayName },
    });
  } catch (error) {
    console.error("세션 확인 실패", error);
    logEvent("session_check_error", { detail: describeError(error) });
    res.status(500).json({ authenticated: false, error: "server_error" });
  }
});

module.exports = router;
