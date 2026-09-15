// 서버 전용 Supabase 클라이언트입니다.
// service role 키는 RLS(Row Level Security)를 우회하므로, 절대 프론트엔드 코드나
// 커밋되는 파일에 넣지 말고 환경변수로만 주입하세요 (.env는 .gitignore에 포함되어 있습니다).
// (index.html이 예전에 불러오던 supabase-client.js는 별개의 publishable key를 쓰는
// 클라이언트용 코드였고 이 패스키 저장소와는 무관합니다 — 지금은 사용하지 않습니다.)
const { createClient } = require("@supabase/supabase-js");

const SUPABASE_URL = process.env.SUPABASE_URL;
const SUPABASE_SERVICE_ROLE_KEY = process.env.SUPABASE_SERVICE_ROLE_KEY;

if (!SUPABASE_URL || !SUPABASE_SERVICE_ROLE_KEY) {
  throw new Error(
    "SUPABASE_URL / SUPABASE_SERVICE_ROLE_KEY 환경변수가 필요합니다. .env.example을 참고해서 .env를 만들어주세요."
  );
}

const supabaseAdmin = createClient(SUPABASE_URL, SUPABASE_SERVICE_ROLE_KEY, {
  auth: { persistSession: false },
});

module.exports = { supabaseAdmin };
