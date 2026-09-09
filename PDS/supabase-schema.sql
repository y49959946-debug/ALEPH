-- PlanDoSee (오늘의 기록) 전용 테이블
-- Supabase 프로젝트의 SQL Editor에서 이 파일 내용을 한 번 실행하세요.
-- (Table Editor에서 직접 만들어도 되지만, 컬럼 타입/제약조건을 정확히 맞추려면 이 스크립트를 쓰는 걸 추천합니다.)

create extension if not exists pgcrypto;

create table if not exists public.pds_tags (
  id uuid primary key default gen_random_uuid(),
  label text not null,
  color text not null,
  created_at timestamptz not null default now()
);

create table if not exists public.pds_plans (
  id uuid primary key default gen_random_uuid(),
  time text,
  title text,
  note text,
  tag_id uuid references public.pds_tags(id) on delete set null,
  done boolean not null default false,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create table if not exists public.pds_settings (
  id text primary key default 'today',
  mood text,
  reflection text,
  tomorrow_note text,
  total_time_ms bigint not null default 0,
  updated_at timestamptz not null default now()
);

-- 이 과제는 로그인이 없고 링크를 아는 사람은 누구나 접근합니다.
-- 그래서 RLS는 켠 채로, anon 역할에게 select/insert/update/delete를 공개로 허용합니다.
-- (RLS를 끄는 것보다, 정책으로 명시적으로 허용하는 쪽이 나중에 로그인을 붙일 때 안전합니다.)
alter table public.pds_tags enable row level security;
alter table public.pds_plans enable row level security;
alter table public.pds_settings enable row level security;

drop policy if exists "pds_tags_public_select" on public.pds_tags;
drop policy if exists "pds_tags_public_insert" on public.pds_tags;
drop policy if exists "pds_tags_public_update" on public.pds_tags;
drop policy if exists "pds_tags_public_delete" on public.pds_tags;
create policy "pds_tags_public_select" on public.pds_tags for select using (true);
create policy "pds_tags_public_insert" on public.pds_tags for insert with check (true);
create policy "pds_tags_public_update" on public.pds_tags for update using (true) with check (true);
create policy "pds_tags_public_delete" on public.pds_tags for delete using (true);

drop policy if exists "pds_plans_public_select" on public.pds_plans;
drop policy if exists "pds_plans_public_insert" on public.pds_plans;
drop policy if exists "pds_plans_public_update" on public.pds_plans;
drop policy if exists "pds_plans_public_delete" on public.pds_plans;
create policy "pds_plans_public_select" on public.pds_plans for select using (true);
create policy "pds_plans_public_insert" on public.pds_plans for insert with check (true);
create policy "pds_plans_public_update" on public.pds_plans for update using (true) with check (true);
create policy "pds_plans_public_delete" on public.pds_plans for delete using (true);

drop policy if exists "pds_settings_public_select" on public.pds_settings;
drop policy if exists "pds_settings_public_insert" on public.pds_settings;
drop policy if exists "pds_settings_public_update" on public.pds_settings;
drop policy if exists "pds_settings_public_delete" on public.pds_settings;
create policy "pds_settings_public_select" on public.pds_settings for select using (true);
create policy "pds_settings_public_insert" on public.pds_settings for insert with check (true);
create policy "pds_settings_public_update" on public.pds_settings for update using (true) with check (true);
create policy "pds_settings_public_delete" on public.pds_settings for delete using (true);
