import useAsync from '../../hooks/useAsync';
import { searchCollections } from '../../api/collections';
import { galleryLabel, categoryLabel } from '../../api/constants';

/**
 * Temporary smoke test for the API layer. Replaced by the real home page next.
 */
export default function HomePage() {
  const { data, loading, error } = useAsync(() => searchCollections({ page_size: 4 }), []);

  return (
    <div>
      <h1>Regional Museum Visitor Experience Platform</h1>
      <p>
        Scaffold running. The list below comes through the api layer, so the
        mock switch, the loading state and the error path are all working.
      </p>

      {loading && <p style={{ color: 'var(--c-muted)' }}>Loading…</p>}

      {error && (
        <p style={{ color: 'var(--c-danger)' }}>
          {error.message} ({error.code})
        </p>
      )}

      {data && (
        <>
          <p style={{ color: 'var(--c-muted)', fontSize: 'var(--fs-sm)' }}>
            Showing {data.items.length} of {data.total} published items
          </p>
          <ul style={{ paddingLeft: 'var(--s-5)' }}>
            {data.items.map((item) => (
              <li key={item.id} style={{ marginBottom: 'var(--s-2)' }}>
                <strong>{item.title}</strong>
                <br />
                <span style={{ color: 'var(--c-muted)', fontSize: 'var(--fs-sm)' }}>
                  {item.accession_number} · {categoryLabel(item.category)} ·{' '}
                  {galleryLabel(item.gallery)} · {item.period_text}
                </span>
              </li>
            ))}
          </ul>
        </>
      )}
    </div>
  );
}
