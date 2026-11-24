# SoLiT 회원가입·로그인 설정

로그인 화면은 Supabase Auth를 사용합니다. 새 Supabase 프로젝트에 다음 설정을 한 번 적용하면 이메일·비밀번호 계정과 역할별 프로필이 동작합니다.

1. Supabase 프로젝트를 만들고 **Project URL**과 **Publishable key**를 확인합니다. `service_role` 또는 secret key는 브라우저 설정에 넣지 않습니다.
2. Supabase Dashboard의 **SQL Editor**에서 저장소의 `supabase/schema.sql`을 실행합니다.
3. `website/supabase-config.js`의 `url`, `publishableKey`를 실제 값으로 바꿉니다. Publishable key는 브라우저에 공개되는 키이며, 접근 제어는 SQL의 RLS 정책이 담당합니다.
4. Supabase Dashboard의 **Authentication → URL Configuration**에서 Site URL을 배포 도메인으로 지정하고, 로컬 개발 주소도 Redirect URLs에 추가합니다. 이메일 인증을 켜 둔 경우 가입 확인 이메일을 누른 뒤 로그인합니다.

회원가입 화면에서 강사 또는 학생 역할을 선택해 계정을 만듭니다. 계정 역할은 가입 시 프로필에 기록되며 클라이언트에서 수정할 수 없도록 제한했습니다. 이 단계의 강사·학생 역할 선택은 공개 가입입니다. 실제 강사 자료 업로드나 학생별 자료 접근을 열기 전에는 강사 계정 승인 절차와 각 자료 테이블의 RLS 정책을 추가해야 합니다.

Netlify는 정적 사이트이므로 설정 파일을 바꾸고 배포하면 바로 적용됩니다. Supabase 키가 비어 있거나 예시 값이면 페이지는 로그인 처리 대신 설정 안내를 표시합니다.
