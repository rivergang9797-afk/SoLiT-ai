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
