const express = require("express");
const { generateRegistrationOptions, verifyRegistrationResponse } = require("@simplewebauthn/server");
const { isoBase64URL } = require("@simplewebauthn/server/helpers");
const { RP_NAME, RP_ID, ORIGIN, CHALLENGE_TTL_MS } = require("../webauthn/rpConfig");
const { getOwner, listCredentials, listCredentialsForExclude, addCredential } = require("../webauthn/passkeyStore");
const { logEvent, maskSecret } = require("../webauthn/debugLog");

const router = express.Router();

// ---- 1) 등록 옵션 발급 ----
// 매 요청마다 @simplewebauthn/server가 새 challenge를 만들어줍니다(직접 고정값을 넘기지 않음).
// 그 challenge는 verify에서 다시 확인해야 하므로, 검증 전까지 서버 쪽 세션에 잠깐 보관합니다.
router.post("/register/options", async (req, res) => {
  try {
    const owner = await getOwner();

    const options = await generateRegistrationOptions({
      rpName: RP_NAME,
      rpID: RP_ID,
      userName: owner.name,
      userDisplayName: owner.displayName,
      userID: isoBase64URL.toBuffer(owner.id),
      attestationType: "none",
      excludeCredentials: listCredentialsForExclude(),
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
      sessionId: maskSecret(req.sessionID),
      challenge: options.challenge,
    });

    res.json(options);
  } catch (error) {
    console.error("등록 옵션 생성 실패", error);
    res.status(500).json({ error: "server_error", message: "등록 옵션을 만들지 못했어요." });
  }
});

// ---- 2) 등록 검증 ----
// 브라우저가 navigator.credentials.create()로 만든 attestation을 여기서 검증합니다.
router.post("/register/verify", async (req, res) => {
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
    logEvent("register_challenge_expired", { sessionId: maskSecret(req.sessionID) });
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
    logEvent("register_verify_error", { sessionId: maskSecret(req.sessionID), message: error.message });
    return res.status(400).json({ verified: false, error: "verification_failed", message: error.message });
  }

  // challenge는 성공하든 실패하든 1회용이라 여기서 확실히 지웁니다(재사용 공격 방지).
  delete req.session.currentRegistration;

  if (!verification.verified || !verification.registrationInfo) {
    logEvent("register_not_verified", { sessionId: maskSecret(req.sessionID) });
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
    createdAt: new Date().toISOString(),
  };

  addCredential(record);

  logEvent("register_verified", {
    sessionId: maskSecret(req.sessionID),
    credentialId: record.id,
    publicKey: record.publicKey,
    label: record.label,
  });

  res.json({ verified: true, credential: { id: record.id, label: record.label, createdAt: record.createdAt } });
});

// ---- 등록된 패스키 목록 (이름 + 등록일만, 공개키는 내려주지 않음) ----
router.get("/passkeys", (req, res) => {
  res.json({ passkeys: listCredentials() });
});

module.exports = router;
