import { Link } from 'react-router-dom';
import useAsync from '../../hooks/useAsync';
import { useAuth } from '../../context/AuthContext';
import { getVisitorInformation } from '../../api/visitInformation';
import { getOpeningHours } from '../../api/openingHours';
import { listTicketTypes } from '../../api/bookings';
import { formatPrice, GALLERIES } from '../../api/constants';
import { formatCalendarDate } from '../../utils/date';
import { dayName } from '../../utils/openingHours';
import EmptyState from '../../components/EmptyState';
import Skeleton from '../../components/Skeleton';
import Button from '../../components/Button';
import Pill from '../../components/Pill';
import styles from './VisitPage.module.css';

const MONDAY_FIRST = [1, 2, 3, 4, 5, 6, 0];

/**
 * Plan your visit (proposal scope: "address, opening hours, transport,
 * parking, ticket prices, contact details, facilities, and accessibility").
 * Everything here is edited by staff — hours on /staff/hours, the rest on
 * /staff/visit — so nothing on this page is hard-coded.
 */
export default function VisitPage() {
  const { user } = useAuth();
  const info = useAsync(() => getVisitorInformation(), []);
  const hours = useAsync(() => getOpeningHours(), []);
  const tickets = useAsync(() => listTicketTypes(user), [user?.id]);

  return (
    <div>
      <h1>Plan your visit</h1>
      <p className={styles.lead}>
        Everything you need before you come: when we are open, what it costs,
        how to get here and what is on site.
      </p>

      <div className={styles.layout}>
        <div className={styles.main}>
          <section className={styles.card} aria-labelledby="visit-hours">
            <h2 id="visit-hours">Opening hours</h2>
            {hours.loading ? <Skeleton height={200} /> : hours.error ? (
              <p className={styles.muted}>Opening hours are unavailable right now.</p>
            ) : (
              <>
                <table className={styles.table}>
                  <tbody>
                    {MONDAY_FIRST.map((day) => {
                      const row = hours.data.weekly.find((r) => r.day_of_week === day);
                      return (
                        <tr key={day}>
                          <th scope="row">{dayName(day)}</th>
                          <td>{!row || row.is_closed ? 'Closed' : `${row.opens_at} – ${row.closes_at}`}</td>
                          <td className={styles.muted}>{row?.note}</td>
                        </tr>
                      );
                    })}
                  </tbody>
                </table>
                {hours.data.overrides.length > 0 && (
                  <>
                    <h3 className={styles.subheading}>Special dates</h3>
                    <ul className={styles.exceptions}>
                      {hours.data.overrides.map((row) => (
                        <li key={row.id}>
                          <strong>{formatCalendarDate(row.specific_date)}</strong>{' '}
                          {row.is_closed ? 'Closed' : `${row.opens_at} – ${row.closes_at}`}
                          {row.note && <span className={styles.muted}> · {row.note}</span>}
                        </li>
                      ))}
                    </ul>
                  </>
                )}
                <p className={styles.hint}>Hours change with the seasons; this page always shows the current times.</p>
              </>
            )}
          </section>

          <section className={styles.card} aria-labelledby="visit-prices">
            <h2 id="visit-prices">Tickets</h2>
            {tickets.loading ? <Skeleton height={140} /> : tickets.error ? (
              <p className={styles.muted}>Prices are unavailable right now.</p>
            ) : (
              <table className={styles.table}>
                <tbody>
                  {tickets.data.items.map((type) => (
                    <tr key={type.id}>
                      <th scope="row">{type.name}</th>
                      <td>{type.price_cents === 0 ? 'Free' : formatPrice(type.price_cents)}</td>
                      <td className={styles.muted}>{type.description}</td>
                    </tr>
                  ))}
                  {!tickets.data.items.some((type) => type.members_only) && (
                    <tr>
                      <th scope="row">Members</th>
                      <td>Free</td>
                      <td className={styles.muted}>
                        Everyone on an active membership. <Link to="/membership">About membership</Link>
                      </td>
                    </tr>
                  )}
                </tbody>
              </table>
            )}
            <p className={styles.hint}>
              One ticket covers all four galleries: {Object.values(GALLERIES).join(', ')}.
              Book a two-hour arrival window online — payment is simulated in this prototype.
            </p>
            <Link to="/book"><Button>Book tickets</Button></Link>
          </section>

          <section className={styles.card} aria-labelledby="visit-facilities">
            <h2 id="visit-facilities">Facilities and accessibility</h2>
            {info.loading ? <Skeleton height={180} /> : info.error ? (
              <p className={styles.muted}>Facility details are unavailable right now.</p>
            ) : (
              <ul className={styles.facilities}>
                {info.data.facilities.map((facility) => (
                  <li key={facility.id} className={styles.facility}>
                    <div className={styles.facilityHead}>
                      <strong>{facility.name}</strong>
                      {!facility.is_available && <Pill tone="ochre">Temporarily unavailable</Pill>}
                    </div>
                    {facility.description && <div>{facility.description}</div>}
                    <div className={styles.muted}>
                      {[facility.location, facility.accessibility_info].filter(Boolean).join(' · ')}
                    </div>
                  </li>
                ))}
              </ul>
            )}
            <p className={styles.hint}>
              Need step-free access, a sensory backpack or the hearing loop? Tick it when you
              book and we will have it ready.
            </p>
          </section>
        </div>

        <aside className={styles.side}>
          {info.loading ? <Skeleton height={320} /> : info.error ? (
            <EmptyState title="Visitor information is unavailable" body={info.error.message}>
              <Button variant="ghost" onClick={info.reload}>Try again</Button>
            </EmptyState>
          ) : (
            <div className={styles.card}>
              <h2>Getting here</h2>
              <h3 className={styles.subheading}>Address</h3>
              <p>{info.data.museum_name}<br />{info.data.address}</p>
              {info.data.transport && (
                <>
                  <h3 className={styles.subheading}>Public transport</h3>
                  <p>{info.data.transport}</p>
                </>
              )}
              {info.data.parking && (
                <>
                  <h3 className={styles.subheading}>Parking</h3>
                  <p>{info.data.parking}</p>
                </>
              )}
              <h3 className={styles.subheading}>Contact</h3>
              <p>
                {info.data.phone && <>Phone <a href={`tel:${info.data.phone.replace(/\s/g, '')}`}>{info.data.phone}</a><br /></>}
                {info.data.email && <>Email <a href={`mailto:${info.data.email}`}>{info.data.email}</a></>}
              </p>
              {info.data.about && (
                <>
                  <h3 className={styles.subheading}>About the museum</h3>
                  <p className={styles.muted}>{info.data.about}</p>
                </>
              )}
            </div>
          )}
        </aside>
      </div>
    </div>
  );
}
