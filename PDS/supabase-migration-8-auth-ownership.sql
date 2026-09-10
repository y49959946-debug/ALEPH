-- PDS 8단계 마이그레이션: Supabase Auth(이메일/비밀번호) 기반 로그인 붙이기
-- 링크만 알면 누구나 보이던 구조를, 로그인한 "내" 계정 소유의 자료만 보이는 구조로 바꿉니다.
-- Supabase SQL Editor에서 이 파일 내용을 한 번 실행하세요. 여러 번 실행해도 안전합니다.
--
-- 실행 순서 안내:
--   1) 이 파일을 먼저 실행 (스키마 변경 + RLS 재설정)
--   2) Supabase 대시보드에서 회원가입을 한 번 진행
--   3) 옆의 supabase-claim-legacy-data.sql 파일을 참고해서, 로그인 없이 만들어둔 기존 테스트
--      데이터(user_id가 비어있는 행)를 방금 만든 내 계정 소유로 옮기기

-- 1) 소유자 컬럼 추가 (기존 행은 user_id가 비어있는 채로 남고, 2단계 SQL로 나중에 채웁니다)
alter table public.pds_plans add column if not exists user_id uuid references auth.users(id) on delete cascade;
alter table public.pds_plans alter column user_id set default auth.uid();

alter table public.pds_todos add column if not exists user_id uuid references auth.users(id) on delete cascade;
alter table public.pds_todos alter column user_id set default auth.uid();

alter table public.pds_tags add column if not exists user_id uuid references auth.users(id) on delete cascade;
alter table public.pds_tags alter column user_id set default auth.uid();

-- pds_settings: id='today' 고정 1행 구조 → 사용자당 1행 구조로.
-- (기존 id 컬럼은 그대로 두되 더 이상 앱에서 쓰지 않습니다. user_id에 unique 제약을 걸어
--  "사용자당 설정 행 최대 1개"를 DB가 보장하게 합니다.)
alter table public.pds_settings add column if not exists user_id uuid references auth.users(id) on delete cascade;
alter table public.pds_settings alter column user_id set default auth.uid();
create unique index if not exists pds_settings_user_id_key on public.pds_settings (user_id);

-- 2) 기존에 anon(로그인 없음)에게 전체 공개했던 정책을 모두 제거
drop policy if exists "pds_plans_public_select" on public.pds_plans;
drop policy if exists "pds_plans_public_insert" on public.pds_plans;
drop policy if exists "pds_plans_public_update" on public.pds_plans;
drop policy if exists "pds_plans_public_delete" on public.pds_plans;

drop policy if exists "pds_todos_public_select" on public.pds_todos;
drop policy if exists "pds_todos_public_insert" on public.pds_todos;
drop policy if exists "pds_todos_public_update" on public.pds_todos;
drop policy if exists "pds_todos_public_delete" on public.pds_todos;

drop policy if exists "pds_tags_public_select" on public.pds_tags;
drop policy if exists "pds_tags_public_insert" on public.pds_tags;
drop policy if exists "pds_tags_public_update" on public.pds_tags;
drop policy if exists "pds_tags_public_delete" on public.pds_tags;

drop policy if exists "pds_settings_public_select" on public.pds_settings;
drop policy if exists "pds_settings_public_insert" on public.pds_settings;
drop policy if exists "pds_settings_public_update" on public.pds_settings;
drop policy if exists "pds_settings_public_delete" on public.pds_settings;

drop policy if exists "pds_plan_revisions_public_select" on public.pds_plan_revisions;
drop policy if exists "pds_plan_revisions_public_insert" on public.pds_plan_revisions;

drop policy if exists "pds_execution_logs_public_select" on public.pds_execution_logs;
drop policy if exists "pds_execution_logs_public_insert" on public.pds_execution_logs;

-- 3) 로그인한 본인 소유 행만 select/insert/update/delete 할 수 있는 정책
--    (pds_plans / pds_todos / pds_tags / pds_settings: user_id 컬럼을 직접 가짐)
create policy "pds_plans_owner_select" on public.pds_plans for select using (auth.uid() = user_id);
create policy "pds_plans_owner_insert" on public.pds_plans for insert with check (auth.uid() = user_id);
create policy "pds_plans_owner_update" on public.pds_plans for update using (auth.uid() = user_id) with check (auth.uid() = user_id);
create policy "pds_plans_owner_delete" on public.pds_plans for delete using (auth.uid() = user_id);

create policy "pds_todos_owner_select" on public.pds_todos for select using (auth.uid() = user_id);
create policy "pds_todos_owner_insert" on public.pds_todos for insert with check (auth.uid() = user_id);
create policy "pds_todos_owner_update" on public.pds_todos for update using (auth.uid() = user_id) with check (auth.uid() = user_id);
create policy "pds_todos_owner_delete" on public.pds_todos for delete using (auth.uid() = user_id);

create policy "pds_tags_owner_select" on public.pds_tags for select using (auth.uid() = user_id);
create policy "pds_tags_owner_insert" on public.pds_tags for insert with check (auth.uid() = user_id);
create policy "pds_tags_owner_update" on public.pds_tags for update using (auth.uid() = user_id) with check (auth.uid() = user_id);
create policy "pds_tags_owner_delete" on public.pds_tags for delete using (auth.uid() = user_id);

create policy "pds_settings_owner_select" on public.pds_settings for select using (auth.uid() = user_id);
create policy "pds_settings_owner_insert" on public.pds_settings for insert with check (auth.uid() = user_id);
create policy "pds_settings_owner_update" on public.pds_settings for update using (auth.uid() = user_id) with check (auth.uid() = user_id);
create policy "pds_settings_owner_delete" on public.pds_settings for delete using (auth.uid() = user_id);

-- 4) pds_plan_revisions / pds_execution_logs는 user_id가 없으므로,
--    각각 plan_id → pds_plans.user_id, todo_id → pds_todos.user_id를 타고 올라가 주인을 확인합니다.
--    (예전처럼 select/insert만 허용하고 update/delete는 여전히 막아 이력을 못 지우게 합니다.)
create policy "pds_plan_revisions_owner_select" on public.pds_plan_revisions for select
  using (exists (
    select 1 from public.pds_plans p where p.id = pds_plan_revisions.plan_id and p.user_id = auth.uid()
  ));
create policy "pds_plan_revisions_owner_insert" on public.pds_plan_revisions for insert
  with check (exists (
    select 1 from public.pds_plans p where p.id = pds_plan_revisions.plan_id and p.user_id = auth.uid()
  ));

create policy "pds_execution_logs_owner_select" on public.pds_execution_logs for select
  using (exists (
    select 1 from public.pds_todos t where t.id = pds_execution_logs.todo_id and t.user_id = auth.uid()
  ));
create policy "pds_execution_logs_owner_insert" on public.pds_execution_logs for insert
  with check (exists (
    select 1 from public.pds_todos t where t.id = pds_execution_logs.todo_id and t.user_id = auth.uid()
  ));
