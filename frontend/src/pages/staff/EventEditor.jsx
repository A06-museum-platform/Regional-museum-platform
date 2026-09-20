import { useState } from 'react';
import Modal from '../../components/Modal';
import Button from '../../components/Button';
import { GALLERIES } from '../../api/constants';
import styles from './StaffEventsPage.module.css';

/**
 * Create / edit form for an event.
 *
 * Datetime handling: the form works in `datetime-local` strings, the API
 * works in ISO 8601. Convert at the boundary, here, rather than letting two
 * formats spread through the app.
 */

const toLocalInput = (iso) => {
  if (!iso) return '';
  const date = new Date(iso);
  const pad = (n) => String(n).padStart(2, '0');
  return `${date.getFullYear()}-${pad(date.getMonth() + 1)}-${pad(date.getDate())}T${pad(
    date.getHours()
  )}:${pad(date.getMinutes())}`;
};

const EMPTY = {
  title: '',
  description: '',
  gallery: 'main_hall',
  starts_at: '',
  ends_at: '',
  capacity: 20,
  price_cents: 0,
  member_price_cents: 0,
  age_min: '',
  age_max: '',
  status: 'draft',
};

export default function EventEditor({ event, onSave, onClose, busy, error }) {
  const [form, setForm] = useState(
    event
      ? {
          ...event,
          starts_at: toLocalInput(event.starts_at),
          ends_at: toLocalInput(event.ends_at),
          age_min: event.age_min ?? '',
          age_max: event.age_max ?? '',
        }
      : EMPTY
  );

  const set = (key) => (e) => setForm((prev) => ({ ...prev, [key]: e.target.value }));

  const endBeforeStart =
    form.starts_at && form.ends_at && new Date(form.ends_at) <= new Date(form.starts_at);

  const valid =
    form.title.trim().length > 2 &&
    form.description.trim().length > 10 &&
    form.starts_at &&
    form.ends_at &&
    !endBeforeStart &&
    Number(form.capacity) > 0;

  function save(status) {
    onSave({
      title: form.title.trim(),
      description: form.description.trim(),
      gallery: form.gallery,
      starts_at: new Date(form.starts_at).toISOString(),
      ends_at: new Date(form.ends_at).toISOString(),
      capacity: Number(form.capacity),
      price_cents: Math.round(Number(form.price_cents)),
      member_price_cents: Math.round(Number(form.member_price_cents)),
      age_min: form.age_min === '' ? null : Number(form.age_min),
      age_max: form.age_max === '' ? null : Number(form.age_max),
      status,
    });
  }

  return (
    <Modal
      title={event ? 'Edit session' : 'New session'}
      onClose={onClose}
      footer={
        <>
          <Button variant="ghost" onClick={onClose}>Cancel</Button>
          <Button variant="ghost" disabled={!valid || busy} onClick={() => save('draft')}>
            Save as draft
          </Button>
          <Button disabled={!valid || busy} onClick={() => save('published')}>
            {busy ? 'Saving…' : 'Publish'}
          </Button>
        </>
      }
    >
      {error && <div className={styles.errorBox}>{error}</div>}

      <div className="field">
        <label htmlFor="ev-title">Title</label>
        <input id="ev-title" className="control" value={form.title} onChange={set('title')} />
      </div>

      <div className="field">
        <label htmlFor="ev-desc">Description</label>
        <textarea
          id="ev-desc"
          className="control"
          rows={4}
          value={form.description}
          onChange={set('description')}
        />
        <div className="hint">
          Written for visitors, not for staff. This is what appears on the public listing.
        </div>
      </div>

      <div className="field">
        <label htmlFor="ev-gallery">Gallery</label>
        <select id="ev-gallery" className="control" value={form.gallery} onChange={set('gallery')}>
          {Object.entries(GALLERIES).map(([value, label]) => (
            <option key={value} value={value}>{label}</option>
          ))}
        </select>
      </div>

      <div className={styles.formRow}>
        <div className="field">
          <label htmlFor="ev-start">Starts</label>
          <input id="ev-start" className="control" type="datetime-local"
            value={form.starts_at} onChange={set('starts_at')} />
        </div>
        <div className="field">
          <label htmlFor="ev-end">Ends</label>
          <input
            id="ev-end"
            className={`control ${endBeforeStart ? 'control--error' : ''}`}
            type="datetime-local"
            value={form.ends_at}
            onChange={set('ends_at')}
          />
          {endBeforeStart && (
            <div className="error-text">The finish time needs to be after the start time.</div>
          )}
        </div>
      </div>

      <div className={styles.formRow}>
        <div className="field">
          <label htmlFor="ev-capacity">Places available</label>
          <input id="ev-capacity" className="control" type="number" min="1"
            value={form.capacity} onChange={set('capacity')} />
          <div className="hint">
            The client confirmed capacity is decided per event, not fixed for the venue.
          </div>
        </div>
        <div className="field">
          <label htmlFor="ev-price">Admission (cents)</label>
          <input id="ev-price" className="control" type="number" min="0" step="100"
            value={form.price_cents} onChange={set('price_cents')} />
          <div className="hint">1500 = $15.00. Enter 0 for a free session.</div>
        </div>
      </div>

      <div className={styles.formRow}>
        <div className="field">
          <label htmlFor="ev-member-price">Member admission (cents)</label>
          <input id="ev-member-price" className="control" type="number" min="0" step="100"
            value={form.member_price_cents} onChange={set('member_price_cents')} />
        </div>
        <div className={styles.formRow} style={{ gap: 'var(--s-3)' }}>
          <div className="field">
            <label htmlFor="ev-age-min">Minimum age</label>
            <input id="ev-age-min" className="control" type="number" min="0"
              value={form.age_min} onChange={set('age_min')} placeholder="Any" />
          </div>
          <div className="field">
            <label htmlFor="ev-age-max">Maximum age</label>
            <input id="ev-age-max" className="control" type="number" min="0"
              value={form.age_max} onChange={set('age_max')} placeholder="Any" />
          </div>
        </div>
      </div>
    </Modal>
  );
}
