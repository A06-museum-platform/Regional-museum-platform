-- The October snapshot labels this project's own Supabase images remote.
-- Only classify URLs in the known project and museum-media bucket; other
-- third-party placeholders remain remote. Preserve URLs and object keys.
UPDATE public.media_asset SET storage = 'supabase'
WHERE storage = 'remote'
  AND left(url, char_length('https://jrgyhvfpgppoarxwqhmk.supabase.co/storage/v1/object/public/museum-media/'))
    = 'https://jrgyhvfpgppoarxwqhmk.supabase.co/storage/v1/object/public/museum-media/';
