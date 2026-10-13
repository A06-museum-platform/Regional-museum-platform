/**
 * Reusable staff upload control. Drop it into the collection / exhibition /
 * event management pages once those are built (Harbor's M4 stream):
 *
 *   <MediaUploader ownerType="collection-item" ownerId={item.id}
 *                  onUploaded={(media) => ...} />
 */
import { useEffect, useRef, useState } from 'react';
import { deleteMedia, listMedia, resolveMediaUrl, uploadMedia } from '../api/media.js';
import styles from './MediaUploader.module.css';
import MediaImage from './MediaImage.jsx';

export default function MediaUploader({ ownerType, ownerId, onUploaded }) {
  const inputRef = useRef(null);
  const [items, setItems] = useState(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState('');

  async function refresh() {
    try {
      setItems(await listMedia(ownerType, ownerId));
    } catch (err) {
      setError(err.message || 'Could not load media.');
    }
  }

  useEffect(() => {
    let active = true;
    listMedia(ownerType, ownerId).then((media) => {
      if (active) setItems(media);
    }).catch((err) => {
      if (active) { setItems([]); setError(err.message || 'Could not load media.'); }
    });
    return () => { active = false; };
  }, [ownerType, ownerId]);

  async function handleFiles(event) {
    const files = [...event.target.files];
    if (!files.length) return;
    setBusy(true);
    setError('');
    try {
      for (const [index, file] of files.entries()) {
        const result = await uploadMedia(ownerType, ownerId, file, {
          isPrimary: items.length === 0 && index === 0,
          sortOrder: items.length + index,
        });
        onUploaded?.(result.media);
      }
      await refresh();
    } catch (err) {
      setError(err.message || 'Upload failed.');
    } finally {
      setBusy(false);
      event.target.value = '';
    }
  }

  async function handleDelete(mediaId) {
    setBusy(true);
    try {
      await deleteMedia(mediaId);
      await refresh();
    } catch (err) {
      setError(err.message || 'Delete failed.');
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className={styles.uploader}>
      <div className={styles.row}>
        <button
          type="button"
          disabled={busy || items === null}
          onClick={() => inputRef.current?.click()}
        >
          {busy ? 'Uploading…' : 'Upload images'}
        </button>
        <input
          ref={inputRef}
          type="file"
          hidden
          multiple
          accept="image/jpeg,image/png,image/webp,video/mp4,video/webm"
          onChange={handleFiles}
        />
      </div>
      {error && <p className={styles.error}>{error}</p>}
      <div className={styles.grid}>
        {(items ?? []).map((item) => (
          <figure key={item.media_id} className={styles.thumb}>
            {item.media_type === 'video' ? (
              <video src={resolveMediaUrl(item.url)} muted playsInline />
            ) : (
              <MediaImage src={item.url} alt="" loading="lazy" />
            )}
            <figcaption>
              {item.is_primary && <span>Primary</span>}
              <button
                type="button"
                disabled={busy}
                onClick={() => handleDelete(item.media_id)}
              >
                Remove
              </button>
            </figcaption>
          </figure>
        ))}
      </div>
    </div>
  );
}
