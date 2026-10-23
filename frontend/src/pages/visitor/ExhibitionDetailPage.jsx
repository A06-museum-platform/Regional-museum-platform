import { Link, useNavigate, useParams } from 'react-router-dom';
import useAsync from '../../hooks/useAsync';
import { getExhibition } from '../../api/exhibitions';
import { listEvents } from '../../api/events';
import { galleryLabel } from '../../api/constants';
import { formatDate, startOfToday } from '../../utils/date';
import CollectionCard from '../../components/CollectionCard';
import MediaImage from '../../components/MediaImage';
import { GALLERY_GRADIENTS } from '../../utils/galleryGradients';
import EmptyState from '../../components/EmptyState';
import Skeleton from '../../components/Skeleton';
import Button from '../../components/Button';
import Pill from '../../components/Pill';
import styles from './ExhibitionDetailPage.module.css';

const fmtDate = (iso) =>
  new Date(`${iso}T00:00:00`).toLocaleDateString('en-AU', { day: 'numeric', month: 'long', year: 'numeric' });

function audience({ age_min, age_max }) {
  if (age_min != null && age_max != null) return `Ages ${age_min}–${age_max}`;
  if (age_min != null) return `Ages ${age_min}+`;
  return 'All ages';
}

/** One exhibition: what it is about, when and where, and the objects in it. */
export default function ExhibitionDetailPage() {
  const { slug } = useParams();
  const navigate = useNavigate();
  const { data: exhibition, loading, error } = useAsync(() => getExhibition(slug), [slug]);
  const events = useAsync(
    () => (exhibition
      ? listEvents({ gallery: exhibition.gallery, from: startOfToday().toISOString(), page_size: 3 })
      : Promise.resolve(null)),
    [exhibition?.gallery]
  );

  if (loading) {
    return (
      <div style={{ display: 'flex', flexDirection: 'column', gap: 'var(--s-3)' }}>
        <Skeleton height={260} />
        <Skeleton height={32} width="60%" />
        <Skeleton height={90} />
      </div>
    );
  }

  if (error) {
    const missing = error.status === 404;
    return (
      <EmptyState
        title={missing ? 'We could not find that exhibition' : 'We could not load that exhibition'}
        body={missing ? 'It may have closed, or the link may be out of date.' : error.message}
      >
        <Button onClick={() => navigate('/exhibitions')}>See current exhibitions</Button>
      </EmptyState>
    );
  }

  return (
    <article>
      <nav className={styles.crumbs} aria-label="Breadcrumb">
        <Link to="/exhibitions">Exhibitions</Link> / {exhibition.title}
      </nav>

      <div
        className={styles.hero}
        style={{ background: GALLERY_GRADIENTS[exhibition.gallery] || GALLERY_GRADIENTS.main_hall }}
      >
        {exhibition.hero_image_url ? (
          <MediaImage src={exhibition.hero_image_url} alt="" hideOnError className={styles.heroImage} />
        ) : (
          <span className={styles.heroLabel} aria-hidden="true">{galleryLabel(exhibition.gallery)}</span>
        )}
      </div>

      <div className={styles.layout}>
        <div>
          <div className={styles.pills}>
            <Pill>{galleryLabel(exhibition.gallery)}</Pill>
            <Pill tone="lime">{audience(exhibition)}</Pill>
            {exhibition.phase === 'upcoming' && <Pill tone="ochre">Opens {fmtDate(exhibition.start_date)}</Pill>}
          </div>
          <h1 className={styles.title}>{exhibition.title}</h1>
          {exhibition.summary && <p className={styles.summary}>{exhibition.summary}</p>}
          {exhibition.body && <p className={styles.body}>{exhibition.body}</p>}
        </div>

        <aside className={styles.facts} aria-label="Visiting this exhibition">
          <table>
            <tbody>
              <tr><th scope="row">Where</th><td>{galleryLabel(exhibition.gallery)}</td></tr>
              <tr>
                <th scope="row">When</th>
                <td>
                  {exhibition.end_date
                    ? `${fmtDate(exhibition.start_date)} – ${fmtDate(exhibition.end_date)}`
                    : `From ${fmtDate(exhibition.start_date)}, long-term display`}
                </td>
              </tr>
              <tr><th scope="row">Suitable for</th><td>{audience(exhibition)}</td></tr>
              <tr><th scope="row">Entry</th><td>Included with general admission</td></tr>
            </tbody>
          </table>
          <div className={styles.factActions}>
            <Link to="/book"><Button fullWidth>Book tickets</Button></Link>
            <Link to="/visit"><Button fullWidth variant="ghost">Plan your visit</Button></Link>
          </div>
        </aside>
      </div>

      <section className={styles.section} aria-labelledby="ex-objects">
        <h2 id="ex-objects" className={styles.heading}>
          In this exhibition {exhibition.items.length > 0 && <span className={styles.count}>{exhibition.items.length} objects</span>}
        </h2>
        {exhibition.items.length === 0 ? (
          <p className={styles.muted}>Objects for this exhibition are still being catalogued.</p>
        ) : (
          <div className={styles.grid}>
            {exhibition.items.map((item) => <CollectionCard key={item.id} item={item} />)}
          </div>
        )}
      </section>

      {events.data?.items.length > 0 && (
        <section className={styles.section} aria-labelledby="ex-events">
          <h2 id="ex-events" className={styles.heading}>Workshops in the {galleryLabel(exhibition.gallery)}</h2>
          <ul className={styles.events}>
            {events.data.items.map((event) => (
              <li key={event.id}>
                <Link to={`/events/${event.slug}`}>{event.title}</Link>
                <span className={styles.muted}> · {formatDate(event.starts_at)}</span>
              </li>
            ))}
          </ul>
        </section>
      )}
    </article>
  );
}
