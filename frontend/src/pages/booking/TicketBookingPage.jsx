import { useMemo, useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import useAsync from '../../hooks/useAsync';
import { useAuth } from '../../context/AuthContext';
import { getAvailability, listTicketTypes, BOOKING_HORIZON_DAYS } from '../../api/bookings';
import { getOpeningHours } from '../../api/openingHours';
import { formatPrice } from '../../api/constants';
import { formatCalendarDate, fromIsoDate, isoDateFromToday } from '../../utils/date';
import { loadDraft, saveDraft } from '../../utils/bookingDraft';
import BookingSteps from '../../components/booking/BookingSteps';
import TicketSelector from '../../components/booking/TicketSelector';
import FormErrorSummary from '../../components/FormErrorSummary';
import EmptyState from '../../components/EmptyState';
import Skeleton from '../../components/Skeleton';
import Button from '../../components/Button';
import Pill from '../../components/Pill';
import styles from '../../components/booking/Booking.module.css';

const QUICK_DATE_COUNT = 6;

/** Next few days the museum is open, from the published opening hours. */
function upcomingOpenDays(hours) {
  if (!hours) return [];
  const days = [];
  for (let offset = 0; offset < 21 && days.length < QUICK_DATE_COUNT; offset += 1) {
    const iso = isoDateFromToday(offset);
    const override = hours.overrides.find((row) => row.specific_date === iso);
    const row = override || hours.weekly.find((w) => w.day_of_week === fromIsoDate(iso).getDay());
    if (!row || row.is_closed) continue;
    // Skip today once its last two-hour arrival window has started.
    if (offset === 0 && row.opens_at && row.closes_at) {
      const toMin = (hhmm) => hhmm.split(':').map(Number).reduce((h, m) => h * 60 + m);
      const open = toMin(row.opens_at);
      const lastStart = open + (Math.floor((toMin(row.closes_at) - open) / 120) - 1) * 120;
      const now = new Date();
      if (now.getHours() * 60 + now.getMinutes() >= lastStart) continue;
    }
    days.push(iso);
  }
  return days;
}

const chipLabel = (iso) => {
  if (iso === isoDateFromToday(0)) return 'Today';
  if (iso === isoDateFromToday(1)) return 'Tomorrow';
  return fromIsoDate(iso).toLocaleDateString('en-AU', { weekday: 'short', day: 'numeric', month: 'short' });
};

/**
 * Book tickets — step 1 of 3: date, arrival window and tickets.
 *
 * Open to everyone. Continuing to step 2 needs an account (the contract gates
 * booking at Member), so the choice is saved as a draft first and survives
 * the trip through sign-in.
 */
export default function TicketBookingPage() {
  const navigate = useNavigate();
  const { user, ready } = useAuth();
  const [draft] = useState(loadDraft); // read once on arrival

  const hours = useAsync(getOpeningHours, []);
  const openDays = useMemo(() => upcomingOpenDays(hours.data), [hours.data]);

  const [pickedDate, setPickedDate] = useState(draft?.visit_date || null);
  // Until the visitor picks one, default to the first open day.
  const date = pickedDate || openDays[0] || null;

  const [windowStart, setWindowStart] = useState(draft?.arrival_window?.start || null);
  const [quantities, setQuantities] = useState(() =>
    Object.fromEntries((draft?.lines || []).map((line) => [line.ticket_type_id, line.quantity]))
  );
  const [errors, setErrors] = useState({});

  const availability = useAsync(
    () => (date ? getAvailability(date) : Promise.resolve(null)),
    [date]
  );
  const types = useAsync(
    () => (ready ? listTicketTypes(user) : new Promise(() => {})),
    [ready, user?.id]
  );

  const windows = availability.data?.windows || [];
  const chosenWindow = windows.find((w) => w.start === windowStart && w.places_left > 0) || null;
  const typeList = types.data?.items || [];
  const maxPerBooking = types.data?.max_per_booking || 10;

  // Drop quantities for ticket types this account cannot buy (e.g. signed out
  // after choosing Member tickets).
  const lines = typeList
    .map((type) => ({
      ticket_type_id: type.id,
      name: type.name,
      quantity: Math.min(quantities[type.id] || 0, type.max_quantity),
      unit_price_cents: type.price_cents,
    }))
    .filter((line) => line.quantity > 0);
  const ticketCount = lines.reduce((sum, line) => sum + line.quantity, 0);
  const total = lines.reduce((sum, line) => sum + line.quantity * line.unit_price_cents, 0);

  function pickDate(iso) {
    setPickedDate(iso);
    setErrors({});
  }

  function handleContinue() {
    const next = {};
    if (!date) next.date = 'Choose the day you would like to visit.';
    if (!chosenWindow) next.window = 'Choose an arrival time.';
    if (ticketCount === 0) next.tickets = 'Add at least one ticket.';
    if (chosenWindow && ticketCount > chosenWindow.places_left) {
      next.tickets = `Only ${chosenWindow.places_left} places are left at ${chosenWindow.start}. Choose another time or fewer tickets.`;
    }
    setErrors(next);
    if (Object.keys(next).length) return;

    saveDraft({
      visit_date: date,
      arrival_window: { start: chosenWindow.start, end: chosenWindow.end },
      lines,
    });
    navigate('/book/details');
  }

  return (
    <div>
      <h1>Book tickets</h1>
      <p style={{ color: 'var(--c-muted)' }}>
        General admission covers all four galleries. Choose a day and an arrival time — you can
        stay until closing.
      </p>

      <BookingSteps current={1} />
      <div className={styles.panel}>
        <div className={styles.main}>
          {/* ---------------- date ---------------- */}
          <section className={styles.section}>
            <h2 className={styles.sectionTitle}>When are you visiting?</h2>
            <p className={styles.sectionHint}>Bookings open {BOOKING_HORIZON_DAYS} days ahead.</p>

            <div className={styles.dateRow}>
              <div className="field">
                <label htmlFor="visit-date">Date</label>
                <input
                  id="visit-date"
                  type="date"
                  className={`control ${errors.date ? 'control--error' : ''}`}
                  min={isoDateFromToday(0)}
                  max={isoDateFromToday(BOOKING_HORIZON_DAYS)}
                  value={date || ''}
                  onChange={(event) => event.target.value && pickDate(event.target.value)}
                />
              </div>
              <div className={styles.quickDates} aria-label="Next open days">
                {hours.loading && <Skeleton height={32} width={320} />}
                {openDays.map((iso) => (
                  <Button
                    key={iso}
                    size="sm"
                    variant={iso === date ? 'primary' : 'ghost'}
                    aria-pressed={iso === date}
                    onClick={() => pickDate(iso)}
                  >
                    {chipLabel(iso)}
                  </Button>
                ))}
              </div>
            </div>
          </section>

          {/* ---------------- arrival window ---------------- */}
          <section className={styles.section}>
            <h2 className={styles.sectionTitle}>Arrival time</h2>
            <p className={styles.sectionHint}>
              {date ? formatCalendarDate(date) : 'Choose a date first.'}
              {availability.data?.opens_at &&
                !availability.data.is_closed &&
                ` · open ${availability.data.opens_at}–${availability.data.closes_at}`}
            </p>

            {availability.loading && (
              <div className={styles.windows}>
                {[0, 1, 2].map((n) => <Skeleton key={n} height={58} />)}
              </div>
            )}

            {availability.error && (
              <EmptyState title="We could not load arrival times" body={availability.error.message}>
                <Button variant="ghost" onClick={availability.reload}>Try again</Button>
              </EmptyState>
            )}

            {!availability.loading && availability.data?.is_closed && (
              <div className={styles.closed}>
                <strong style={{ color: 'var(--c-ink)' }}>No arrival times on this day.</strong>{' '}
                {availability.data.note || 'The museum is closed.'}{' '}
                {openDays[0] && openDays[0] !== date && (
                  <div style={{ marginTop: 'var(--s-3)' }}>
                    <Button size="sm" variant="ghost" onClick={() => pickDate(openDays[0])}>
                      Next open day: {formatCalendarDate(openDays[0])}
                    </Button>
                  </div>
                )}
              </div>
            )}

            {!availability.loading && windows.length > 0 && (
              <fieldset className={styles.windows}>
                <legend className="visually-hidden">Arrival time</legend>
                {windows.map((w) => {
                  const full = w.places_left === 0;
                  const selected = chosenWindow?.start === w.start;
                  const low = !full && w.places_left <= 15;
                  return (
                    <label
                      key={w.start}
                      className={[
                        styles.window,
                        selected ? styles.windowSelected : '',
                        full ? styles.windowFull : '',
                      ].join(' ')}
                    >
                      <input
                        type="radio"
                        name="arrival"
                        value={w.start}
                        checked={selected}
                        disabled={full}
                        onChange={() => {
                          setWindowStart(w.start);
                          setErrors((prev) => ({ ...prev, window: undefined }));
                        }}
                      />
                      <span>
                        {w.start} – {w.end}
                        <span className={`${styles.windowMeta} ${low ? styles.windowLow : ''}`}>
                          {full ? 'Fully booked' : `${w.places_left} places left`}
                        </span>
                      </span>
                    </label>
                  );
                })}
              </fieldset>
            )}
            {errors.window && <div className="error-text">{errors.window}</div>}
          </section>

          {/* ---------------- tickets ---------------- */}
          <section className={styles.section}>
            <h2 className={styles.sectionTitle}>Tickets</h2>
            <p className={styles.sectionHint}>
              {user && typeList.some((t) => t.members_only) ? (
                <>
                  <Pill tone="lime">Member</Pill> Your membership tickets are free.
                </>
              ) : (
                <>
                  Members visit free.{' '}
                  {user ? <Link to="/membership">See membership</Link> : <Link to="/signin" state={{ from: '/book' }}>Sign in</Link>}{' '}
                  to use member tickets.
                </>
              )}
            </p>

            {types.loading ? (
              <div className={styles.tickets}>
                {[0, 1, 2].map((n) => <Skeleton key={n} height={62} />)}
              </div>
            ) : types.error ? (
              <EmptyState title="We could not load ticket prices" body={types.error.message}>
                <Button variant="ghost" onClick={types.reload}>Try again</Button>
              </EmptyState>
            ) : (
              <TicketSelector
                types={typeList}
                quantities={quantities}
                maxPerBooking={maxPerBooking}
                onChange={(next) => {
                  setQuantities(next);
                  setErrors((prev) => ({ ...prev, tickets: undefined }));
                }}
              />
            )}
            {errors.tickets && <div className="error-text">{errors.tickets}</div>}
          </section>

          <div style={{ marginTop: 'var(--s-5)' }}>
            <FormErrorSummary errors={Object.fromEntries(Object.entries(errors).filter(([, v]) => v))} />
          </div>
        </div>

        <div className={styles.footerBar}>
          <div>
            <div className={styles.totalLabel}>
              Total{ticketCount > 0 && ` · ${ticketCount} ${ticketCount === 1 ? 'ticket' : 'tickets'}`}
            </div>
            <div className={styles.totalValue}>{formatPrice(total)}</div>
          </div>
          <Button onClick={handleContinue}>
            {user ? 'Continue' : 'Continue — sign in to book'}
          </Button>
        </div>
      </div>
    </div>
  );
}
