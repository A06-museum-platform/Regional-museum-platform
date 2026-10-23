import { useSearchParams } from 'react-router-dom';
import useAsync from '../../hooks/useAsync';
import useDebouncedValue from '../../hooks/useDebouncedValue';
import { listExhibitions } from '../../api/exhibitions';
import { GALLERIES } from '../../api/constants';
import ExhibitionCard from '../../components/exhibition/ExhibitionCard';
import EmptyState from '../../components/EmptyState';
import Skeleton from '../../components/Skeleton';
import Button from '../../components/Button';
import styles from './ExhibitionsPage.module.css';

/**
 * What is on in each gallery now, and what opens next. An exhibition groups
 * objects; individual objects live under Collections.
 * Filters live in the URL so a filtered list can be shared or bookmarked.
 */
export default function ExhibitionsPage() {
  const [params, setParams] = useSearchParams();
  const q = params.get('q') || '';
  const gallery = params.get('gallery') || '';
  const debouncedQ = useDebouncedValue(q, 300);

  const { data, loading, error, reload } = useAsync(
    () => listExhibitions({ q: debouncedQ, gallery, page_size: 50 }),
    [debouncedQ, gallery]
  );

  const update = (changes) => {
    const next = new URLSearchParams(params);
    Object.entries(changes).forEach(([key, value]) => (value ? next.set(key, value) : next.delete(key)));
    setParams(next, { replace: true });
  };

  const current = data?.items.filter((x) => x.phase === 'current') ?? [];
  const upcoming = data?.items.filter((x) => x.phase === 'upcoming') ?? [];

  return (
    <div>
      <h1>Exhibitions</h1>
      <p className={styles.lead}>
        Four galleries, each with its own story. Entry to every exhibition is
        included in general admission.
      </p>

      <div className={styles.filters}>
        <div className={`field ${styles.search}`}>
          <label htmlFor="ex-q">Search</label>
          <input id="ex-q" className="control" type="search" value={q}
            placeholder="Telegraph, whaling, mining…" onChange={(e) => update({ q: e.target.value })} />
        </div>
        <div className={`field ${styles.select}`}>
          <label htmlFor="ex-gallery">Gallery</label>
          <select id="ex-gallery" className="control" value={gallery}
            onChange={(e) => update({ gallery: e.target.value })}>
            <option value="">All galleries</option>
            {Object.entries(GALLERIES).map(([key, label]) => (
              <option key={key} value={key}>{label}</option>
            ))}
          </select>
        </div>
      </div>

      {loading ? (
        <div className={styles.grid}>{[1, 2, 3].map((n) => <Skeleton key={n} height={300} />)}</div>
      ) : error ? (
        <EmptyState title="We could not load the exhibitions" body={error.message}>
          <Button variant="ghost" onClick={reload}>Try again</Button>
        </EmptyState>
      ) : data.items.length === 0 ? (
        <EmptyState
          title={q ? `No exhibitions match “${q}”` : 'No exhibitions in that gallery right now'}
          body="Try a broader search, or browse the whole collection instead."
        >
          <Button variant="ghost" onClick={() => update({ q: '', gallery: '' })}>Show all exhibitions</Button>
        </EmptyState>
      ) : (
        <>
          {current.length > 0 && (
            <section className={styles.section} aria-labelledby="ex-current">
              <h2 id="ex-current" className={styles.heading}>Now showing</h2>
              <div className={styles.grid}>
                {current.map((x) => <ExhibitionCard key={x.id} exhibition={x} />)}
              </div>
            </section>
          )}
          {upcoming.length > 0 && (
            <section className={styles.section} aria-labelledby="ex-upcoming">
              <h2 id="ex-upcoming" className={styles.heading}>Coming soon</h2>
              <div className={styles.grid}>
                {upcoming.map((x) => <ExhibitionCard key={x.id} exhibition={x} />)}
              </div>
            </section>
          )}
        </>
      )}
    </div>
  );
}
