import { useSearchParams } from 'react-router-dom';
import { useEffect, useState } from 'react';
import useAsync from '../../hooks/useAsync';
import useDebouncedValue from '../../hooks/useDebouncedValue';
import { searchCollections } from '../../api/collections';
import { GALLERIES, CATEGORIES, galleryLabel, categoryLabel } from '../../api/constants';
import CollectionCard from '../../components/CollectionCard';
import EmptyState from '../../components/EmptyState';
import Skeleton from '../../components/Skeleton';
import Button from '../../components/Button';
import Pill from '../../components/Pill';
import styles from './CollectionsPage.module.css';

const PAGE_SIZE = 12;
const SUGGESTED = ['copper', 'telegraph', 'whaling', 'narrow gauge'];

/**
 * Collection search — client requirement 3(ii).
 *
 * Search and filter state lives in the URL, not in component state. That means
 * a result page can be shared, the browser back button works, and a
 * usability-test participant who gets lost can be returned to exactly what
 * they were looking at. It costs nothing now and is painful to retrofit.
 */
export default function CollectionsPage() {
  const [searchParams, setSearchParams] = useSearchParams();

  const q = searchParams.get('q') || '';
  const gallery = searchParams.get('gallery') || '';
  const category = searchParams.get('category') || '';
  const familyFriendly = searchParams.get('family_friendly') === 'true';
  const page = Number(searchParams.get('page')) || 1;

  // The input is uncontrolled by the URL while typing, then debounced into it.
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
      if (value === '' || value === false || value === null || value === undefined) {
        next.delete(key);
      } else {
        next.set(key, String(value));
      }
    });
    if (!('page' in changes)) next.set('page', '1');
    if (next.get('page') === '1') next.delete('page');
    setSearchParams(next);
  }

  function clearAll() {
    setTyped('');
    setSearchParams(new URLSearchParams());
  }

  const { data, loading, error } = useAsync(
    () =>
      searchCollections({
        q,
        gallery,
        category,
        family_friendly: familyFriendly || undefined,
        page,
        page_size: PAGE_SIZE,
      }),
    [q, gallery, category, familyFriendly, page]
  );

  const hasFilters = Boolean(q || gallery || category || familyFriendly);
  const totalPages = data ? Math.max(1, Math.ceil(data.total / PAGE_SIZE)) : 1;

  return (
    <div>
      <div className={styles.head}>
        <h1>Collections</h1>
        <p>
          Search the objects held across the museum&apos;s four galleries. Every
          record is catalogued by the curatorial team.
        </p>
      </div>

      <div className={styles.filters}>
        <div className={`field ${styles.searchField}`}>
          <label htmlFor="collection-search">Search</label>
          <input
            id="collection-search"
            className="control"
            type="search"
            value={typed}
            placeholder="Try copper, telegraph, whaling"
            onChange={(event) => setTyped(event.target.value)}
          />
        </div>

        <div className={`field ${styles.selectField}`}>
          <label htmlFor="filter-gallery">Gallery</label>
          <select
            id="filter-gallery"
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
          <label htmlFor="filter-category">Category</label>
          <select
            id="filter-category"
            className="control"
            value={category}
            onChange={(event) => updateParams({ category: event.target.value })}
          >
            <option value="">All categories</option>
            {Object.entries(CATEGORIES).map(([value, label]) => (
              <option key={value} value={value}>{label}</option>
            ))}
          </select>
        </div>

        <label className={`field ${styles.checkboxField}`}>
          <input
            type="checkbox"
            checked={familyFriendly}
            onChange={(event) => updateParams({ family_friendly: event.target.checked })}
          />
          Good for ages 10–14
        </label>
      </div>

      <div className={styles.summary}>
        {loading && <span>Searching…</span>}
        {data && <span>{data.total} {data.total === 1 ? 'item' : 'items'}</span>}

        {q && <Pill onRemove={() => { setTyped(''); updateParams({ q: '' }); }}>{q}</Pill>}
        {gallery && (
          <Pill onRemove={() => updateParams({ gallery: '' })}>{galleryLabel(gallery)}</Pill>
        )}
        {category && (
          <Pill onRemove={() => updateParams({ category: '' })}>{categoryLabel(category)}</Pill>
        )}
        {familyFriendly && (
          <Pill tone="lime" onRemove={() => updateParams({ family_friendly: false })}>
            Ages 10–14
          </Pill>
        )}

        {hasFilters && (
          <button type="button" className={styles.clear} onClick={clearAll}>
            Clear filters
          </button>
        )}
      </div>

      {loading && (
        <div className={styles.grid}>
          {Array.from({ length: 6 }).map((_, index) => (
            <div key={index} className={styles.skeletonCard}>
              <Skeleton height={140} radius={0} />
              <div className={styles.skeletonBody}>
                <Skeleton height={16} width="45%" />
                <Skeleton height={18} width="85%" />
                <Skeleton height={12} width="70%" />
              </div>
            </div>
          ))}
        </div>
      )}

      {error && (
        <EmptyState
          title="We could not load the collection"
          body={error.message}
        >
          <Button onClick={() => window.location.reload()}>Try again</Button>
        </EmptyState>
      )}

      {data && data.items.length === 0 && (
        <EmptyState
          title={q ? `No collection items match “${q}”` : 'No items match those filters'}
          body="Check the spelling, or try a broader term."
        >
          {SUGGESTED.map((term) => (
            <Button
              key={term}
              variant="ghost"
              size="sm"
              onClick={() => { setTyped(term); updateParams({ q: term }); }}
            >
              {term}
            </Button>
          ))}
          <Button size="sm" onClick={clearAll}>Browse everything</Button>
        </EmptyState>
      )}

      {data && data.items.length > 0 && (
        <>
          <div className={styles.grid}>
            {data.items.map((item) => (
              <CollectionCard key={item.id} item={item} />
            ))}
          </div>

          {totalPages > 1 && (
            <div className={styles.pagination}>
              <Button
                variant="ghost"
                size="sm"
                disabled={page <= 1}
                onClick={() => updateParams({ page: page - 1 })}
              >
                Previous
              </Button>
              <span className={styles.pageLabel}>Page {page} of {totalPages}</span>
              <Button
                variant="ghost"
                size="sm"
                disabled={page >= totalPages}
                onClick={() => updateParams({ page: page + 1 })}
              >
                Next
              </Button>
            </div>
          )}
        </>
      )}
    </div>
  );
}
