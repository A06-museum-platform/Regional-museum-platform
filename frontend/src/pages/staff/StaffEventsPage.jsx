import { useState } from 'react';
import useAsync from '../../hooks/useAsync';
import useDebouncedValue from '../../hooks/useDebouncedValue';
import {
  listStaffEvents, createEvent, updateEvent, deleteEvent,
} from '../../api/events';
import { GALLERIES, galleryLabel, formatPrice } from '../../api/constants';
import { formatDate, formatTimeRange } from '../../utils/date';
import Button from '../../components/Button';
import Pill from '../../components/Pill';
import Skeleton from '../../components/Skeleton';
import EmptyState from '../../components/EmptyState';
import ConfirmDialog from '../../components/ConfirmDialog';
import EventEditor from './EventEditor';
import styles from './StaffEventsPage.module.css';

/**
 * Staff event management — client requirement 4(a): staff create and edit
 * event pages.
 *
 * Unlike the public listing this shows drafts, and it is NOT driven by the
 * URL. Staff work through a task in one sitting; a shareable filter state
 * buys nothing here and would put internal filters in browser history.
 */
export default function StaffEventsPage() {
  const [q, setQ] = useState('');
  const [status, setStatus] = useState('');
  const [gallery, setGallery] = useState('');
  const debouncedQ = useDebouncedValue(q, 300);

  const [editing, setEditing] = useState(null); // event object, or 'new'
  const [deleting, setDeleting] = useState(null);
  const [busy, setBusy] = useState(false);
  const [formError, setFormError] = useState(null);
  const [pageError, setPageError] = useState(null);

  const { data, loading, error, reload } = useAsync(
    () => listStaffEvents({ q: debouncedQ, status, gallery }),
    [debouncedQ, status, gallery]
  );

  async function handleSave(payload) {
    setBusy(true);
    setFormError(null);
    try {
      if (editing === 'new') await createEvent(payload);
      else await updateEvent(editing.id, payload);
      setEditing(null);
      reload();
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
      await deleteEvent(deleting.id);
      setDeleting(null);
      reload();
    } catch (err) {
      setDeleting(null);
      setPageError(err.message);
    } finally {
      setBusy(false);
    }
  }

  async function togglePublish(event) {
    setPageError(null);
    try {
      await updateEvent(event.id, {
        status: event.status === 'published' ? 'draft' : 'published',
      });
      reload();
    } catch (err) {
      setPageError(err.message);
    }
  }

  return (
    <div>
      <div className={styles.head}>
        <div>
          <h1>Events and workshops</h1>
          <p style={{ color: 'var(--c-muted)', marginBottom: 0 }}>
            Drafts are only visible here. Publishing puts a session straight onto
            the public listing.
          </p>
        </div>
        <Button onClick={() => { setFormError(null); setEditing('new'); }}>New session</Button>
      </div>

      {pageError && <div className={styles.errorBox}>{pageError}</div>}

      <div className={styles.filters}>
        <div className={`field ${styles.searchField}`}>
          <label htmlFor="staff-event-search">Search</label>
          <input id="staff-event-search" className="control" type="search"
            value={q} onChange={(e) => setQ(e.target.value)} placeholder="Title or description" />
        </div>
        <div className={`field ${styles.selectField}`}>
          <label htmlFor="staff-event-status">Status</label>
          <select id="staff-event-status" className="control" value={status}
            onChange={(e) => setStatus(e.target.value)}>
            <option value="">All statuses</option>
            <option value="published">Published</option>
            <option value="draft">Draft</option>
          </select>
        </div>
        <div className={`field ${styles.selectField}`}>
          <label htmlFor="staff-event-gallery">Gallery</label>
          <select id="staff-event-gallery" className="control" value={gallery}
            onChange={(e) => setGallery(e.target.value)}>
            <option value="">All galleries</option>
            {Object.entries(GALLERIES).map(([value, label]) => (
              <option key={value} value={value}>{label}</option>
            ))}
          </select>
        </div>
      </div>

      {loading && (
        <div className={styles.tableWrap} style={{ padding: 'var(--s-4)' }}>
          <div style={{ display: 'flex', flexDirection: 'column', gap: 'var(--s-3)' }}>
            {Array.from({ length: 5 }).map((_, i) => <Skeleton key={i} height={40} />)}
          </div>
        </div>
      )}

      {error && (
        <EmptyState title="We could not load the programme" body={error.message}>
          <Button onClick={reload}>Try again</Button>
        </EmptyState>
      )}

      {data && data.items.length === 0 && (
        <EmptyState
          title="No sessions match those filters"
          body="Clear the filters, or create the first session."
        >
          <Button variant="ghost" onClick={() => { setQ(''); setStatus(''); setGallery(''); }}>
            Clear filters
          </Button>
          <Button onClick={() => setEditing('new')}>New session</Button>
        </EmptyState>
      )}

      {data && data.items.length > 0 && (
        <div className={styles.tableWrap}>
          <table className={styles.table}>
            <thead>
              <tr>
                <th>Session</th>
                <th>When</th>
                <th>Places</th>
                <th>Admission</th>
                <th>Status</th>
                <th />
              </tr>
            </thead>
            <tbody>
              {data.items.map((event) => {
                const taken = event.capacity - event.spots_remaining;
                return (
                  <tr key={event.id}>
                    <td>
                      <div className={styles.title}>{event.title}</div>
                      <div className={styles.meta}>{galleryLabel(event.gallery)}</div>
                    </td>
                    <td>
                      {formatDate(event.starts_at).replace(/^[^,]+,\s*/, '')}
                      <div className={styles.meta}>
                        {formatTimeRange(event.starts_at, event.ends_at)}
                      </div>
                    </td>
                    <td>
                      {taken} / {event.capacity}
                      {event.is_sold_out && <div className={styles.meta}>Full</div>}
                    </td>
                    <td>
                      {event.price_cents === 0 ? 'Free' : formatPrice(event.price_cents)}
                    </td>
                    <td>
                      {event.status === 'published' ? (
                        <Pill tone="lime">Published</Pill>
                      ) : (
                        <Pill tone="ochre">Draft</Pill>
                      )}
                    </td>
                    <td className={styles.actions}>
                      <Button size="sm" variant="ghost" onClick={() => togglePublish(event)}>
                        {event.status === 'published' ? 'Unpublish' : 'Publish'}
                      </Button>
                      <Button size="sm" variant="ghost"
                        onClick={() => { setFormError(null); setEditing(event); }}>
                        Edit
                      </Button>
                      <Button size="sm" variant="danger" onClick={() => setDeleting(event)}>
                        Delete
                      </Button>
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      )}

      {editing && (
        <EventEditor
          event={editing === 'new' ? null : editing}
          busy={busy}
          error={formError}
          onSave={handleSave}
          onClose={() => setEditing(null)}
        />
      )}

      {deleting && (
        <ConfirmDialog
          title={`Delete “${deleting.title}”?`}
          body="The session is removed from the public listing immediately. Sessions that already have registrations cannot be deleted."
          confirmLabel="Delete session"
          cancelLabel="Keep it"
          busy={busy}
          onConfirm={handleDelete}
          onCancel={() => setDeleting(null)}
        />
      )}
    </div>
  );
}
