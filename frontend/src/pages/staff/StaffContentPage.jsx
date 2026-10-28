import { useState } from 'react';
import { Link } from 'react-router-dom';
import useAsync from '../../hooks/useAsync';
import useDebouncedValue from '../../hooks/useDebouncedValue';
import {
  listStaffCollectionItems, createCollectionItem, updateCollectionItem, deleteCollectionItem,
} from '../../api/collections';
import {
  listStaffExhibitions, createExhibition, updateExhibition, deleteExhibition,
} from '../../api/exhibitions';
import { GALLERIES, CATEGORIES, galleryLabel, categoryLabel } from '../../api/constants';
import Button from '../../components/Button';
import Pill from '../../components/Pill';
import Skeleton from '../../components/Skeleton';
import EmptyState from '../../components/EmptyState';
import ConfirmDialog from '../../components/ConfirmDialog';
import ExhibitionEditor from './ExhibitionEditor';
import CollectionItemEditor from './CollectionItemEditor';
import styles from './StaffContentPage.module.css';

/**
 * Exhibitions and collection objects in one screen, two tabs.
 *
 * They are separate tables and separate public pages, but curatorial staff
 * think of them as one job: "the content". Splitting them across two sidebar
 * items would mean bouncing back and forth to attach an object to a show.
 */
export default function StaffContentPage() {
  const [tab, setTab] = useState('exhibitions');

  const [q, setQ] = useState('');
  const [status, setStatus] = useState('');
  const [gallery, setGallery] = useState('');
  const [category, setCategory] = useState('');
  const debouncedQ = useDebouncedValue(q, 300);

  const [editing, setEditing] = useState(null);
  const [deleting, setDeleting] = useState(null);
  const [busy, setBusy] = useState(false);
  const [formError, setFormError] = useState(null);
  const [pageError, setPageError] = useState(null);

  const exhibitionsQuery = useAsync(
    () => listStaffExhibitions(tab === 'exhibitions' ? { q: debouncedQ, status, gallery } : {}),
    [tab, debouncedQ, status, gallery]
  );

  const itemsQuery = useAsync(
    () =>
      tab === 'items'
        ? listStaffCollectionItems({ q: debouncedQ, status, gallery, category })
        : Promise.resolve(null),
    [tab, debouncedQ, status, gallery, category]
  );

  const active = tab === 'exhibitions' ? exhibitionsQuery : itemsQuery;
  const allExhibitions = exhibitionsQuery.data?.items ?? [];

  function switchTab(next) {
    setTab(next);
    setQ(''); setStatus(''); setGallery(''); setCategory('');
    setPageError(null);
  }

  function refresh() {
    exhibitionsQuery.reload();
    if (tab === 'items') itemsQuery.reload();
  }

  async function handleSave(payload) {
    setBusy(true);
    setFormError(null);
    try {
      if (tab === 'exhibitions') {
        if (editing === 'new') await createExhibition(payload);
        else await updateExhibition(editing.id, payload);
      } else {
        if (editing === 'new') await createCollectionItem(payload);
        else await updateCollectionItem(editing.id, payload);
      }
      setEditing(null);
      refresh();
    } catch (err) {
      setFormError(err.message);
    } finally {
      setBusy(false);
    }
  }

  async function handleDelete() {
    setBusy(true);
    setPageError(null);
    try {
      if (tab === 'exhibitions') await deleteExhibition(deleting.id);
      else await deleteCollectionItem(deleting.id);
      setDeleting(null);
      refresh();
    } catch (err) {
      setDeleting(null);
      setPageError(err.message);
    } finally {
      setBusy(false);
    }
  }

  async function togglePublish(record) {
    setPageError(null);
    const changes = { status: record.status === 'published' ? 'draft' : 'published' };
    try {
      if (tab === 'exhibitions') await updateExhibition(record.id, changes);
      else await updateCollectionItem(record.id, changes);
      refresh();
    } catch (err) {
      setPageError(err.message);
    }
  }

  const StatusPill = ({ value }) =>
    value === 'published' ? <Pill tone="lime">Published</Pill> : <Pill tone="ochre">Draft</Pill>;

  return (
    <div>
      <div className={styles.head}>
        <div>
          <h1>Exhibitions and collections</h1>
          <p style={{ color: 'var(--c-muted)', marginBottom: 0 }}>
            An exhibition groups objects. An object can sit in one exhibition, or none.
          </p>
        </div>
        <Button onClick={() => { setFormError(null); setEditing('new'); }}>
          {tab === 'exhibitions' ? 'New exhibition' : 'New object'}
        </Button>
      </div>

      <div className={styles.tabs}>
        <button
          type="button"
          className={`${styles.tab} ${tab === 'exhibitions' ? styles.tabActive : ''}`}
          onClick={() => switchTab('exhibitions')}
        >
          Exhibitions
          {exhibitionsQuery.data && (
            <span className={styles.tabCount}>{exhibitionsQuery.data.total}</span>
          )}
        </button>
        <button
          type="button"
          className={`${styles.tab} ${tab === 'items' ? styles.tabActive : ''}`}
          onClick={() => switchTab('items')}
        >
          Collection objects
          {itemsQuery.data && <span className={styles.tabCount}>{itemsQuery.data.total}</span>}
        </button>
      </div>

      {pageError && <div className={styles.errorBox}>{pageError}</div>}

      <div className={styles.filters}>
        <div className={`field ${styles.searchField}`}>
          <label htmlFor="content-search">Search</label>
          <input id="content-search" className="control" type="search" value={q}
            onChange={(e) => setQ(e.target.value)}
            placeholder={tab === 'exhibitions' ? 'Title or summary' : 'Title or accession number'} />
        </div>
        <div className={`field ${styles.selectField}`}>
          <label htmlFor="content-status">Status</label>
          <select id="content-status" className="control" value={status}
            onChange={(e) => setStatus(e.target.value)}>
            <option value="">All statuses</option>
            <option value="published">Published</option>
            <option value="draft">Draft</option>
          </select>
        </div>
        <div className={`field ${styles.selectField}`}>
          <label htmlFor="content-gallery">Gallery</label>
          <select id="content-gallery" className="control" value={gallery}
            onChange={(e) => setGallery(e.target.value)}>
            <option value="">All galleries</option>
            {Object.entries(GALLERIES).map(([value, label]) => (
              <option key={value} value={value}>{label}</option>
            ))}
          </select>
        </div>
        {tab === 'items' && (
          <div className={`field ${styles.selectField}`}>
            <label htmlFor="content-category">Category</label>
            <select id="content-category" className="control" value={category}
              onChange={(e) => setCategory(e.target.value)}>
              <option value="">All categories</option>
              {Object.entries(CATEGORIES).map(([value, label]) => (
                <option key={value} value={value}>{label}</option>
              ))}
            </select>
          </div>
        )}
      </div>

      {active.loading && (
        <div className={styles.tableWrap} style={{ padding: 'var(--s-4)' }}>
          <div style={{ display: 'flex', flexDirection: 'column', gap: 'var(--s-3)' }}>
            {Array.from({ length: 5 }).map((_, i) => <Skeleton key={i} height={40} />)}
          </div>
        </div>
      )}

      {active.error && (
        <EmptyState title="We could not load that list" body={active.error.message}>
          <Button onClick={refresh}>Try again</Button>
        </EmptyState>
      )}

      {active.data?.items.length === 0 && (
        <EmptyState
          title="Nothing matches those filters"
          body="Clear the filters, or create the first record."
        >
          <Button variant="ghost"
            onClick={() => { setQ(''); setStatus(''); setGallery(''); setCategory(''); }}>
            Clear filters
          </Button>
          <Button onClick={() => setEditing('new')}>
            {tab === 'exhibitions' ? 'New exhibition' : 'New object'}
          </Button>
        </EmptyState>
      )}

      {tab === 'exhibitions' && exhibitionsQuery.data?.items.length > 0 && (
        <div className={styles.tableWrap}>
          <table className={styles.table}>
            <thead>
              <tr><th>Exhibition</th><th>Gallery</th><th>Runs</th><th>Objects</th><th>Status</th><th /></tr>
            </thead>
            <tbody>
              {exhibitionsQuery.data.items.map((exhibition) => (
                <tr key={exhibition.id}>
                  <td>
                    <div className={styles.title}>{exhibition.title}</div>
                    <div className={styles.meta}>Record ID: {exhibition.id}</div>
                    <div className={styles.meta}>{exhibition.summary}</div>
                  </td>
                  <td>{galleryLabel(exhibition.gallery)}</td>
                  <td>
                    {exhibition.start_date}
                    <div className={styles.meta}>
                      {exhibition.end_date ? `until ${exhibition.end_date}` : 'Permanent'}
                    </div>
                  </td>
                  <td>{exhibition.item_count}</td>
                  <td><StatusPill value={exhibition.status} /></td>
                  <td className={styles.actions}>
                    <Link to={`/staff/media?type=exhibition&id=${encodeURIComponent(exhibition.id)}`}>Manage images</Link>
                    <Button size="sm" variant="ghost" onClick={() => togglePublish(exhibition)}>
                      {exhibition.status === 'published' ? 'Unpublish' : 'Publish'}
                    </Button>
                    <Button size="sm" variant="ghost"
                      onClick={() => { setFormError(null); setEditing(exhibition); }}>Edit</Button>
                    <Button size="sm" variant="danger" onClick={() => setDeleting(exhibition)}>
                      Delete
                    </Button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {tab === 'items' && itemsQuery.data?.items.length > 0 && (
        <div className={styles.tableWrap}>
          <table className={styles.table}>
            <thead>
              <tr><th>Object</th><th>Category</th><th>Gallery</th><th>Part of</th><th>Status</th><th /></tr>
            </thead>
            <tbody>
              {itemsQuery.data.items.map((item) => (
                <tr key={item.id}>
                  <td>
                    <div className={styles.title}>{item.title}</div>
                    <div className={styles.meta}>
                      {item.accession_number} · {item.period_text}
                      {item.is_family_friendly && ' · ages 10–14'}
                    </div>
                  </td>
                  <td>{categoryLabel(item.category)}</td>
                  <td>{galleryLabel(item.gallery)}</td>
                  <td>
                    {item.exhibition
                      ? item.exhibition.title
                      : <span className={styles.meta}>Not in an exhibition</span>}
                  </td>
                  <td><StatusPill value={item.status} /></td>
                  <td className={styles.actions}>
                    <Button size="sm" variant="ghost" onClick={() => togglePublish(item)}>
                      {item.status === 'published' ? 'Unpublish' : 'Publish'}
                    </Button>
                    <Button size="sm" variant="ghost"
                      onClick={() => { setFormError(null); setEditing(item); }}>Edit</Button>
                    <Button size="sm" variant="danger" onClick={() => setDeleting(item)}>Delete</Button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {editing && tab === 'exhibitions' && (
        <ExhibitionEditor
          exhibition={editing === 'new' ? null : editing}
          busy={busy} error={formError}
          onSave={handleSave} onClose={() => setEditing(null)}
        />
      )}

      {editing && tab === 'items' && (
        <CollectionItemEditor
          item={editing === 'new' ? null : editing}
          exhibitions={allExhibitions}
          busy={busy} error={formError}
          onSave={handleSave} onClose={() => setEditing(null)}
        />
      )}

      {deleting && (
        <ConfirmDialog
          title={`Delete “${deleting.title}”?`}
          body={
            tab === 'exhibitions'
              ? 'The exhibition is removed from the public site. Exhibitions that still have objects attached cannot be deleted.'
              : 'The object and its page are removed from the public site. This cannot be undone.'
          }
          confirmLabel="Delete"
          cancelLabel="Keep it"
          busy={busy}
          onConfirm={handleDelete}
          onCancel={() => setDeleting(null)}
        />
      )}
    </div>
  );
}
