import { useState } from 'react';
import { resolveMediaUrl } from '../api/media.js';
import { mediaFallbackUrl } from '../utils/mediaFallback.js';
import styles from './MediaImage.module.css';

const standby = {
  supabaseUrl: import.meta.env.VITE_SUPABASE_URL,
  bucket: import.meta.env.VITE_SUPABASE_BUCKET || 'museum-media',
  r2PublicBase: import.meta.env.VITE_R2_PUBLIC_BASE,
};

function ImageAttempt({ src, alt = '', ...props }) {
  const [attempt, setAttempt] = useState('primary');
  const primary = resolveMediaUrl(src);
  const fallback = mediaFallbackUrl(primary, standby);
  if (!primary || attempt === 'unavailable') {
    return <span className={styles.placeholder} role="img" aria-label={alt || 'Image unavailable'}>Image unavailable</span>;
  }
  return (
    <img {...props} src={attempt === 'fallback' ? fallback : primary} alt={alt}
      data-media-fallback={attempt === 'fallback' ? 'true' : 'false'}
      onError={() => setAttempt(attempt === 'primary' && fallback ? 'fallback' : 'unavailable')} />
  );
}

export default function MediaImage({ src, ...props }) {
  // A changed source starts a new attempt; failure never loops between hosts.
  return <ImageAttempt key={src} src={src} {...props} />;
}
