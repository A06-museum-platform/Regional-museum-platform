import { Link } from 'react-router-dom';
import useAsync from '../../hooks/useAsync';
import { useAuth } from '../../context/AuthContext';
import { getOpeningHours } from '../../api/openingHours';
import { listEvents } from '../../api/events';
import { listExhibitions } from '../../api/exhibitions';
import { searchCollections } from '../../api/collections';
import { galleryLabel, formatPrice } from '../../api/constants';
import { formatDate, formatTimeRange, startOfToday } from '../../utils/date';
import { openingStatus, dayName, hoursOn } from '../../utils/openingHours';
import CollectionCard from '../../components/CollectionCard';
import ExhibitionCard from '../../components/exhibition/ExhibitionCard';
import Skeleton from '../../components/Skeleton';
import Button from '../../components/Button';
import Pill from '../../components/Pill';
import styles from './HomePage.module.css';

/**
 * Landing page. Client requirement 3(i): "a landing/home page with general
 * info like opening hours, timed events, upcoming events, etc. Should also
 * have the option for members to sign in."
 *
 * Every block reads the live API, so what staff publish appears here
 * without anyone editing this page.
 */
export default function HomePage() {
  const { user, isStaff } = useAuth();
  const hours = useAsync(() => getOpeningHours(), []);
  const events = useAsync(
    () => listEvents({ from: startOfToday().toISOString(), page_size: 4 }),
    []
  );
  const exhibitions = useAsync(() => listExhibitions({ page_size: 3 }), []);
  const highlights = useAsync(() => searchCollections({ highlight: true, page_size: 4 }), []);

  const status = hours.data ? openingStatus(hours.data) : null;

  return (
    <div className={styles.page}>
      <section className={styles.hero} aria-labelledby="home-title">
        <div className={styles.heroText}>
          <p className={styles.kicker}>South Australian Regional Heritage Network</p>
          <h1 id="home-title" className={styles.title}>
            Copper, telegraph and the southern coast — four galleries, one museum
          </h1>
          <p className={styles.lead}>
            Follow the copper from the Monster Mine to the Overland Telegraph, try
            Morse code for yourself, and meet the people who worked the Encounter
            Bay shore. Most visits take about two hours; families with children
            aged 10 to 14 are especially welcome.
          </p>
          <div className={styles.heroActions}>
            <Link to="/book"><Button>Book tickets</Button></Link>
            <Link to="/visit"><Button variant="ghost">Plan your visit</Button></Link>
          </div>
        </div>

        <aside className={styles.statusCard} aria-label="Opening hours">
          {hours.loading ? (
            <Skeleton height={150} />
          ) : hours.error ? (
            <p style={{ margin: 0 }}>Opening hours are unavailable right now.</p>
          ) : (
            <>
              <div className={styles.statusRow}>
                <span className={`${styles.dot} ${status.open ? styles.dotOpen : ''}`} aria-hidden="true" />
                <strong>{status.label}</strong>
              </div>
              {status.note && <div className={styles.statusNote}>{status.note}</div>}
              <WeekHours hours={hours.data} />
              <Link to="/visit" className={styles.statusLink}>Getting here, prices and accessibility</Link>
            </>
          )}

          <div className={styles.memberBox}>
            {user ? (
              <>
                Signed in as <strong>{user.full_name}</strong>.{' '}
                <Link to={isStaff ? '/staff' : '/account'}>
                  {isStaff ? 'Go to the staff workspace' : 'Your account and passes'}
                </Link>
              </>
            ) : (
              <>
                Members, <Link to="/signin">sign in</Link> for free entry and your passes.{' '}
                <Link to="/membership">Become a member</Link>
              </>
            )}
          </div>
        </aside>
      </section>

      <section className={styles.section} aria-labelledby="whats-on">
        <div className={styles.sectionHead}>
          <h2 id="whats-on">Coming up</h2>
          <Link to="/events">All events and workshops</Link>
        </div>
        {events.loading ? (
          <div className={styles.eventGrid}>
            {[1, 2, 3, 4].map((n) => <Skeleton key={n} height={150} />)}
          </div>
        ) : events.error || events.data.items.length === 0 ? (
          <p className={styles.muted}>No sessions are scheduled right now — check back soon.</p>
        ) : (
          <div className={styles.eventGrid}>
            {events.data.items.map((event) => (
              <Link key={event.id} to={`/events/${event.slug}`} className={styles.eventCard}>
                <div className={styles.eventDate}>{formatDate(event.starts_at).replace(/ \d{4}$/, '')}</div>
                <div className={styles.eventTime}>{formatTimeRange(event.starts_at, event.ends_at)}</div>
                <h3 className={styles.eventTitle}>{event.title}</h3>
                <div className={styles.eventPills}>
                  <Pill>{galleryLabel(event.gallery)}</Pill>
                  {event.status === 'cancelled' ? (
                    <Pill tone="danger">Cancelled</Pill>
                  ) : event.is_sold_out ? (
                    <Pill tone="danger">Fully booked</Pill>
                  ) : event.spots_remaining <= 5 ? (
                    <Pill tone="ochre">{event.spots_remaining} places left</Pill>
                  ) : null}
                </div>
                <div className={styles.eventPrice}>
                  {event.price_cents === 0 ? 'Free' : formatPrice(event.price_cents)}
                </div>
              </Link>
            ))}
          </div>
        )}
      </section>

      <section className={styles.section} aria-labelledby="now-showing">
        <div className={styles.sectionHead}>
          <h2 id="now-showing">Now showing</h2>
          <Link to="/exhibitions">All exhibitions</Link>
        </div>
        {exhibitions.loading ? (
          <div className={styles.cardGrid}>{[1, 2, 3].map((n) => <Skeleton key={n} height={300} />)}</div>
        ) : exhibitions.error || exhibitions.data.items.length === 0 ? (
          <p className={styles.muted}>Exhibition details are coming soon.</p>
        ) : (
          <div className={styles.cardGrid}>
            {exhibitions.data.items.map((exhibition) => (
              <ExhibitionCard key={exhibition.id} exhibition={exhibition} />
            ))}
          </div>
        )}
      </section>

      <section className={styles.section} aria-labelledby="from-collection">
        <div className={styles.sectionHead}>
          <h2 id="from-collection">From the collection</h2>
          <Link to="/collections">Search the collection</Link>
        </div>
        {highlights.loading ? (
          <div className={styles.cardGrid4}>{[1, 2, 3, 4].map((n) => <Skeleton key={n} height={230} />)}</div>
        ) : highlights.error || highlights.data.items.length === 0 ? (
          <p className={styles.muted}>The collection is being catalogued.</p>
        ) : (
          <div className={styles.cardGrid4}>
            {highlights.data.items.map((item) => <CollectionCard key={item.id} item={item} />)}
          </div>
        )}
      </section>

      <section className={styles.joinBand} aria-labelledby="join-title">
        <div>
          <h2 id="join-title" className={styles.joinTitle}>Come back as often as you like</h2>
          <p className={styles.joinText}>
            A family membership covers two adults and up to three children for a year,
            with priority booking for workshops.
          </p>
        </div>
        <Link to="/membership"><Button>See memberships</Button></Link>
      </section>
    </div>
  );
}

/** This week's hours, Monday first, with today and exceptions marked. */
function WeekHours({ hours }) {
  const today = startOfToday();
  const monday = new Date(today);
  monday.setDate(today.getDate() - ((today.getDay() + 6) % 7));
  const days = Array.from({ length: 7 }, (_, i) => {
    const day = new Date(monday);
    day.setDate(monday.getDate() + i);
    return day;
  });

  return (
    <table className={styles.hoursTable}>
      <tbody>
        {days.map((day) => {
          const row = hoursOn(day, hours);
          const isToday = day.getTime() === today.getTime();
          return (
            <tr key={day.toISOString()} className={isToday ? styles.today : undefined}>
              <th scope="row">{dayName(day.getDay())}</th>
              <td>
                {row.is_closed ? 'Closed' : `${row.opens_at} – ${row.closes_at}`}
                {row.isException && <span className={styles.exception}> · {row.note || 'special hours'}</span>}
              </td>
            </tr>
          );
        })}
      </tbody>
    </table>
  );
}
