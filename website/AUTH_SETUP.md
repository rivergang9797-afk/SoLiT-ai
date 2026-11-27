# SoLiT 회원가입·로그인 설정

로그인과 강의별 이용 권한은 Supabase Auth와 RLS로 처리합니다. 새 프로젝트에는 아래 설정을 적용하고, 기존 프로젝트는 업데이트된 스키마를 다시 실행해야 합니다.

1. Supabase 프로젝트를 만들고 **Project URL**과 **Publishable key**를 확인합니다. `service_role` 또는 secret key는 브라우저 설정에 넣지 않습니다.
2. Supabase Dashboard의 **SQL Editor**에서 저장소의 `supabase/schema.sql`을 실행합니다.
3. `website/supabase-config.js`의 `url`, `publishableKey`를 실제 값으로 바꿉니다. Publishable key는 브라우저에 공개되는 키이며, 접근 제어는 SQL의 RLS 정책이 담당합니다.
4. Supabase Dashboard의 **Authentication → URL Configuration**에서 Site URL을 배포 도메인으로 지정하고, `https://solve-like-my-teacher.netlify.app/**`를 Redirect URLs에 추가합니다. 가입 확인 메일의 링크는 SoLiT 앱의 이메일 인증 완료 화면으로 돌아옵니다.

회원가입 화면에서 강사 또는 학생 역할을 선택해 계정을 만듭니다. 현재 역할 선택은 공개 가입이므로, 실제 서비스에서 강사 계정을 제한하려면 별도의 강사 승인 절차가 필요합니다.

## 강사별 수강생·폴더 권한

강사는 강의 업로드 시 폴더명을 지정하고, 강사 페이지의 **수강생 등록**에서 학생 이메일과 허용할 폴더를 선택합니다. 학생이 해당 이메일로 가입하고 이메일 인증을 마친 뒤 로그인하면 등록이 자동 연결됩니다. 가입 전 이메일을 먼저 등록한 경우에도 학생의 첫 로그인 시 권한이 연결됩니다. 학생 화면과 강의 질문 선택 목록에는 허용된 폴더의 강의만 표시됩니다.

수강생 등록은 초대 메일을 발송하지 않습니다. 현재 강사는 학생 이메일을 등록하고, 학생은 같은 주소로 직접 가입해야 합니다. 폴더 권한은 강의 단위가 아니라 폴더 단위이며, 폴더에 나중에 추가된 강의도 해당 권한에 포함됩니다. 기존 강의에는 `기본 폴더`가 지정됩니다.

기존 데이터베이스는 새 스키마를 적용하기 전에 Supabase Dashboard의 **SQL Editor**에서 업데이트된 `supabase/schema.sql` 전체를 다시 실행하세요. 기존 강의와 계정은 유지되며 `folder_name`, 수강생 등록 테이블, 접근 정책 및 RPC 함수가 추가됩니다. 프런트엔드 변경만 배포하고 이 SQL을 적용하지 않으면 수강생 등록 및 폴더별 접근이 동작하지 않습니다.

가입 확인 메일 발신자를 `SoLiT`로 표시하려면 Supabase 기본 메일 발송기 대신 **custom SMTP**를 설정해야 합니다. 인증 설정에서 SMTP 제공자의 host, port, username, password와 검증된 From 주소를 입력하고 Sender name을 `SoLiT`로 지정합니다. SMTP 비밀번호는 이 저장소나 웹사이트 설정 파일에 넣지 말고 Supabase 대시보드에만 입력합니다. 기본 발송기는 개발용이며 발신자 브랜딩과 수신 주소에 제한이 있습니다.

Netlify는 정적 사이트이므로 설정 파일을 바꾸고 배포하면 바로 적용됩니다. Supabase 키가 비어 있거나 예시 값이면 페이지는 로그인 처리 대신 설정 안내를 표시합니다.
