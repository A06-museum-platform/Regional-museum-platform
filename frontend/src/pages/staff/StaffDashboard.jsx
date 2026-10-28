import { Link } from 'react-router-dom';
import useAsync from '../../hooks/useAsync';
import { listEvents } from '../../api/events';
import { getStaffToday } from '../../api/bookings';
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

  const today = useAsync(() => getStaffToday(), []);
  const t = today.data;
  const nearlyFull = data?.items.filter((event) => event.spots_remaining <= 5) ?? [];

  return (
    <div>
      <h1>Good day, {user?.full_name?.split(' ')[0]}</h1>
      <p style={{ color: 'var(--c-muted)' }}>
        {isAdmin
          ? 'You have full administrative access, including member records and the activity log.'
          : 'You can publish and update exhibitions, collections, events and opening hours.'}
      </p>

      {t && (
        <p style={{ marginTop: 0 }}>
          <strong>{t.is_open ? `Open today ${t.opens_at}–${t.closes_at}` : 'Closed today'}</strong>
          {t.note && <span style={{ color: 'var(--c-muted)' }}> · {t.note}</span>}
        </p>
      )}

      <div className={styles.stats}>
        <Link to="/staff/bookings" className={styles.stat} style={{ textDecoration: 'none', color: 'inherit' }}>
          <div className={styles.statLabel}>Visitors booked today</div>
          <div className={styles.statValue}>{t ? t.bookings.tickets : '—'}</div>
          <div className={styles.statNote}>
            {t ? `${t.bookings.checked_in} of ${t.bookings.bookings} bookings checked in` : 'General admission'}
          </div>
        </Link>
        <div className={styles.stat}>
          <div className={styles.statLabel}>Upcoming sessions</div>
          <div className={styles.statValue}>{loading ? '—' : data?.total ?? 0}</div>
          <div className={styles.statNote}>{nearlyFull.length} of the next five nearly full</div>
        </div>
        <Link to="/staff/content" className={styles.stat} style={{ textDecoration: 'none', color: 'inherit' }}>
          <div className={styles.statLabel}>Collection records</div>
          <div className={styles.statValue}>{t ? t.objects : '—'}</div>
          <div className={styles.statNote}>
            {t ? `${t.draft_objects} draft · ${t.exhibitions} exhibitions on show` : 'Objects catalogued'}
          </div>
        </Link>
        {isAdmin && (
          <Link to="/admin/members?status=pending" className={styles.stat} style={{ textDecoration: 'none', color: 'inherit' }}>
            <div className={styles.statLabel}>Membership applications</div>
            <div className={styles.statValue}>{t ? t.pending_applications : '—'}</div>
            <div className={styles.statNote}>Waiting for approval</div>
          </Link>
        )}
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
          Every figure here comes from the bookings, events and collection records the
          system holds. Revenue and footfall analytics from the early wireframes are out
          of scope — payment is simulated, so there is no real revenue to report.
        </div>
      </div>
    </div>
  );
}
