-- PDS 3단계 마이그레이션: 태그 글자색을 배경색과 별도로 지정할 수 있도록 컬럼 추가
-- Supabase SQL Editor에서 이 파일 내용을 한 번 실행하세요. 여러 번 실행해도 안전합니다.

alter table public.pds_tags add column if not exists text_color text;
