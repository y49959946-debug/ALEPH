-- PDS 5단계 마이그레이션: 계획을 여러 개 동시에 세울 수 있도록 "활성 계획은 1개만" 제약 제거
-- (기존에는 pds_plans.is_active가 true인 행이 한 번에 하나만 있을 수 있게 부분 유니크 인덱스로 막아뒀는데,
--  이제 여러 계획을 동시에 활성 상태로 두고 각자 할 일을 붙일 수 있게 이 제약을 없앱니다.)
-- Supabase SQL Editor에서 이 파일 내용을 한 번 실행하세요. 여러 번 실행해도 안전합니다.

drop index if exists public.pds_plans_only_one_active;
