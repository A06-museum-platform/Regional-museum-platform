import { toIsoDate } from './date';

const DAY_NAMES = ['Sunday', 'Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday'];

/**
 * The hours that apply on one date: a dated exception (public holiday,
 * special late night) wins over the weekly pattern. `hours` is the
 * { weekly, overrides } object from GET /opening-hours.
 */
export function hoursOn(date, hours) {
  const iso = toIsoDate(date);
  const override = hours.overrides.find((row) => row.specific_date === iso);
  if (override) return { ...override, isException: true };
  const weekly = hours.weekly.find((row) => row.day_of_week === date.getDay());
  return weekly
    ? { ...weekly, isException: false }
    : { is_closed: true, opens_at: null, closes_at: null, note: '', isException: false };
}

/** "Open today 09:00–17:00", "Closed today · opens Monday 09:00", ... */
export function openingStatus(hours, now = new Date()) {
  const today = hoursOn(now, hours);
  const hhmm = `${String(now.getHours()).padStart(2, '0')}:${String(now.getMinutes()).padStart(2, '0')}`;
  if (!today.is_closed && hhmm < today.closes_at) {
    return {
      open: hhmm >= today.opens_at,
      label: hhmm >= today.opens_at
        ? `Open now · until ${today.closes_at}`
        : `Opens today at ${today.opens_at}`,
      note: today.note,
    };
  }
  for (let i = 1; i <= 14; i += 1) {
    const day = new Date(now);
    day.setDate(now.getDate() + i);
    const next = hoursOn(day, hours);
    if (!next.is_closed) {
      const when = i === 1 ? 'tomorrow' : DAY_NAMES[day.getDay()];
      return {
        open: false,
        label: `Closed ${today.is_closed ? 'today' : 'now'} · opens ${when} at ${next.opens_at}`,
        note: today.note,
      };
    }
  }
  return { open: false, label: 'Closed', note: today.note };
}

export const dayName = (dayOfWeek) => DAY_NAMES[dayOfWeek];
