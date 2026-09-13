import { Link } from 'react-router-dom';
import Pill from './Pill';
import Button from './Button';
import { galleryLabel, formatPrice } from '../api/constants';
import { formatDate, formatTimeRange } from '../utils/date';
import styles from './EventRow.module.css';

function audienceLabel({ age_min, age_max }) {
  if (age_min && age_max) return `Ages ${age_min}–${age_max}`;
  if (age_min) return `Ages ${age_min}+`;
  return 'All ages';
}

export default function EventRow({ event }) {
  const suitsFamilies = (event.age_min ?? 0) <= 14 && (event.age_max ?? 99) >= 10;

  return (
    <article className={styles.row}>
      <div className={styles.when}>
        <div className={styles.whenDate}>{formatDate(event.starts_at).replace(/,.*/, '')}</div>
        <div>{formatDate(event.starts_at).replace(/^[^,]+,\s*/, '')}</div>
        <div>{formatTimeRange(event.starts_at, event.ends_at)}</div>
      </div>

      <div>
        <div className={styles.pills}>
          <Pill tone={suitsFamilies ? 'lime' : 'grey'}>{audienceLabel(event)}</Pill>
          <Pill>{galleryLabel(event.gallery)}</Pill>
          {event.is_sold_out ? (
            <Pill tone="danger">Fully booked</Pill>
          ) : (
            event.spots_remaining <= 5 && (
              <Pill tone="ochre">{event.spots_remaining} places left</Pill>
            )
          )}
        </div>

        <h3 className={styles.title}>
          <Link to={`/events/${event.slug}`}>{event.title}</Link>
        </h3>
        <p className={styles.blurb}>{event.description}</p>
      </div>

      <div className={styles.aside}>
        <div className={`${styles.price} ${event.price_cents === 0 ? styles.free : ''}`}>
          {event.price_cents === 0 ? 'Free' : formatPrice(event.price_cents)}
        </div>
        {event.price_cents > 0 && event.member_price_cents === 0 && (
          <div className={styles.memberNote}>Free for members</div>
        )}
        {event.price_cents > 0 && event.member_price_cents > 0 && (
          <div className={styles.memberNote}>
            {formatPrice(event.member_price_cents)} for members
          </div>
        )}
        <Link to={`/events/${event.slug}`}>
          <Button size="sm" variant={event.is_sold_out ? 'ghost' : 'primary'}>
            {event.is_sold_out ? 'View details' : 'Register'}
          </Button>
        </Link>
      </div>
    </article>
  );
}
