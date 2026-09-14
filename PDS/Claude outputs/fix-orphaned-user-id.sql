-- 예전 계정(4b6cc72c-...)에 붙어있던 계획/할 일/태그/설정을
-- 지금 로그인 중인 계정(71bae10f-...)으로 옮겨서 다시 보이게 합니다.
-- Supabase SQL Editor에서 한 번만 실행하세요.

update public.pds_plans set user_id = '71bae10f-1c80-48d0-9220-1e851d684753' where user_id = '4b6cc72c-a9a7-4b78-b3c8-709bf595ba54';
update public.pds_todos set user_id = '71bae10f-1c80-48d0-9220-1e851d684753' where user_id = '4b6cc72c-a9a7-4b78-b3c8-709bf595ba54';
update public.pds_tags  set user_id = '71bae10f-1c80-48d0-9220-1e851d684753' where user_id = '4b6cc72c-a9a7-4b78-b3c8-709bf595ba54';

-- pds_settings는 user_id가 유니크라서, 새 계정 설정 행이 이미 있으면 옛 행은 지우고
-- 없으면 옛 행을 새 계정 앞으로 옮깁니다 (둘 다 있는 경우의 "중복 키" 에러 방지).
delete from public.pds_settings
where user_id = '4b6cc72c-a9a7-4b78-b3c8-709bf595ba54'
  and exists (select 1 from public.pds_settings where user_id = '71bae10f-1c80-48d0-9220-1e851d684753');

update public.pds_settings set user_id = '71bae10f-1c80-48d0-9220-1e851d684753' where user_id = '4b6cc72c-a9a7-4b78-b3c8-709bf595ba54';

-- 확인: 이제 pds_plans에 남은 user_id가 71bae10f... 하나뿐이어야 합니다.
select distinct user_id from public.pds_plans;
