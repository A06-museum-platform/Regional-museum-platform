import { useEffect, useState } from 'react';
import { useSearchParams } from 'react-router-dom';
import useAsync from '../../hooks/useAsync';
import useDebouncedValue from '../../hooks/useDebouncedValue';
import { listEvents } from '../../api/events';
import { GALLERIES, galleryLabel } from '../../api/constants';
import { startOfToday, comingWeekend } from '../../utils/date';
import EventRow from '../../components/EventRow';
import EmptyState from '../../components/EmptyState';
import Skeleton from '../../components/Skeleton';
import Button from '../../components/Button';
import Pill from '../../components/Pill';
import styles from './EventsPage.module.css';

const PAGE_SIZE = 10;

const WHEN_OPTIONS = {
  upcoming: 'Upcoming',
  weekend: 'This weekend',
  all: 'Including past events',
};

const AUDIENCE_OPTIONS = {
  families: 'Families and ages 10–14',
  adults: 'Adults (16+)',
};

/**
 * Event listing and search. Same URL-as-state pattern as CollectionsPage —
 * when you build the exhibitions list, copy this rather than inventing a
 * third approach.
 */
export default function EventsPage() {
  const [searchParams, setSearchParams] = useSearchParams();

  const q = searchParams.get('q') || '';
  const gallery = searchParams.get('gallery') || '';
  const audience = searchParams.get('audience') || '';
  const when = searchParams.get('when') || 'upcoming';
  const page = Number(searchParams.get('page')) || 1;

  const [typed, setTyped] = useState(q);
  const debouncedTyped = useDebouncedValue(typed, 300);

  useEffect(() => {
    if (debouncedTyped === q) return;
    updateParams({ q: debouncedTyped, page: 1 });
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [debouncedTyped]);

  function updateParams(changes) {
    const next = new URLSearchParams(searchParams);
    Object.entries(changes).forEach(([key, value]) => {
      if (value === '' || value === false || value == null) next.delete(key);
      else next.set(key, String(value));
    });
    if (!('page' in changes)) next.set('page', '1');
    if (next.get('page') === '1') next.delete('page');
    setSearchParams(next);
  }

  function clearAll() {
    setTyped('');
    setSearchParams(new URLSearchParams());
  }

  // 'when' is a friendly preset over the contract's from/to range params.
  let range = {};
  if (when === 'upcoming') range = { from: startOfToday().toISOString() };
  else if (when === 'weekend') range = comingWeekend();

  const { data, loading, error } = useAsync(
    () => listEvents({ q, gallery, audience, ...range, page, page_size: PAGE_SIZE }),
    [q, gallery, audience, when, page]
  );

  const hasFilters = Boolean(q || gallery || audience || when !== 'upcoming');
  const totalPages = data ? Math.max(1, Math.ceil(data.total / PAGE_SIZE)) : 1;

  return (
    <div>
      <div className={styles.head}>
        <h1>Events and workshops</h1>
        <p>
          Hands-on sessions, curatorial talks and field trips across the
          museum&apos;s four galleries. Most sessions are free for members.
        </p>
      </div>

      <div className={styles.filters}>
        <div className={`field ${styles.searchField}`}>
          <label htmlFor="event-search">Search</label>
          <input
            id="event-search"
            className="control"
            type="search"
            value={typed}
            placeholder="Try telegraph, steam, weaving"
            onChange={(event) => setTyped(event.target.value)}
          />
        </div>

        <div className={`field ${styles.selectField}`}>
          <label htmlFor="event-when">When</label>
          <select
            id="event-when"
            className="control"
            value={when}
            onChange={(event) => updateParams({ when: event.target.value })}
          >
            {Object.entries(WHEN_OPTIONS).map(([value, label]) => (
              <option key={value} value={value}>{label}</option>
            ))}
          </select>
        </div>

        <div className={`field ${styles.selectField}`}>
          <label htmlFor="event-gallery">Gallery</label>
          <select
            id="event-gallery"
            className="control"
            value={gallery}
            onChange={(event) => updateParams({ gallery: event.target.value })}
          >
            <option value="">All galleries</option>
            {Object.entries(GALLERIES).map(([value, label]) => (
              <option key={value} value={value}>{label}</option>
            ))}
          </select>
        </div>

        <div className={`field ${styles.selectField}`}>
          <label htmlFor="event-audience">Suitable for</label>
          <select
            id="event-audience"
            className="control"
            value={audience}
            onChange={(event) => updateParams({ audience: event.target.value })}
          >
            <option value="">Everyone</option>
            {Object.entries(AUDIENCE_OPTIONS).map(([value, label]) => (
              <option key={value} value={value}>{label}</option>
            ))}
          </select>
        </div>
      </div>

      <div className={styles.summary}>
        {loading && <span>Searching…</span>}
        {data && <span>{data.total} {data.total === 1 ? 'session' : 'sessions'}</span>}

        {q && <Pill onRemove={() => { setTyped(''); updateParams({ q: '' }); }}>{q}</Pill>}
        {gallery && <Pill onRemove={() => updateParams({ gallery: '' })}>{galleryLabel(gallery)}</Pill>}
        {audience && (
          <Pill tone="lime" onRemove={() => updateParams({ audience: '' })}>
            {AUDIENCE_OPTIONS[audience]}
          </Pill>
        )}
        {when !== 'upcoming' && (
          <Pill onRemove={() => updateParams({ when: 'upcoming' })}>{WHEN_OPTIONS[when]}</Pill>
        )}

        {hasFilters && (
          <button type="button" className={styles.clear} onClick={clearAll}>
            Clear filters
          </button>
        )}
      </div>

      {loading && (
        <div className={styles.list}>
          {Array.from({ length: 4 }).map((_, index) => (
            <div key={index} className={styles.skeletonRow}>
              <div className={styles.skeletonCol}>
                <Skeleton height={18} width="70%" />
                <Skeleton height={12} width="90%" />
              </div>
              <div className={styles.skeletonCol}>
                <Skeleton height={16} width="35%" />
                <Skeleton height={20} width="75%" />
                <Skeleton height={12} />
                <Skeleton height={12} width="60%" />
              </div>
              <Skeleton height={34} width={110} />
            </div>
          ))}
        </div>
      )}

      {error && (
        <EmptyState title="We could not load the programme" body={error.message}>
          <Button onClick={() => window.location.reload()}>Try again</Button>
        </EmptyState>
      )}

      {data && data.items.length === 0 && (
        <EmptyState
          title={q ? `No sessions match “${q}”` : 'No sessions match those filters'}
          body={
            when === 'upcoming'
              ? 'Nothing is scheduled that matches. Try including past events, or widen the filters.'
              : 'Try a broader search term.'
          }
        >
          {when === 'upcoming' && (
            <Button size="sm" variant="ghost" onClick={() => updateParams({ when: 'all' })}>
              Include past events
            </Button>
          )}
          <Button size="sm" onClick={clearAll}>Show everything</Button>
        </EmptyState>
      )}

      {data && data.items.length > 0 && (
        <>
          <div className={styles.list}>
            {data.items.map((event) => (
              <EventRow key={event.id} event={event} />
            ))}
          </div>

          {totalPages > 1 && (
            <div className={styles.pagination}>
              <Button variant="ghost" size="sm" disabled={page <= 1}
                onClick={() => updateParams({ page: page - 1 })}>Previous</Button>
              <span className={styles.pageLabel}>Page {page} of {totalPages}</span>
              <Button variant="ghost" size="sm" disabled={page >= totalPages}
                onClick={() => updateParams({ page: page + 1 })}>Next</Button>
            </div>
          )}
        </>
      )}
    </div>
  );
}
