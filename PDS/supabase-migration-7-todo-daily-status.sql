-- PDS 7단계 마이그레이션: 여러 날에 걸친 계획(예: 일주일짜리)의 할 일을
-- 날짜별로 따로 완료/실패 표시할 수 있도록 날짜별 상태 컬럼 추가.
-- (기존 done/failed 컬럼은 그대로 두되, 앞으로는 daily_status를 기준으로 사용합니다.)
-- (원래 5단계로 만들어졌는데, 5단계 번호를 계획 여러 개 허용 마이그레이션이 이미 쓰고 있어서 7단계로 번호를 맞췄습니다.)
-- Supabase SQL Editor에서 이 파일 내용을 한 번 실행하세요. 여러 번 실행해도 안전합니다.

alter table public.pds_todos add column if not exists daily_status jsonb not null default '{}'::jsonb;
