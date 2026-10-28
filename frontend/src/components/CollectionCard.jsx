import { Link } from 'react-router-dom';
import Pill from './Pill';
import MediaImage from './MediaImage';
import { catalogPhotoCredit } from '../utils/catalogPhotoCredit';
import { galleryLabel, categoryLabel } from '../api/constants';
import styles from './CollectionCard.module.css';

/**
 * Shows the object's primary image once staff upload one; until then (and if
 * the image fails to load) a gradient derived from the category. The gradient is
 * derived from the category so the grid does not read as rows of identical
 * grey boxes during the client demonstration.
 */
const THUMBS = {
  mineral:    'linear-gradient(135deg, #3B5417, #4C6B1F)',
  instrument: 'linear-gradient(135deg, #8A6A1A, #C08A1E)',
  document:   'linear-gradient(135deg, #4A4636, #6E6A50)',
  photograph: 'linear-gradient(135deg, #2A3524, #47543C)',
  machinery:  'linear-gradient(135deg, #5A5140, #8A7C60)',
};

export default function CollectionCard({ item }) {
  return (
    <Link to={`/collections/${item.slug}`} className={styles.card}>
      <div
        className={styles.thumb}
        style={{ background: THUMBS[item.category] || THUMBS.document }}
      >
        {item.image_url && <MediaImage src={item.image_url} alt="" hideOnError className={styles.image} />}
      </div>
      <div className={styles.body}>
        <div className={styles.pills}>
          <Pill>{categoryLabel(item.category)}</Pill>
          {catalogPhotoCredit(item.image_url) && <Pill>Reference photo</Pill>}
          {item.is_family_friendly && <Pill tone="lime">Ages 10–14</Pill>}
        </div>
        <h3 className={styles.title}>{item.title}</h3>
        <div className={styles.meta}>
          {item.accession_number} · {galleryLabel(item.gallery)} · {item.period_text}
        </div>
      </div>
    </Link>
  );
}
