-- PDS 2단계 마이그레이션: 계획(Plan) / 할일(Todo) / 실행기록(Execution Log) 구조 분리
-- 1단계(supabase-schema.sql)를 이미 실행했다는 전제로 동작합니다.
-- Supabase SQL Editor에서 이 파일 내용을 한 번 실행하세요. 여러 번 실행해도 안전하게 만들어뒀습니다.

-- 1) 예전 pds_plans 테이블(사실은 "할 일" 목록이었음)을 pds_todos로 이름 변경
--    (이미 새 pds_plans가 있으면-즉 success_criteria 컬럼이 있으면-건드리지 않음: 재실행 안전장치)
do $$
begin
  if exists (
    select 1 from information_schema.tables where table_schema = 'public' and table_name = 'pds_plans'
  ) and not exists (
    select 1 from information_schema.columns where table_schema = 'public' and table_name = 'pds_plans' and column_name = 'success_criteria'
  ) then
    alter table public.pds_plans rename to pds_todos;
  end if;
end $$;

-- 2) pds_todos에 카드2가 요구하는 필드 추가
alter table public.pds_todos add column if not exists plan_id uuid;
alter table public.pds_todos add column if not exists deadline date;
alter table public.pds_todos add column if not exists priority text not null default 'medium';
alter table public.pds_todos add column if not exists estimated_minutes integer;

do $$
begin
  if not exists (select 1 from pg_constraint where conname = 'pds_todos_priority_check') then
    alter table public.pds_todos add constraint pds_todos_priority_check check (priority in ('high','medium','low'));
  end if;
end $$;

-- 3) 진짜 "계획" 테이블 생성
create table if not exists public.pds_plans (
  id uuid primary key default gen_random_uuid(),
  title text not null,
  period_start date,
  period_end date,
  priority text not null default 'medium' check (priority in ('high','medium','low')),
  success_criteria text,
  estimated_minutes integer,
  is_active boolean not null default true,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

-- 활성 계획은 한 번에 하나만 존재하도록
create unique index if not exists pds_plans_only_one_active on public.pds_plans (is_active) where is_active;

do $$
begin
  if not exists (select 1 from pg_constraint where conname = 'pds_todos_plan_id_fkey') then
    alter table public.pds_todos add constraint pds_todos_plan_id_fkey foreign key (plan_id) references public.pds_plans(id) on delete set null;
  end if;
end $$;

-- 4) 계획 수정 이력 테이블 + 트리거 (계획을 고쳐도 고치기 전 내용이 사라지지 않도록)
create table if not exists public.pds_plan_revisions (
  id uuid primary key default gen_random_uuid(),
  plan_id uuid not null references public.pds_plans(id) on delete cascade,
  title text,
  period_start date,
  period_end date,
  priority text,
  success_criteria text,
  estimated_minutes integer,
  snapshot_at timestamptz not null default now()
);

create or replace function public.pds_plans_snapshot() returns trigger as $$
begin
  insert into public.pds_plan_revisions (plan_id, title, period_start, period_end, priority, success_criteria, estimated_minutes, snapshot_at)
  values (old.id, old.title, old.period_start, old.period_end, old.priority, old.success_criteria, old.estimated_minutes, now());
  new.updated_at = now();
  return new;
end;
$$ language plpgsql;

drop trigger if exists trg_pds_plans_before_update on public.pds_plans;
create trigger trg_pds_plans_before_update
before update on public.pds_plans
for each row execute function public.pds_plans_snapshot();

-- 5) 실행 기록 테이블 (시작/종료 시각, 실제 걸린 시간, 막힌 이유)
create table if not exists public.pds_execution_logs (
  id uuid primary key default gen_random_uuid(),
  todo_id uuid not null references public.pds_todos(id) on delete cascade,
  started_at timestamptz,
  ended_at timestamptz not null default now(),
  actual_minutes integer,
  blocked_reason text,
  created_at timestamptz not null default now()
);

-- 6) RLS: 로그인이 없는 과제라 anon 역할에 공개 (이력 테이블은 select/insert만 허용해 지우거나 고치지 못하게 함)
alter table public.pds_plans enable row level security;
alter table public.pds_plan_revisions enable row level security;
alter table public.pds_todos enable row level security;
alter table public.pds_execution_logs enable row level security;

drop policy if exists "pds_plans_public_select" on public.pds_plans;
drop policy if exists "pds_plans_public_insert" on public.pds_plans;
drop policy if exists "pds_plans_public_update" on public.pds_plans;
drop policy if exists "pds_plans_public_delete" on public.pds_plans;
create policy "pds_plans_public_select" on public.pds_plans for select using (true);
create policy "pds_plans_public_insert" on public.pds_plans for insert with check (true);
create policy "pds_plans_public_update" on public.pds_plans for update using (true) with check (true);
create policy "pds_plans_public_delete" on public.pds_plans for delete using (true);

drop policy if exists "pds_plan_revisions_public_select" on public.pds_plan_revisions;
drop policy if exists "pds_plan_revisions_public_insert" on public.pds_plan_revisions;
create policy "pds_plan_revisions_public_select" on public.pds_plan_revisions for select using (true);
create policy "pds_plan_revisions_public_insert" on public.pds_plan_revisions for insert with check (true);

-- 예전 이름으로 pds_todos에 붙어있던 정책을 정리하고 새 이름으로 다시 만듦
drop policy if exists "pds_plans_public_select" on public.pds_todos;
drop policy if exists "pds_plans_public_insert" on public.pds_todos;
drop policy if exists "pds_plans_public_update" on public.pds_todos;
drop policy if exists "pds_plans_public_delete" on public.pds_todos;
drop policy if exists "pds_todos_public_select" on public.pds_todos;
drop policy if exists "pds_todos_public_insert" on public.pds_todos;
drop policy if exists "pds_todos_public_update" on public.pds_todos;
drop policy if exists "pds_todos_public_delete" on public.pds_todos;
create policy "pds_todos_public_select" on public.pds_todos for select using (true);
create policy "pds_todos_public_insert" on public.pds_todos for insert with check (true);
create policy "pds_todos_public_update" on public.pds_todos for update using (true) with check (true);
create policy "pds_todos_public_delete" on public.pds_todos for delete using (true);

drop policy if exists "pds_execution_logs_public_select" on public.pds_execution_logs;
drop policy if exists "pds_execution_logs_public_insert" on public.pds_execution_logs;
create policy "pds_execution_logs_public_select" on public.pds_execution_logs for select using (true);
create policy "pds_execution_logs_public_insert" on public.pds_execution_logs for insert with check (true);
