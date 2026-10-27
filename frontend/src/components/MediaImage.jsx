import { useEffect, useRef, useState } from 'react';
import { resolveMediaUrl } from '../api/media.js';
import { mediaFallbackUrl } from '../utils/mediaFallback.js';
import styles from './MediaImage.module.css';

const standby = {
  supabaseUrl: import.meta.env.VITE_SUPABASE_URL,
  bucket: import.meta.env.VITE_SUPABASE_BUCKET || 'museum-media',
  r2PublicBase: import.meta.env.VITE_R2_PUBLIC_BASE,
};

function ImageAttempt({ src, alt = '', hideOnError = false, ...props }) {
  const [attempt, setAttempt] = useState('primary');
  const imageRef = useRef(null);
  const primary = resolveMediaUrl(src);
  const fallback = mediaFallbackUrl(primary, standby);
  useEffect(() => {
    // Bound both attempts for mirrored images, including connections that hang
    // without producing an error. Leave unrelated/local image URLs alone.
    if (!primary || !fallback || attempt === 'unavailable') return;
    const image = imageRef.current;
    let timer;
    let observer;
    const start = () => {
      timer = window.setTimeout(() => {
        if (!image?.complete || !image.naturalWidth) {
          setAttempt(current => current === attempt
            ? (attempt === 'primary' ? 'fallback' : 'unavailable') : current);
        }
      }, 10000);
    };
    // Off-screen lazy images haven't started loading yet. Their timeout begins
    // when they enter the viewport, rather than while a user is reading above.
    if (image?.loading === 'lazy' && 'IntersectionObserver' in window) {
      observer = new IntersectionObserver(entries => {
        if (entries.some(entry => entry.isIntersecting)) {
          observer.disconnect();
          start();
        }
      });
      observer.observe(image);
    } else {
      start();
    }
    return () => {
      window.clearTimeout(timer);
      observer?.disconnect();
    };
  }, [attempt, primary, fallback]);
  if (!primary || attempt === 'unavailable') {
    // Cards keep their own designed placeholder behind the image.
    if (hideOnError) return null;
    return <span className={styles.placeholder} role="img" aria-label={alt || 'Image unavailable'}>Image unavailable</span>;
  }
  return (
    <img {...props} key={attempt} ref={imageRef} src={attempt === 'fallback' ? fallback : primary} alt={alt}
      data-media-fallback={attempt === 'fallback' ? 'true' : 'false'}
      onError={() => setAttempt(attempt === 'primary' && fallback ? 'fallback' : 'unavailable')} />
  );
}

export default function MediaImage({ src, ...props }) {
  // A changed source starts a new attempt; failure never loops between hosts.
  return <ImageAttempt key={src} src={src} {...props} />;
}
