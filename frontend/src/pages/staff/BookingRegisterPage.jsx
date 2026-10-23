import { useState } from 'react';
import useAsync from '../../hooks/useAsync';
import useDebouncedValue from '../../hooks/useDebouncedValue';
import { listStaffBookings, getBookingSummary, checkInBooking, staffCancelBooking } from '../../api/bookings';
import { listStaffEvents, listEventRegistrations } from '../../api/events';
import { ACCESSIBILITY_OPTIONS, formatPrice } from '../../api/constants';
import { formatDate, formatTimeRange, isoDateFromToday, formatCalendarDate } from '../../utils/date';
import Button from '../../components/Button';
import Pill from '../../components/Pill';
import Skeleton from '../../components/Skeleton';
import EmptyState from '../../components/EmptyState';
import ConfirmDialog from '../../components/ConfirmDialog';
import styles from './StaffContentPage.module.css';
import dash from './StaffDashboard.module.css';

/**
 * Bookings & check-in (role-permission matrix: "View all bookings and event
 * registrations"; proposal: "Booking Management").
 *
 * Front desk view: pick a day, see who is arriving in each window and check
 * them in. Accessibility requests are shown on the row so the sensory
 * backpack is ready before the family reaches the desk.
 */
export default function BookingRegisterPage() {
  const [tab, setTab] = useState('bookings');
  return (
    <div>
      <h1>Bookings and check-in</h1>
      <p style={{ color: 'var(--c-muted)' }}>
        General-admission bookings by day, and who is registered for each workshop.
      </p>
      <div className={styles.tabs} role="tablist">
        {[['bookings', 'Visitor bookings'], ['events', 'Event registrations']].map(([key, label]) => (
          <button key={key} type="button" role="tab" aria-selected={tab === key}
            className={`${styles.tab} ${tab === key ? styles.tabActive : ''}`} onClick={() => setTab(key)}>
            {label}
          </button>
        ))}
      </div>
      {tab === 'bookings' ? <Bookings /> : <Registrations />}
    </div>
  );
}

const ticketsText = (lines) => lines.map((l) => `${l.quantity} ${l.name}`).join(', ');

function Bookings() {
  const [date, setDate] = useState(isoDateFromToday(0));
  const [q, setQ] = useState('');
  const debouncedQ = useDebouncedValue(q, 300);
  const searching = debouncedQ.trim().length > 0;
  const list = useAsync(() => listStaffBookings({ date: searching ? '' : date, q: debouncedQ }),
    [date, debouncedQ, searching]);
  const summary = useAsync(() => getBookingSummary(date), [date]);
  const [cancelling, setCancelling] = useState(null);
  const [busy, setBusy] = useState(null);
  const [error, setError] = useState(null);

  async function act(fn, reference) {
    setBusy(reference);
    setError(null);
    try {
      await fn(reference);
      list.reload();
      summary.reload();
    } catch (err) {
      setError(err.message);
    } finally {
      setBusy(null);
    }
  }

  return (
    <>
      <div className={styles.filters}>
        <div className="field">
          <label htmlFor="bk-date">Day</label>
          <input id="bk-date" className="control" type="date" value={date} disabled={searching}
            onChange={(e) => setDate(e.target.value || isoDateFromToday(0))} />
        </div>
        <div className={`field ${styles.searchField}`}>
          <label htmlFor="bk-q">Find a booking (any day)</label>
          <input id="bk-q" className="control" type="search" value={q}
            placeholder="Reference, name or email" onChange={(e) => setQ(e.target.value)} />
        </div>
      </div>

      {!searching && summary.data && (
        <div className={dash.stats}>
          <div className={dash.stat}>
            <div className={dash.statLabel}>{formatCalendarDate(date)}</div>
            <div className={dash.statValue}>{summary.data.tickets}</div>
            <div className={dash.statNote}>tickets in {summary.data.bookings} bookings</div>
          </div>
          <div className={dash.stat}>
            <div className={dash.statLabel}>Checked in</div>
            <div className={dash.statValue}>{summary.data.checked_in} / {summary.data.bookings}</div>
            <div className={dash.statNote}>bookings arrived</div>
          </div>
          <div className={dash.stat}>
            <div className={dash.statLabel}>By arrival window</div>
            <div className={dash.statNote} style={{ marginTop: 'var(--s-2)' }}>
              {summary.data.windows.length === 0 ? 'No bookings' : summary.data.windows.map((w) => (
                <div key={w.start}>{w.start} — {w.tickets} tickets ({w.checked_in}/{w.bookings} in)</div>
              ))}
            </div>
          </div>
        </div>
      )}

      {error && <div className={styles.errorBox} role="alert">{error}</div>}

      {list.loading ? <Skeleton height={160} /> : list.error ? (
        <EmptyState title="We could not load the bookings" body={list.error.message}>
          <Button variant="ghost" onClick={list.reload}>Try again</Button>
        </EmptyState>
      ) : list.data.items.length === 0 ? (
        <EmptyState title={searching ? `No bookings match “${debouncedQ}”` : 'No bookings for this day'}
          body={searching ? 'Check the reference, or search by the visitor’s name or email.' : 'Pick another day above.'} />
      ) : (
        <div className={styles.tableWrap}>
          <table className={styles.table}>
            <thead>
              <tr><th>Arrival</th><th>Visitor</th><th>Tickets</th><th>Needs</th><th>Status</th><th /></tr>
            </thead>
            <tbody>
              {[...list.data.items].sort((a, b) => (a.visit_date + a.arrival_window.start).localeCompare(b.visit_date + b.arrival_window.start)).map((b) => (
                <tr key={b.id}>
                  <td>
                    <div style={{ fontWeight: 600 }}>{b.arrival_window.start}–{b.arrival_window.end}</div>
                    {searching && <div className={styles.meta}>{formatCalendarDate(b.visit_date)}</div>}
                    <div className={styles.meta}>{b.reference}</div>
                  </td>
                  <td>
                    <div>{b.visitor.first_name} {b.visitor.last_name}</div>
                    <div className={styles.meta}>{b.visitor.email}{b.visitor.mobile && ` · ${b.visitor.mobile}`}</div>
                  </td>
                  <td>
                    {ticketsText(b.lines)}
                    <div className={styles.meta}>{b.total_cents === 0 ? 'Free' : formatPrice(b.total_cents)} (simulated)</div>
                  </td>
                  <td>
                    {b.accessibility.length === 0 ? <span className={styles.meta}>—</span>
                      : b.accessibility.map((key) => <Pill key={key} tone="ochre">{ACCESSIBILITY_OPTIONS[key] ?? key}</Pill>)}
                  </td>
                  <td>
                    {b.status === 'cancelled' ? <Pill tone="danger">Cancelled</Pill>
                      : b.checked_in ? <Pill tone="lime">Checked in</Pill>
                        : b.status === 'completed' ? <Pill>No-show</Pill>
                          : <Pill>Expected</Pill>}
                  </td>
                  <td className={styles.actions}>
                    {b.status !== 'cancelled' && !b.checked_in && b.visit_date <= isoDateFromToday(0) && (
                      <Button size="sm" disabled={busy === b.reference} onClick={() => act(checkInBooking, b.reference)}>
                        {busy === b.reference ? 'Checking in…' : 'Check in'}
                      </Button>
                    )}
                    {b.status === 'reserved' && b.visit_date >= isoDateFromToday(0) && !b.checked_in && (
                      <Button size="sm" variant="ghost" onClick={() => setCancelling(b)}>Cancel</Button>
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {cancelling && (
        <ConfirmDialog
          title={`Cancel booking ${cancelling.reference}?`}
          body={`Cancels ${cancelling.visitor.first_name} ${cancelling.visitor.last_name}’s visit on ${formatCalendarDate(cancelling.visit_date)} and puts the places back on sale. Use this when a visitor phones or emails to cancel.`}
          confirmLabel="Cancel booking"
          cancelLabel="Keep it"
          busy={busy === cancelling.reference}
          onConfirm={async () => { const ref = cancelling.reference; setCancelling(null); await act(staffCancelBooking, ref); }}
          onCancel={() => setCancelling(null)}
        />
      )}
    </>
  );
}

function Registrations() {
  const events = useAsync(() => listStaffEvents({}), []);
  const [selected, setSelected] = useState('');
  const regs = useAsync(() => (selected ? listEventRegistrations(selected) : Promise.resolve(null)), [selected]);

  const options = events.data?.items.filter((e) => e.status !== 'draft') ?? [];
  const event = options.find((e) => String(e.id) === String(selected));
  const active = regs.data?.filter((r) => r.status === 'confirmed') ?? [];

  return (
    <>
      <div className="field" style={{ maxWidth: 560 }}>
        <label htmlFor="reg-event">Session</label>
        <select id="reg-event" className="control" value={selected} onChange={(e) => setSelected(e.target.value)}>
          <option value="">Choose a session…</option>
          {options.map((e) => (
            <option key={e.id} value={e.id}>
              {formatDate(e.starts_at).replace(/^[^,]+,\s*/, '')} — {e.title} ({e.capacity - e.spots_remaining}/{e.capacity})
            </option>
          ))}
        </select>
      </div>

      {!selected ? (
        <p style={{ color: 'var(--c-muted)' }}>Pick a session to see who is coming.</p>
      ) : regs.loading || (!regs.data && !regs.error) ? <Skeleton height={120} /> : regs.error ? (
        <EmptyState title="We could not load the registrations" body={regs.error.message} />
      ) : (
        <>
          <p>
            <strong>{event?.title}</strong> · {event && formatTimeRange(event.starts_at, event.ends_at)} ·{' '}
            {active.reduce((sum, r) => sum + r.party_size, 0)} of {event?.capacity} places taken
          </p>
          {regs.data.length === 0 ? (
            <EmptyState title="Nobody has registered yet" body="Registrations appear here as visitors sign up." />
          ) : (
            <div className={styles.tableWrap}>
              <table className={styles.table}>
                <thead><tr><th>Contact</th><th>Account</th><th>People</th><th>Registered</th><th>Status</th></tr></thead>
                <tbody>
                  {regs.data.map((r) => (
                    <tr key={r.id}>
                      <td>{r.contact_name}<div className={styles.meta}>{r.contact_email}</div></td>
                      <td className={styles.meta}>{r.account_email}</td>
                      <td>{r.party_size}</td>
                      <td className={styles.meta}>{new Date(r.registered_at).toLocaleDateString('en-AU')}<br />{r.reference}</td>
                      <td>{r.status === 'confirmed' ? <Pill tone="lime">Registered</Pill> : <Pill tone="danger">Cancelled</Pill>}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </>
      )}
    </>
  );
}
