import useAsync from '../../hooks/useAsync';
import { listMyActivity } from '../../api/activity';
import { ACTION_LABELS } from '../../api/mocks/activityLog';
import Skeleton from '../Skeleton';
import styles from './Member.module.css';

const when = (iso) =>
  new Date(iso).toLocaleString('en-AU', { day: 'numeric', month: 'short', hour: '2-digit', minute: '2-digit' });

/** "Last activity" (client requirement 3(iv)): the account's recent actions
 *  and decisions about it, written by the server. */
export default function ActivityPanel() {
  const { data, loading, error } = useAsync(() => listMyActivity({ size: 8 }), []);
  return (
    <section className={styles.panel} aria-labelledby="activity-heading">
      <div className={styles.panelHead}>
        <h2 id="activity-heading" className={styles.heading}>Recent activity</h2>
      </div>
      {loading ? <Skeleton height={120} /> : error ? (
        <div className={styles.empty}>{error.message}</div>
      ) : data.items.length === 0 ? (
        <div className={styles.empty}>Bookings, registrations and membership updates will appear here.</div>
      ) : (
        <ol className={styles.timeline}>
          {data.items.map((entry) => (
            <li key={entry.id}>
              <div className={styles.timelineWhen}>{when(entry.created_at)}</div>
              <div>
                <strong>{ACTION_LABELS[entry.action] ?? entry.action}</strong>
                <div className={styles.meta}>
                  {entry.target}
                  {entry.reference && ` · ${entry.reference}`}
                </div>
              </div>
            </li>
          ))}
        </ol>
      )}
    </section>
  );
}
