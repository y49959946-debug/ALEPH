-- Supabase 대시보드의 SQL Editor에서 한 번 실행하세요.
--
-- [중요] 이 스크립트는 기존 테이블을 전부 지우고 새로 만듭니다(drop → create).
-- "계정은 1명뿐"이던 예전 구조(webauthn_owner)를 "여러 계정을 지원"하는 구조로
-- 바꾸는 것이라, 기존에 등록해둔 패스키 데이터는 이 SQL을 실행하면 함께 사라집니다.
-- 실행 후에는 사이트에서 패스키를 다시 등록(=계정 새로 만들기)해야 합니다.

-- gen_random_uuid() 사용을 위해 필요합니다. (Supabase 프로젝트는 기본 활성화되어 있는 경우가 많음)
create extension if not exists pgcrypto;

drop table if exists private_notes;
drop table if exists webauthn_credentials;
drop table if exists webauthn_owner;
drop table if exists webauthn_accounts;

-- 계정 테이블. 예전에는 "이 사이트 소유자 1명"만 담는 고정 행 하나였지만,
-- 이제는 회원가입(패스키로 계정 만들기)할 때마다 행이 하나씩 늘어납니다.
create table webauthn_accounts (
  id uuid primary key default gen_random_uuid(),
  user_handle text not null unique,   -- WebAuthn user.id (userHandle). 공개 식별자일 뿐 비밀값 아님.
  username text not null unique,      -- 계정을 만들 때 정한 아이디. 로그인 자체엔 안 쓰이고(패스키가 대신함) 계정 구분/표시용.
  display_name text not null,
  created_at timestamptz not null default now()
);

-- 패스키(자격 증명) 테이블. account_id로 반드시 계정 하나에 소속됩니다.
-- 한 계정이 패스키를 여러 개(=여러 기기) 가질 수 있어야 기기를 잃어버렸을 때도
-- 다른 기기의 패스키로 로그인해서 복구할 수 있습니다.
create table webauthn_credentials (
  credential_id text primary key,            -- 패스키의 공개 식별자
  account_id uuid not null references webauthn_accounts(id) on delete cascade,
  public_key text not null,                  -- 공개키 (base64url, COSE 형식). 개인키는 절대 여기 없습니다.
  counter bigint not null default 0,         -- 재사용 공격 탐지용 사용 횟수
  transports jsonb not null default '[]'::jsonb,
  label text not null,                       -- 사람이 알아볼 수 있는 이름 (예: "내 노트북 - 크롬")
  device_type text,
  backed_up boolean,
  created_at timestamptz not null default now()
);
create index webauthn_credentials_account_id_idx on webauthn_credentials(account_id);

-- 계정별 비공개 메모. "다른 계정으로 로그인하면 내 메모가 절대 안 보인다"를 실제로
-- 증명하는 데이터입니다. 계정 하나가 메모를 여러 개(추가/수정/삭제) 가질 수 있도록
-- id를 따로 둔 일반 테이블입니다(= account_id는 그냥 외래키일 뿐 기본키가 아님).
create table private_notes (
  id uuid primary key default gen_random_uuid(),
  account_id uuid not null references webauthn_accounts(id) on delete cascade,
  content text not null,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);
create index private_notes_account_id_idx on private_notes(account_id);

-- 이 앱은 서버(service role 키)에서만 이 테이블들에 접근합니다.
-- RLS를 켜두면, 혹시 모를 anon/publishable 키를 통한 접근은 기본적으로 전부 막히고
-- (별도 정책을 만들지 않았으므로) service role 키만 계속 정상 동작합니다.
alter table webauthn_accounts enable row level security;
alter table webauthn_credentials enable row level security;
alter table private_notes enable row level security;
