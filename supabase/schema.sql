-- Supabase 대시보드의 SQL Editor에서 한 번 실행하세요.
-- data/passkeys.json에 있던 { owner, credentials: [...] } 구조를 두 테이블로 옮긴 것입니다.

create table if not exists webauthn_owner (
  id smallint primary key,       -- 이 사이트는 소유자가 1명뿐이라 항상 1을 씁니다.
  owner_id text not null,        -- WebAuthn user.id (userHandle). 공개 식별자일 뿐 비밀값이 아닙니다.
  name text not null,
  display_name text not null
);

create table if not exists webauthn_credentials (
  credential_id text primary key,            -- 패스키의 공개 식별자
  public_key text not null,                  -- 공개키 (base64url, COSE 형식). 개인키는 절대 여기 없습니다.
  counter bigint not null default 0,         -- 재사용 공격 탐지용 사용 횟수
  transports jsonb not null default '[]'::jsonb,
  label text not null,                       -- 사람이 알아볼 수 있는 이름 (예: "내 노트북 - 크롬")
  device_type text,
  backed_up boolean,
  created_at timestamptz not null default now()
);

-- 이 앱은 서버(service role 키)에서만 이 두 테이블에 접근합니다.
-- RLS를 켜두면, 혹시 모를 anon/publishable 키를 통한 접근은 기본적으로 전부 막히고
-- (별도 정책을 만들지 않았으므로) service role 키만 계속 정상 동작합니다.
alter table webauthn_owner enable row level security;
alter table webauthn_credentials enable row level security;
