-- Add image metadata used by image ingestion and RAG.

alter table public.items
add column if not exists image_description text;


-- Private storage bucket for saved images.

insert into storage.buckets (id, name, public)
values ('item-images', 'item-images', false)
on conflict (id) do nothing;


-- Semantic search now returns the fields required
-- for image retrieval and RAG.

drop function if exists public.match_items(
    extensions.vector,
    uuid,
    integer
);
