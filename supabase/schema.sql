-- SoLiT account profiles for Supabase Auth.
-- Run once in Supabase Dashboard > SQL Editor.

create table if not exists public.profiles (
  id uuid primary key references auth.users(id) on delete cascade,
  display_name text not null default '',
  role text not null default 'student' check (role in ('teacher', 'student')),
  created_at timestamptz not null default now()
);

alter table public.profiles enable row level security;

drop policy if exists "Users can read their own profile" on public.profiles;
create policy "Users can read their own profile"
  on public.profiles for select
  to authenticated
  using ((select auth.uid()) = id);

drop policy if exists "Users can update their own display name" on public.profiles;
create policy "Users can update their own display name"
  on public.profiles for update
  to authenticated
  using ((select auth.uid()) = id)
  with check ((select auth.uid()) = id);

revoke all on public.profiles from anon, authenticated;
grant select on public.profiles to authenticated;
grant update (display_name) on public.profiles to authenticated;

create or replace function public.handle_new_user()
returns trigger
language plpgsql
security definer
set search_path = ''
as $$
begin
  insert into public.profiles (id, display_name, role)
  values (
    new.id,
    coalesce(nullif(trim(new.raw_user_meta_data ->> 'display_name'), ''), split_part(new.email, '@', 1)),
    case when new.raw_user_meta_data ->> 'role' = 'teacher' then 'teacher' else 'student' end
  );
  return new;
end;
$$;

drop trigger if exists on_auth_user_created on auth.users;
create trigger on_auth_user_created
  after insert on auth.users
  for each row execute procedure public.handle_new_user();

-- Private source files and metadata for lecture uploads and student questions.
create table if not exists public.lectures (
  id uuid primary key default gen_random_uuid(),
  teacher_id uuid not null references public.profiles(id) on delete cascade,
  title text not null check (char_length(trim(title)) between 1 and 160),
  storage_path text not null unique,
  original_filename text not null,
  mime_type text not null,
  size_bytes bigint not null check (size_bytes > 0),
  status text not null default 'uploaded' check (status in ('uploaded', 'processing', 'ready', 'failed')),
  created_at timestamptz not null default now()
);

-- Folder names define the smallest unit of teacher-to-student access.
alter table public.lectures add column if not exists folder_name text not null default '기본 폴더';

create table if not exists public.student_questions (
  id uuid primary key default gen_random_uuid(),
  student_id uuid not null references public.profiles(id) on delete cascade,
  lecture_id uuid references public.lectures(id) on delete set null,
  lecture_title_snapshot text not null default '',
  question_text text not null default '',
  image_path text,
  original_filename text,
  mime_type text,
  size_bytes bigint,
  status text not null default 'submitted' check (status in ('submitted', 'processing', 'answered', 'failed')),
  created_at timestamptz not null default now(),
  constraint student_question_has_content check (char_length(trim(question_text)) > 0 or image_path is not null)
);

alter table public.lectures enable row level security;
alter table public.student_questions enable row level security;

drop policy if exists "Teachers manage their own lectures" on public.lectures;
create policy "Teachers manage their own lectures"
  on public.lectures for all to authenticated
  using (teacher_id = (select auth.uid()) and exists (
    select 1 from public.profiles p where p.id = (select auth.uid()) and p.role = 'teacher'
  ))
  with check (teacher_id = (select auth.uid()) and exists (
    select 1 from public.profiles p where p.id = (select auth.uid()) and p.role = 'teacher'
  ));

drop policy if exists "Students manage their own questions" on public.student_questions;
create policy "Students manage their own questions"
  on public.student_questions for all to authenticated
  using (student_id = (select auth.uid()) and exists (
    select 1 from public.profiles p where p.id = (select auth.uid()) and p.role = 'student'
  ))
  with check (student_id = (select auth.uid()) and exists (
    select 1 from public.profiles p where p.id = (select auth.uid()) and p.role = 'student'
  ));

grant select, insert, update, delete on public.lectures to authenticated;
grant select, insert, update, delete on public.student_questions to authenticated;

-- Teacher-managed student roster. A pending row is attached when the student
-- signs in with the registered, email-confirmed address.
create table if not exists public.teacher_students (
  id uuid primary key default gen_random_uuid(),
  teacher_id uuid not null references public.profiles(id) on delete cascade,
  student_email text not null,
  student_id uuid references public.profiles(id) on delete cascade,
  folder_names text[] not null default '{}',
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  constraint teacher_students_email_lowercase check (student_email = lower(trim(student_email))),
  constraint teacher_students_has_folders check (cardinality(folder_names) > 0)
);

create unique index if not exists teacher_students_teacher_email_uidx
  on public.teacher_students (teacher_id, student_email);
create index if not exists teacher_students_student_id_idx
  on public.teacher_students (student_id);

alter table public.teacher_students enable row level security;
revoke all on public.teacher_students from anon, authenticated;
grant select on public.teacher_students to authenticated;

drop policy if exists "Teachers read their own student roster" on public.teacher_students;
create policy "Teachers read their own student roster"
  on public.teacher_students for select to authenticated
  using (teacher_id = (select auth.uid()) and exists (
    select 1 from public.profiles p where p.id = (select auth.uid()) and p.role = 'teacher'
  ));

drop policy if exists "Students read their own teacher enrollments" on public.teacher_students;
create policy "Students read their own teacher enrollments"
  on public.teacher_students for select to authenticated
  using (student_id = (select auth.uid()) and exists (
    select 1 from public.profiles p where p.id = (select auth.uid()) and p.role = 'student'
  ));

create or replace function public.register_student_by_email(p_student_email text, p_folder_names text[])
returns text
language plpgsql
security definer
set search_path = ''
as $$
declare
  v_teacher_id uuid := auth.uid();
  v_email text := lower(trim(coalesce(p_student_email, '')));
  v_folders text[];
  v_student_id uuid;
  v_existing_role text;
  v_confirmed_at timestamptz;
begin
  if v_teacher_id is null or not exists (
    select 1 from public.profiles p where p.id = v_teacher_id and p.role = 'teacher'
  ) then
    raise exception '강사 계정만 수강생을 등록할 수 있습니다.';
  end if;
  if v_email = '' or position('@' in v_email) < 2 then
    raise exception '학생 이메일을 확인해 주세요.';
  end if;

  select array_agg(distinct trim(folder_name)) into v_folders
  from unnest(coalesce(p_folder_names, array[]::text[])) as folders(folder_name)
  where trim(folder_name) <> '';
  if coalesce(cardinality(v_folders), 0) = 0 then
    raise exception '이용 권한을 줄 폴더를 하나 이상 선택해 주세요.';
  end if;
  if exists (
    select 1 from unnest(v_folders) as selected(folder_name)
    where not exists (
      select 1 from public.lectures l
      where l.teacher_id = v_teacher_id and l.folder_name = selected.folder_name
    )
  ) then
    raise exception '선택한 폴더 중 등록된 강의가 없는 폴더가 있습니다.';
  end if;

  select u.id, p.role, u.email_confirmed_at into v_student_id, v_existing_role, v_confirmed_at
  from auth.users u
  join public.profiles p on p.id = u.id
  where lower(u.email) = v_email
  limit 1;
  if v_student_id is not null and v_existing_role <> 'student' then
    raise exception '해당 이메일은 학생 계정으로 등록할 수 없습니다.';
  end if;
  if v_confirmed_at is null then v_student_id := null; end if;

  insert into public.teacher_students (teacher_id, student_email, student_id, folder_names, updated_at)
  values (v_teacher_id, v_email, v_student_id, v_folders, now())
  on conflict (teacher_id, student_email) do update
    set student_id = excluded.student_id,
        folder_names = excluded.folder_names,
        updated_at = now();

  return 'registered';
end;
$$;

revoke all on function public.register_student_by_email(text, text[]) from public, anon;
grant execute on function public.register_student_by_email(text, text[]) to authenticated;

create or replace function public.claim_pending_student_enrollments()
returns void
language plpgsql
security definer
set search_path = ''
as $$
declare
  v_student_id uuid := auth.uid();
  v_email text;
begin
  if v_student_id is null or not exists (
    select 1 from public.profiles p where p.id = v_student_id and p.role = 'student'
  ) then
    return;
  end if;
  select lower(u.email) into v_email
  from auth.users u
  where u.id = v_student_id and u.email_confirmed_at is not null;
  if v_email is null then return; end if;

  update public.teacher_students
  set student_id = v_student_id, updated_at = now()
  where student_id is null and student_email = v_email;
end;
$$;

revoke all on function public.claim_pending_student_enrollments() from public, anon;
grant execute on function public.claim_pending_student_enrollments() to authenticated;

drop policy if exists "Students manage their own questions" on public.student_questions;
create policy "Students manage their own questions"
  on public.student_questions for all to authenticated
  using (student_id = (select auth.uid()) and exists (
    select 1 from public.profiles p where p.id = (select auth.uid()) and p.role = 'student'
  ))
  with check (student_id = (select auth.uid()) and exists (
    select 1 from public.profiles p where p.id = (select auth.uid()) and p.role = 'student'
  ) and lecture_id is not null and exists (
    select 1
    from public.lectures l
    join public.teacher_students ts on ts.teacher_id = l.teacher_id
    where l.id = lecture_id and ts.student_id = (select auth.uid())
      and l.folder_name = any(ts.folder_names)
  ));

drop policy if exists "Enrolled students read assigned lecture folders" on public.lectures;
create policy "Enrolled students read assigned lecture folders"
  on public.lectures for select to authenticated
  using (
    exists (select 1 from public.profiles p where p.id = (select auth.uid()) and p.role = 'student')
    and exists (
      select 1 from public.teacher_students ts
      where ts.teacher_id = lectures.teacher_id
        and ts.student_id = (select auth.uid())
        and lectures.folder_name = any(ts.folder_names)
    )
  );

drop policy if exists "Enrolled students read assigned lecture videos" on storage.objects;
create policy "Enrolled students read assigned lecture videos"
  on storage.objects for select to authenticated
  using (
    bucket_id = 'lecture-videos'
    and exists (
      select 1
      from public.lectures l
      join public.teacher_students ts on ts.teacher_id = l.teacher_id
      where l.storage_path = storage.objects.name
        and ts.student_id = (select auth.uid())
        and l.folder_name = any(ts.folder_names)
    )
  );

insert into storage.buckets (id, name, public, file_size_limit, allowed_mime_types)
values
  ('lecture-videos', 'lecture-videos', false, 52428800, array['video/mp4', 'video/quicktime', 'video/webm']),
  ('question-images', 'question-images', false, 10485760, array['image/jpeg', 'image/png', 'image/webp', 'application/pdf'])
on conflict (id) do update set
  public = excluded.public,
  file_size_limit = excluded.file_size_limit,
  allowed_mime_types = excluded.allowed_mime_types;

drop policy if exists "Teachers upload their own lecture videos" on storage.objects;
create policy "Teachers upload their own lecture videos"
  on storage.objects for insert to authenticated
  with check (
    bucket_id = 'lecture-videos'
    and (storage.foldername(name))[1] = (select auth.uid())::text
    and exists (select 1 from public.profiles p where p.id = (select auth.uid()) and p.role = 'teacher')
  );

drop policy if exists "Teachers read their own lecture videos" on storage.objects;
create policy "Teachers read their own lecture videos"
  on storage.objects for select to authenticated
  using (
    bucket_id = 'lecture-videos'
    and (storage.foldername(name))[1] = (select auth.uid())::text
    and exists (select 1 from public.profiles p where p.id = (select auth.uid()) and p.role = 'teacher')
  );

drop policy if exists "Teachers delete their own lecture videos" on storage.objects;
create policy "Teachers delete their own lecture videos"
  on storage.objects for delete to authenticated
  using (
    bucket_id = 'lecture-videos'
    and (storage.foldername(name))[1] = (select auth.uid())::text
    and exists (select 1 from public.profiles p where p.id = (select auth.uid()) and p.role = 'teacher')
  );

drop policy if exists "Students upload their own question files" on storage.objects;
create policy "Students upload their own question files"
  on storage.objects for insert to authenticated
  with check (
    bucket_id = 'question-images'
    and (storage.foldername(name))[1] = (select auth.uid())::text
    and exists (select 1 from public.profiles p where p.id = (select auth.uid()) and p.role = 'student')
  );

drop policy if exists "Students read their own question files" on storage.objects;
create policy "Students read their own question files"
  on storage.objects for select to authenticated
  using (
    bucket_id = 'question-images'
    and (storage.foldername(name))[1] = (select auth.uid())::text
    and exists (select 1 from public.profiles p where p.id = (select auth.uid()) and p.role = 'student')
  );

drop policy if exists "Students delete their own question files" on storage.objects;
create policy "Students delete their own question files"
  on storage.objects for delete to authenticated
  using (
    bucket_id = 'question-images'
    and (storage.foldername(name))[1] = (select auth.uid())::text
    and exists (select 1 from public.profiles p where p.id = (select auth.uid()) and p.role = 'student')
  );
