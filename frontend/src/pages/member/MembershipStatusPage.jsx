import { Link } from 'react-router-dom';
import useAsync from '../../hooks/useAsync';
import { useAuth } from '../../context/AuthContext';
import { getMyMembership } from '../../api/memberships';
import { listMyBookings } from '../../api/bookings';
import { formatPrice } from '../../api/constants';
import { formatCalendarDate, isoDateFromToday } from '../../utils/date';
import MembershipStatusPanel from '../../components/membership/MembershipStatusPanel';
import EmptyState from '../../components/EmptyState';
import Skeleton from '../../components/Skeleton';
import Button from '../../components/Button';
import Pill from '../../components/Pill';
import styles from './MembershipStatusPage.module.css';

const BOOKING_PILL = {
  reserved: ['lime', 'Upcoming'],
  completed: ['grey', 'Visited'],
  cancelled: ['danger', 'Cancelled'],
};

const ticketsLabel = (lines) => {
  const count = lines.reduce((sum, line) => sum + line.quantity, 0);
  return `${count} ${count === 1 ? 'ticket' : 'tickets'} · ${lines.map((l) => `${l.quantity} ${l.name}`).join(', ')}`;
};

function BookingRow({ booking }) {
  const [tone, label] = BOOKING_PILL[booking.status] || ['grey', booking.status];
  return (
    <li className={styles.booking}>
      <div className={styles.bookingDate}>
        <div className={styles.bookingDay}>{formatCalendarDate(booking.visit_date)}</div>
        <div className={styles.bookingMeta}>
          {booking.arrival_window.start}–{booking.arrival_window.end} arrival · {ticketsLabel(booking.lines)}
        </div>
        <div className={styles.bookingMeta}>
          {booking.reference} · {booking.total_cents === 0 ? 'Free' : formatPrice(booking.total_cents)}
        </div>
      </div>
      <Pill tone={tone}>{label}</Pill>
      <Link to={`/book/confirmation/${booking.reference}`}>
        <Button size="sm" variant="ghost">{booking.status === 'reserved' ? 'View pass' : 'View'}</Button>
      </Link>
    </li>
  );
}

/**
 * Member portal: the member's own membership and bookings.
 * Route is member-only — a staff account has no membership to show.
 */
export default function MembershipStatusPage() {
  const { user } = useAuth();
  const membership = useAsync(() => getMyMembership(user), [user.id]);
  const bookings = useAsync(() => listMyBookings(user), [user.id]);

  const today = isoDateFromToday(0);
  const all = bookings.data?.items || [];
  const upcoming = all
    .filter((b) => b.status === 'reserved' && b.visit_date >= today)
    .sort((a, b) => (a.visit_date > b.visit_date ? 1 : -1));
  const past = all.filter((b) => !upcoming.includes(b));

  return (
    <div>
      <h1>Hello, {user.full_name.split(' ')[0]}</h1>
      <p style={{ color: 'var(--c-muted)' }}>Your membership and visits, in one place.</p>

      <div className={styles.layout}>
        <section aria-labelledby="membership-heading">
          <div className={styles.headRow}>
            <h2 id="membership-heading" className={styles.heading}>Membership</h2>
          </div>
          {membership.loading ? (
            <Skeleton height={240} />
          ) : membership.error ? (
            <EmptyState title="We could not load your membership" body={membership.error.message}>
              <Button variant="ghost" onClick={membership.reload}>Try again</Button>
            </EmptyState>
          ) : (
            <MembershipStatusPanel membership={membership.data} />
          )}
        </section>

        <section aria-labelledby="bookings-heading">
          <div className={styles.headRow}>
            <h2 id="bookings-heading" className={styles.heading}>Upcoming visits</h2>
            <Link to="/book"><Button size="sm">Book tickets</Button></Link>
          </div>

          {bookings.loading ? (
            <div style={{ display: 'flex', flexDirection: 'column', gap: 'var(--s-2)' }}>
              <Skeleton height={76} />
              <Skeleton height={76} />
            </div>
          ) : bookings.error ? (
            <EmptyState title="We could not load your bookings" body={bookings.error.message}>
              <Button variant="ghost" onClick={bookings.reload}>Try again</Button>
            </EmptyState>
          ) : upcoming.length === 0 ? (
            <div className={styles.empty}>
              No visits booked yet. Choose a day and arrival time — it takes about a minute.
            </div>
          ) : (
            <ul className={styles.bookings}>
              {upcoming.map((booking) => <BookingRow key={booking.id} booking={booking} />)}
            </ul>
          )}

          {past.length > 0 && (
            <>
              <h3 className={styles.subheading}>Past and cancelled</h3>
              <ul className={styles.bookings}>
                {past.map((booking) => <BookingRow key={booking.id} booking={booking} />)}
              </ul>
            </>
          )}
        </section>
      </div>
    </div>
  );
}
