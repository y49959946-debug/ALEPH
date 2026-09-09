-- PDS 4단계 마이그레이션: 돌아보기(카드4)에서 "다음 계획으로 남길 한 가지"를 저장할 컬럼 추가
-- (3단계 번호는 태그 글자색 마이그레이션이 이미 쓰고 있어서 4단계로 번호를 맞췄습니다.)
-- Supabase SQL Editor에서 이 파일 내용을 한 번 실행하세요.

alter table public.pds_settings add column if not exists next_plan_note text;
