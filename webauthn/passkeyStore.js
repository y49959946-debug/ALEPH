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

function listCredentialsForExclude() {
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

module.exports = {
  STORE_FILE,
  getOwner,
  listCredentials,
  listCredentialsForExclude,
  findCredentialById,
  addCredential,
};
