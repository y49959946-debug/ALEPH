-- PDS 9단계 마이그레이션: 내 계정 삭제 기능
-- 클라이언트(anon key)는 auth.users를 직접 지울 권한이 없으므로, 로그인한 본인만
-- 자기 자신을 지울 수 있는 서버 함수를 만들어 그 함수만 호출하게 합니다.
-- auth.users를 on delete cascade로 참조하는 pds_plans/pds_todos/pds_tags/pds_settings 행도
-- 함께 삭제됩니다. Supabase SQL Editor에서 이 파일 내용을 한 번 실행하세요.

create or replace function public.delete_user()
returns void
language plpgsql
security definer
set search_path = public
as $$
begin
  delete from auth.users where id = auth.uid();
end;
$$;

revoke all on function public.delete_user() from public;
grant execute on function public.delete_user() to authenticated;
