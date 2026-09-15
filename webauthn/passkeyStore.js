// 등록된 패스키 저장소. 지금 단계에서는 JSON 파일 하나로 충분합니다.
//
// 여기 저장되는 값은 전부 "공개키"입니다. WebAuthn 표준상 개인키는 등록에 사용한
// 기기(브라우저의 보안 저장소, 보안키, 지문/얼굴 인식 모듈 등) 밖으로 절대 나가지 않고,
// 이 파일에도, 서버 메모리 어디에도 개인키가 존재한 적이 없습니다.
const fs = require("fs");
const path = require("path");
const { isoBase64URL, generateUserID } = require("@simplewebauthn/server/helpers");

const DATA_DIR = path.join(__dirname, "..", "data");
const STORE_FILE = path.join(DATA_DIR, "passkeys.json");

function readStoreFile() {
  if (!fs.existsSync(STORE_FILE)) return null;
  return JSON.parse(fs.readFileSync(STORE_FILE, "utf8"));
}

function writeStoreFile(store) {
  fs.mkdirSync(DATA_DIR, { recursive: true });
  fs.writeFileSync(STORE_FILE, JSON.stringify(store, null, 2), "utf8");
}

// 이 사이트는 아직 다중 사용자 로그인이 없어서, "사이트 소유자" 1명의
// WebAuthn user handle을 최초 1회 생성해서 파일에 고정해두고 계속 재사용합니다.
async function getOwner() {
  let store = readStoreFile();
  if (store && store.owner) return store.owner;

  const ownerID = await generateUserID();
  const owner = {
    id: isoBase64URL.fromBuffer(ownerID), // WebAuthn user.id (userHandle), 공개 식별자일 뿐 비밀값 아님
    name: "owner",
    displayName: "사이트 관리자",
  };

  store = store || { owner, credentials: [] };
  store.owner = owner;
  writeStoreFile(store);
  return owner;
}

function listCredentials() {
  const store = readStoreFile();
  if (!store) return [];
  // 목록 화면에는 공개키 원문까지 보낼 필요가 없어서 이름/날짜만 추려서 돌려줍니다.
  return store.credentials.map(({ id, label, createdAt }) => ({ id, label, createdAt }));
}

// 등록 게이트(부트스트랩 허용 여부)를 판단할 때 씀: 패스키가 하나라도 있는지만 빠르게 확인.
function countCredentials() {
  const store = readStoreFile();
  return store ? store.credentials.length : 0;
}

// { id, transports } 형태만 필요한 두 군데(등록 시 excludeCredentials,
// 로그인 시 allowCredentials)에서 함께 씁니다.
function listCredentialRefs() {
  const store = readStoreFile();
  if (!store) return [];
  return store.credentials.map(({ id, transports }) => ({ id, transports }));
}

function findCredentialById(id) {
  const store = readStoreFile();
  if (!store) return null;
  return store.credentials.find((cred) => cred.id === id) || null;
}

function addCredential(record) {
  const store = readStoreFile() || { owner: null, credentials: [] };
  store.credentials.push(record);
  writeStoreFile(store);
  return record;
}

// 로그인(인증) 성공 시 인증기가 보고한 사용 횟수(counter)로 갱신합니다.
// 이 값이 뒤로 가거나 그대로면 복제된 인증기를 의심할 수 있어서(재사용 공격 탐지),
// @simplewebauthn/server 문서에서도 반드시 저장해두라고 안내합니다.
function updateCredentialCounter(id, counter) {
  const store = readStoreFile();
  if (!store) return null;
  const credential = store.credentials.find((cred) => cred.id === id);
  if (!credential) return null;
  credential.counter = counter;
  writeStoreFile(store);
  return credential;
}

// 패스키 삭제. 삭제 후 남은 개수를 같이 돌려줘서(라우트가 응답에 그대로 실어 보낼 수 있게)
// 호출하는 쪽에서 별도로 다시 세지 않아도 되게 합니다.
function deleteCredential(id) {
  const store = readStoreFile();
  if (!store) return { deleted: false, remainingCount: 0 };

  const beforeCount = store.credentials.length;
  store.credentials = store.credentials.filter((cred) => cred.id !== id);
  const deleted = store.credentials.length < beforeCount;

  if (deleted) writeStoreFile(store);
  return { deleted, remainingCount: store.credentials.length };
}

module.exports = {
  STORE_FILE,
  getOwner,
  listCredentials,
  listCredentialRefs,
  countCredentials,
  findCredentialById,
  addCredential,
  updateCredentialCounter,
  deleteCredential,
};
