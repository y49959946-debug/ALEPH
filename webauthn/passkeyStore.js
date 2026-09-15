// 등록된 패스키 저장소. Supabase(Postgres) 테이블에 저장합니다.
// 스키마는 supabase/schema.sql 참고 (webauthn_owner, webauthn_credentials 두 테이블).
//
// 여기 저장되는 값은 전부 "공개키"입니다. WebAuthn 표준상 개인키는 등록에 사용한
// 기기(브라우저의 보안 저장소, 보안키, 지문/얼굴 인식 모듈 등) 밖으로 절대 나가지 않고,
// 이 저장소에도, 서버 코드 어디에도 개인키가 존재한 적이 없습니다.
const { isoBase64URL, generateUserID } = require("@simplewebauthn/server/helpers");
const { supabaseAdmin } = require("./supabaseAdmin");

const OWNER_TABLE = "webauthn_owner";
const CREDENTIALS_TABLE = "webauthn_credentials";
const OWNER_ROW_ID = 1; // 이 사이트는 소유자가 1명뿐이라 고정 행 하나만 씁니다.

// 이 사이트는 아직 다중 사용자 로그인이 없어서, "사이트 소유자" 1명의
// WebAuthn user handle을 최초 1회 생성해서 저장해두고 계속 재사용합니다.
async function getOwner() {
  const { data: existing, error: selectError } = await supabaseAdmin
    .from(OWNER_TABLE)
    .select("owner_id,name,display_name")
    .eq("id", OWNER_ROW_ID)
    .maybeSingle();
  if (selectError) throw selectError;

  if (existing) {
    return { id: existing.owner_id, name: existing.name, displayName: existing.display_name };
  }

  const ownerID = await generateUserID();
  const owner = {
    id: isoBase64URL.fromBuffer(ownerID), // WebAuthn user.id (userHandle), 공개 식별자일 뿐 비밀값 아님
    name: "owner",
    displayName: "사이트 관리자",
  };

  const { error: insertError } = await supabaseAdmin.from(OWNER_TABLE).insert({
    id: OWNER_ROW_ID,
    owner_id: owner.id,
    name: owner.name,
    display_name: owner.displayName,
  });
  if (insertError) throw insertError;

  return owner;
}

// 목록 화면에는 공개키 원문까지 보낼 필요가 없어서 이름/날짜만 추려서 돌려줍니다.
async function listCredentials() {
  const { data, error } = await supabaseAdmin
    .from(CREDENTIALS_TABLE)
    .select("credential_id,label,created_at")
    .order("created_at", { ascending: true });
  if (error) throw error;
  return data.map((row) => ({ id: row.credential_id, label: row.label, createdAt: row.created_at }));
}

// 등록 게이트(부트스트랩 허용 여부)를 판단할 때 씀: 패스키가 하나라도 있는지만 빠르게 확인.
async function countCredentials() {
  const { count, error } = await supabaseAdmin
    .from(CREDENTIALS_TABLE)
    .select("credential_id", { count: "exact", head: true });
  if (error) throw error;
  return count || 0;
}

// { id, transports } 형태만 필요한 두 군데(등록 시 excludeCredentials,
// 로그인 시 allowCredentials)에서 함께 씁니다.
async function listCredentialRefs() {
  const { data, error } = await supabaseAdmin.from(CREDENTIALS_TABLE).select("credential_id,transports");
  if (error) throw error;
  return data.map((row) => ({ id: row.credential_id, transports: row.transports || [] }));
}

async function findCredentialById(id) {
  const { data, error } = await supabaseAdmin
    .from(CREDENTIALS_TABLE)
    .select("credential_id,public_key,counter,transports,label,device_type,backed_up,created_at")
    .eq("credential_id", id)
    .maybeSingle();
  if (error) throw error;
  if (!data) return null;
  return {
    id: data.credential_id,
    publicKey: data.public_key,
    counter: data.counter,
    transports: data.transports || [],
    label: data.label,
    deviceType: data.device_type,
    backedUp: data.backed_up,
    createdAt: data.created_at,
  };
}

async function addCredential(record) {
  const { error } = await supabaseAdmin.from(CREDENTIALS_TABLE).insert({
    credential_id: record.id,
    public_key: record.publicKey,
    counter: record.counter,
    transports: record.transports || [],
    label: record.label,
    device_type: record.deviceType,
    backed_up: record.backedUp,
  });
  if (error) throw error;
  return record;
}

// 로그인(인증) 성공 시 인증기가 보고한 사용 횟수(counter)로 갱신합니다.
// 이 값이 뒤로 가거나 그대로면 복제된 인증기를 의심할 수 있어서(재사용 공격 탐지),
// @simplewebauthn/server 문서에서도 반드시 저장해두라고 안내합니다.
async function updateCredentialCounter(id, counter) {
  const { error } = await supabaseAdmin.from(CREDENTIALS_TABLE).update({ counter }).eq("credential_id", id);
  if (error) throw error;
}

// 패스키 삭제. 삭제 후 남은 개수를 같이 돌려줘서(라우트가 응답에 그대로 실어 보낼 수 있게)
// 호출하는 쪽에서 별도로 다시 세지 않아도 되게 합니다.
async function deleteCredential(id) {
  const { error, count } = await supabaseAdmin
    .from(CREDENTIALS_TABLE)
    .delete({ count: "exact" })
    .eq("credential_id", id);
  if (error) throw error;

  const remainingCount = await countCredentials();
  return { deleted: (count || 0) > 0, remainingCount };
}

module.exports = {
  getOwner,
  listCredentials,
  listCredentialRefs,
  countCredentials,
  findCredentialById,
  addCredential,
  updateCredentialCounter,
  deleteCredential,
};
