import { Link } from 'react-router-dom';
import Pill from '../Pill';
import MediaImage from '../MediaImage';
import { galleryLabel } from '../../api/constants';
import { GALLERY_GRADIENTS } from '../../utils/galleryGradients';
import styles from './ExhibitionCard.module.css';


const formatRange = (start, end) => {
  const fmt = (iso) => new Date(`${iso}T00:00:00`).toLocaleDateString('en-AU', {
    day: 'numeric', month: 'short', year: 'numeric',
  });
  return end ? `${fmt(start)} – ${fmt(end)}` : `From ${fmt(start)} · long-term display`;
};

export default function ExhibitionCard({ exhibition }) {
  return (
    <Link to={`/exhibitions/${exhibition.slug}`} className={styles.card}>
      <div
        className={styles.thumb}
        style={{ background: GALLERY_GRADIENTS[exhibition.gallery] || GALLERY_GRADIENTS.main_hall }}
      >
        {exhibition.hero_image_url && (
          <MediaImage src={exhibition.hero_image_url} alt="" hideOnError className={styles.image} />
        )}
      </div>
      <div className={styles.body}>
        <div className={styles.pills}>
          <Pill>{galleryLabel(exhibition.gallery)}</Pill>
          {exhibition.phase === 'upcoming' && <Pill tone="ochre">Coming soon</Pill>}
          {exhibition.age_min != null && exhibition.age_min <= 14 && <Pill tone="lime">Ages 10–14</Pill>}
        </div>
        <h3 className={styles.title}>{exhibition.title}</h3>
        <p className={styles.summary}>{exhibition.summary}</p>
        <div className={styles.meta}>
          {formatRange(exhibition.start_date, exhibition.end_date)}
          {exhibition.item_count > 0 && ` · ${exhibition.item_count} objects`}
        </div>
      </div>
    </Link>
  );
}
