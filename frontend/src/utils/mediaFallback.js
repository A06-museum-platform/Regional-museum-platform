// Public URL mapping only. API keys never belong in the frontend.
export function mediaFallbackUrl(url, { supabaseUrl, bucket = 'museum-media', r2PublicBase } = {}) {
  if (!url || !supabaseUrl || !r2PublicBase) return null;
  let primary;
  let standby;
  try {
    primary = new URL(supabaseUrl);
    standby = new URL(r2PublicBase);
  } catch {
    return null;
  }
  if (primary.protocol !== 'https:' || standby.protocol !== 'https:') return null;
  const prefix = `${primary.origin}/storage/v1/object/public/${encodeURIComponent(bucket)}/`;
  if (!url.startsWith(prefix) || url.length === prefix.length) return null;
  return `${r2PublicBase.replace(/\/+$/, '')}/${url.slice(prefix.length)}`;
}
