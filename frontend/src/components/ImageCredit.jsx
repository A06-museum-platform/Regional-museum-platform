import { catalogPhotoCredit } from '../utils/catalogPhotoCredit';
import styles from './ImageCredit.module.css';

export default function ImageCredit({ src }) {
  const credit = catalogPhotoCredit(src);
  if (!credit) return null;
  return (
    <aside className={styles.credit} aria-label="Image source">
      <strong>Reference photo</strong>
      <p>{credit.caption} This illustrates the subject; it is not a photograph of this accessioned object.</p>
      <p>{credit.creator} · <a href={credit.sourceUrl} target="_blank" rel="noreferrer">Source</a> ·{' '}
        <a href={credit.licenseUrl} target="_blank" rel="noreferrer">{credit.license}</a>. {credit.changes}</p>
    </aside>
  );
}
