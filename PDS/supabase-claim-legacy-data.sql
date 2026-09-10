-- 로그인 없이 만들어둔 기존 테스트 데이터(user_id가 비어있는 행)를
-- 방금 회원가입한 내 계정 소유로 옮기는 일회성 스크립트입니다.
-- supabase-migration-8-auth-ownership.sql을 먼저 실행하고, 회원가입을 한 번 마친 뒤에 실행하세요.
-- 마이그레이션 파일이 아니라서 번호를 붙이지 않았습니다 (스키마가 아니라 데이터를 고치는 일회성 SQL).

-- 1) 내 계정의 uuid 확인 (이메일을 실제 가입한 이메일로 바꿔서 실행)
--    또는 Supabase 대시보드 Authentication > Users 목록에서 UID를 그대로 복사해도 됩니다.
select id, email from auth.users where email = '가입한이메일@example.com';

-- 2) 위에서 나온 id 값을 아래 <YOUR_USER_ID> 자리에 모두 붙여넣고 실행
update public.pds_plans    set user_id = '<YOUR_USER_ID>' where user_id is null;
update public.pds_todos    set user_id = '<YOUR_USER_ID>' where user_id is null;
update public.pds_tags     set user_id = '<YOUR_USER_ID>' where user_id is null;
update public.pds_settings set user_id = '<YOUR_USER_ID>' where user_id is null;
