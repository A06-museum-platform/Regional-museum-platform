import { Link } from 'react-router-dom';
import useAsync from '../../hooks/useAsync';
import { listEvents } from '../../api/events';
import { useAuth } from '../../context/AuthContext';
import { galleryLabel } from '../../api/constants';
import { formatDate, formatTimeRange, startOfToday } from '../../utils/date';
import Pill from '../../components/Pill';
import Skeleton from '../../components/Skeleton';
import styles from './StaffDashboard.module.css';

/**
 * "Today at a glance" — the landing screen for both staff and administrators.
 *
 * Revenue and footfall figures from the original wireframe are deliberately
 * NOT here. They imply analytics the prototype does not produce, and showing
 * invented numbers to a client during a demonstration is a bad habit. What is
 * shown below comes from data the system actually holds.
 */
export default function StaffDashboard() {
  const { user, isAdmin } = useAuth();
  const { data, loading } = useAsync(
    () => listEvents({ from: startOfToday().toISOString(), page_size: 5 }),
    []
  );

  const nearlyFull = data?.items.filter((event) => event.spots_remaining <= 5) ?? [];

  return (
    <div>
      <h1>Good day, {user?.full_name?.split(' ')[0]}</h1>
      <p style={{ color: 'var(--c-muted)' }}>
        {isAdmin
          ? 'You have full administrative access, including member records and the activity log.'
          : 'You can publish and update exhibitions, collections, events and opening hours.'}
      </p>

      <div className={styles.stats}>
        <div className={styles.stat}>
          <div className={styles.statLabel}>Upcoming sessions</div>
          <div className={styles.statValue}>{loading ? '—' : data?.total ?? 0}</div>
          <div className={styles.statNote}>Published and open for registration</div>
        </div>
        <div className={styles.stat}>
          <div className={styles.statLabel}>Nearly full</div>
          <div className={styles.statValue}>{loading ? '—' : nearlyFull.length}</div>
          <div className={styles.statNote}>Five places or fewer remaining</div>
        </div>
        <div className={styles.stat}>
          <div className={styles.statLabel}>Collection records</div>
          <div className={styles.statValue}>12</div>
          <div className={styles.statNote}>Placeholder catalogue</div>
        </div>
      </div>

      <section className={styles.panel}>
        <div className={styles.panelHead}>
          <h2 style={{ margin: 0 }}>Next sessions</h2>
          <Link to="/staff/events" style={{ fontSize: 'var(--fs-sm)' }}>Manage events</Link>
        </div>

        {loading && (
          <div style={{ display: 'flex', flexDirection: 'column', gap: 'var(--s-3)' }}>
            <Skeleton height={16} />
            <Skeleton height={16} width="80%" />
            <Skeleton height={16} width="60%" />
          </div>
        )}

        {data?.items.map((event) => (
          <div key={event.id} className={styles.row}>
            <div>
              <div>{event.title}</div>
              <div className={styles.rowMeta}>
                {formatDate(event.starts_at)} · {formatTimeRange(event.starts_at, event.ends_at)}{' '}
                · {galleryLabel(event.gallery)}
              </div>
            </div>
            <div>
              {event.is_sold_out ? (
                <Pill tone="danger">Fully booked</Pill>
              ) : event.spots_remaining <= 5 ? (
                <Pill tone="ochre">{event.spots_remaining} left</Pill>
              ) : (
                <Pill tone="lime">{event.spots_remaining} places</Pill>
              )}
            </div>
          </div>
        ))}
      </section>

      <div className={styles.placeholderNote}>
        <Pill tone="ochre">Prototype</Pill>
        <div>
          Visitor numbers, ticket revenue and staffing density are not produced by
          this prototype. They appeared in the early wireframes and have been kept
          out of the build deliberately — inventing figures for a demonstration
          misrepresents what the system does.
        </div>
      </div>
    </div>
  );
}
