-- Add active space support to users

alter table app_users
add column if not exists active_space_id uuid
references spaces(id)
on delete set null;


-- Backfill active_space_id from existing memberships

update app_users
set active_space_id = (
    select sm.space_id
    from space_members sm
    where sm.user_id = app_users.id
    order by sm.joined_at asc
    limit 1
)
where active_space_id is null;


-- Add invite codes to spaces

alter table spaces
add column if not exists invite_code text unique;
