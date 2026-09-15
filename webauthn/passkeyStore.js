// 계정 / 패스키 / 비공개 메모 저장소. Supabase(Postgres) 테이블에 저장합니다.
// 스키마는 supabase/schema.sql 참고 (webauthn_accounts, webauthn_credentials, private_notes).
//
// 여기 저장되는 자격 증명 값은 전부 "공개키"입니다. WebAuthn 표준상 개인키는 등록에 사용한
// 기기(브라우저의 보안 저장소, 보안키, 지문/얼굴 인식 모듈 등) 밖으로 절대 나가지 않고,
// 이 저장소에도, 서버 코드 어디에도 개인키가 존재한 적이 없습니다.
//
// 이 파일 전체에서 지키는 규칙: "어떤 함수든 accountId를 파라미터로 받은 경우, 그 accountId로만
// 필터링한 행만 돌려주거나 건드립니다." 라우트(routes/*.js)는 항상 req.session.accountId만
// 넘기므로, 결과적으로 로그인한 계정 자신의 데이터 밖으로는 절대 나갈 수 없습니다.
const { isoBase64URL, generateUserID } = require("@simplewebauthn/server/helpers");
const { supabaseAdmin } = require("./supabaseAdmin");

const ACCOUNTS_TABLE = "webauthn_accounts";
const CREDENTIALS_TABLE = "webauthn_credentials";
const NOTES_TABLE = "private_notes";

function mapAccountRow(row) {
  if (!row) return null;
  return { id: row.id, userHandle: row.user_handle, username: row.username, displayName: row.display_name };
}

// WebAuthn 등록에 쓸 userID(userHandle)를 새로 하나 만듭니다. 계정을 실제로 만들기
// 전(=회원가입 challenge 발급 시점)에 미리 필요해서 별도 함수로 뺐습니다.
async function generateAccountUserHandle() {
  const raw = await generateUserID();
  return isoBase64URL.fromBuffer(raw);
}

async function findAccountByUsername(username) {
  const { data, error } = await supabaseAdmin
    .from(ACCOUNTS_TABLE)
    .select("id,user_handle,username,display_name")
    .eq("username", username)
    .maybeSingle();
  if (error) throw error;
  return mapAccountRow(data);
}

async function findAccountById(id) {
  if (!id) return null;
  const { data, error } = await supabaseAdmin
    .from(ACCOUNTS_TABLE)
    .select("id,user_handle,username,display_name")
    .eq("id", id)
    .maybeSingle();
  if (error) throw error;
  return mapAccountRow(data);
}

// 새 계정 생성(= 패스키로 회원가입). username은 테이블에 unique 제약이 걸려 있어서,
// 동시에 같은 아이디로 가입을 시도하는 경쟁 상태가 나도 DB가 최종적으로 막아줍니다
// (이 경우 error.code === "23505").
async function createAccount({ userHandle, username, displayName }) {
  const { data, error } = await supabaseAdmin
    .from(ACCOUNTS_TABLE)
    .insert({ user_handle: userHandle, username, display_name: displayName })
    .select("id,user_handle,username,display_name")
    .single();
  if (error) throw error;
  return mapAccountRow(data);
}

// 목록 화면에는 공개키 원문까지 보낼 필요가 없어서 이름/날짜만 추려서 돌려줍니다.
// accountId로 필터링하므로, 로그인한 계정 본인의 패스키만 나옵니다.
async function listCredentials(accountId) {
  const { data, error } = await supabaseAdmin
    .from(CREDENTIALS_TABLE)
    .select("credential_id,label,created_at")
    .eq("account_id", accountId)
    .order("created_at", { ascending: true });
  if (error) throw error;
  return data.map((row) => ({ id: row.credential_id, label: row.label, createdAt: row.created_at }));
}

// 로그인(인증) 시 allowCredentials에 쓸 목록. 여기서만 예외적으로 계정과 무관하게 전체를
// 봅니다 — 로그인은 "이 패스키가 누구 것인지"를 아직 모르는 상태에서 시작하기 때문에,
// 사이트에 등록된 모든 패스키 중 브라우저가 갖고 있는 것을 고르게 해야 합니다. credential_id와
// transports만 담겨 있어 계정을 특정할 수 있는 정보(이름 등)는 없습니다.
async function listCredentialRefs() {
  const { data, error } = await supabaseAdmin.from(CREDENTIALS_TABLE).select("credential_id,transports");
  if (error) throw error;
  return data.map((row) => ({ id: row.credential_id, transports: row.transports || [] }));
}

// 등록(회원가입/기기 추가) 시 excludeCredentials에 쓸 목록 — "새 기기 추가" 모드에서
// 같은 계정에 이미 등록된 패스키를 중복 등록하지 않도록 해당 계정 것만 골라 봅니다.
async function listCredentialRefsForAccount(accountId) {
  const { data, error } = await supabaseAdmin
    .from(CREDENTIALS_TABLE)
    .select("credential_id,transports")
    .eq("account_id", accountId);
  if (error) throw error;
  return data.map((row) => ({ id: row.credential_id, transports: row.transports || [] }));
}

// 한 계정에 등록된 패스키 개수. "마지막 남은 패스키는 삭제 못 하게" 막을 때 씀
// (그거 하나까지 지우면 그 계정은 로그인할 방법이 영영 사라지므로).
async function countCredentialsForAccount(accountId) {
  const { count, error } = await supabaseAdmin
    .from(CREDENTIALS_TABLE)
    .select("credential_id", { count: "exact", head: true })
    .eq("account_id", accountId);
  if (error) throw error;
  return count || 0;
}

async function findCredentialById(id) {
  const { data, error } = await supabaseAdmin
    .from(CREDENTIALS_TABLE)
    .select("credential_id,account_id,public_key,counter,transports,label,device_type,backed_up,created_at")
    .eq("credential_id", id)
    .maybeSingle();
  if (error) throw error;
  if (!data) return null;
  return {
    id: data.credential_id,
    accountId: data.account_id,
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
    account_id: record.accountId,
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

// 패스키 삭제. credential_id뿐 아니라 account_id까지 조건에 함께 걸어서, 혹시라도 남의
// 패스키 id를 알아내 요청하더라도 자기 계정 것이 아니면 삭제 자체가 아예 안 먹히도록 합니다
// (라우트에서 사전에 소유자 확인을 해도, 저장소 레벨에서 한 번 더 막아두는 이중 방어).
async function deleteCredential(id, accountId) {
  const { error, count } = await supabaseAdmin
    .from(CREDENTIALS_TABLE)
    .delete({ count: "exact" })
    .eq("credential_id", id)
    .eq("account_id", accountId);
  if (error) throw error;

  const remainingCount = await countCredentialsForAccount(accountId);
  return { deleted: (count || 0) > 0, remainingCount };
}

function mapNoteRow(row) {
  if (!row) return null;
  return { id: row.id, content: row.content, createdAt: row.created_at, updatedAt: row.updated_at };
}

// 계정별 비공개 메모 목록. accountId로 필터링하므로, 로그인한 계정 본인의 메모만 나옵니다.
// 최신 메모가 위로 오도록 최근 수정순으로 정렬합니다.
async function listPrivateNotes(accountId) {
  const { data, error } = await supabaseAdmin
    .from(NOTES_TABLE)
    .select("id,content,created_at,updated_at")
    .eq("account_id", accountId)
    .order("updated_at", { ascending: false });
  if (error) throw error;
  return data.map(mapNoteRow);
}

async function createPrivateNote(accountId, content) {
  const { data, error } = await supabaseAdmin
    .from(NOTES_TABLE)
    .insert({ account_id: accountId, content })
    .select("id,content,created_at,updated_at")
    .single();
  if (error) throw error;
  return mapNoteRow(data);
}

// id뿐 아니라 account_id까지 조건에 함께 걸어서, 남의 메모 id를 알아내도 수정이
// 아예 먹히지 않도록 합니다(패스키 삭제와 같은 이중 방어 패턴).
async function updatePrivateNote(id, accountId, content) {
  const { data, error } = await supabaseAdmin
    .from(NOTES_TABLE)
    .update({ content, updated_at: new Date().toISOString() })
    .eq("id", id)
    .eq("account_id", accountId)
    .select("id,content,created_at,updated_at")
    .maybeSingle();
  if (error) throw error;
  return mapNoteRow(data);
}

async function deletePrivateNote(id, accountId) {
  const { error, count } = await supabaseAdmin
    .from(NOTES_TABLE)
    .delete({ count: "exact" })
    .eq("id", id)
    .eq("account_id", accountId);
  if (error) throw error;
  return { deleted: (count || 0) > 0 };
}

module.exports = {
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
  listPrivateNotes,
  createPrivateNote,
  updatePrivateNote,
  deletePrivateNote,
};
