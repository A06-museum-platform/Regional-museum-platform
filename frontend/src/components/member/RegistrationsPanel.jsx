import { useState } from 'react';
import { Link } from 'react-router-dom';
import useAsync from '../../hooks/useAsync';
import { listMyRegistrations, cancelRegistration } from '../../api/events';
import { galleryLabel } from '../../api/constants';
import { formatDate, formatTimeRange } from '../../utils/date';
import ConfirmDialog from '../ConfirmDialog';
import Skeleton from '../Skeleton';
import Button from '../Button';
import Pill from '../Pill';
import styles from './Member.module.css';

const PILL = { confirmed: ['lime', 'Registered'], cancelled: ['danger', 'Cancelled'], attended: ['grey', 'Attended'] };

/** The account's workshop and event registrations, with cancel for upcoming ones. */
export default function RegistrationsPanel() {
  const { data, loading, error, reload } = useAsync(() => listMyRegistrations(), []);
  const [cancelling, setCancelling] = useState(null);
  const [busy, setBusy] = useState(false);
  const [actionError, setActionError] = useState(null);

  async function confirmCancel() {
    setBusy(true);
    setActionError(null);
    try {
      await cancelRegistration(cancelling.reference);
      setCancelling(null);
      reload();
    } catch (err) {
      setActionError(err.message);
      setCancelling(null);
    } finally {
      setBusy(false);
    }
  }

  const items = data?.items ?? [];
  const upcoming = items.filter((r) => r.status === 'confirmed' && !r.is_past).reverse();
  const rest = items.filter((r) => !upcoming.includes(r));

  return (
    <section className={styles.panel} aria-labelledby="regs-heading">
      <div className={styles.panelHead}>
        <h2 id="regs-heading" className={styles.heading}>Workshops and events</h2>
        <Link to="/events"><Button size="sm" variant="ghost">Find a session</Button></Link>
      </div>
      {actionError && <div className={styles.error} role="alert">{actionError}</div>}
      {loading ? <Skeleton height={120} /> : error ? (
        <div className={styles.empty}>{error.message}</div>
      ) : items.length === 0 ? (
        <div className={styles.empty}>You haven’t registered for a session yet.</div>
      ) : (
        <ul className={styles.list}>
          {[...upcoming, ...rest].map((reg) => {
            const [tone, label] = reg.is_past && reg.status === 'confirmed' ? ['grey', 'Finished'] : PILL[reg.status];
            return (
              <li key={reg.id} className={styles.listRow}>
                <div className={styles.listMain}>
                  <Link to={`/events/${reg.event_slug}`} className={styles.listTitle}>{reg.event_title}</Link>
                  <div className={styles.meta}>
                    {formatDate(reg.starts_at)} · {formatTimeRange(reg.starts_at, reg.ends_at)} · {galleryLabel(reg.gallery)}
                  </div>
                  <div className={styles.meta}>
                    {reg.party_size} {reg.party_size === 1 ? 'person' : 'people'} · {reg.reference}
                  </div>
                </div>
                <Pill tone={tone}>{label}</Pill>
                {reg.status === 'confirmed' && !reg.is_past && (
                  <Button size="sm" variant="ghost" onClick={() => setCancelling(reg)}>Cancel</Button>
                )}
              </li>
            );
          })}
        </ul>
      )}
      {cancelling && (
        <ConfirmDialog
          title={`Cancel your place at “${cancelling.event_title}”?`}
          body="Your places go back on offer straight away. You can register again later if there is still room."
          confirmLabel="Cancel registration"
          cancelLabel="Keep my place"
          busy={busy}
          onConfirm={confirmCancel}
          onCancel={() => setCancelling(null)}
        />
      )}
    </section>
  );
}
