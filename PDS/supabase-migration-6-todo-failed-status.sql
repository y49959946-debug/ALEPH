-- PDS 6단계 마이그레이션: 할 일에 "실패" 상태 추가 (완료/실패를 분리해서 표시하기 위함)
-- (원래 4단계로 만들어졌는데, 4단계 번호를 next_plan_note 마이그레이션이 이미 쓰고 있어서 6단계로 번호를 맞췄습니다.)
-- Supabase SQL Editor에서 이 파일 내용을 한 번 실행하세요. 여러 번 실행해도 안전합니다.

alter table public.pds_todos add column if not exists failed boolean not null default false;
