/**
 * All dates are formatted for an Australian audience in one place. Do not
 * call toLocaleDateString directly in a page — the day/month order silently
 * flips depending on the browser locale, which is a nasty thing to discover
 * during a client demonstration.
 */

const AU = 'en-AU';

export const formatDate = (iso) =>
  new Date(iso).toLocaleDateString(AU, {
    weekday: 'long',
    day: 'numeric',
    month: 'long',
    year: 'numeric',
  });

export const formatDateShort = (iso) =>
  new Date(iso).toLocaleDateString(AU, { day: 'numeric', month: 'short' });

export const formatWeekday = (iso) =>
  new Date(iso).toLocaleDateString(AU, { weekday: 'short' });

export const formatTime = (iso) =>
  new Date(iso).toLocaleTimeString(AU, { hour: '2-digit', minute: '2-digit', hour12: false });

export const formatTimeRange = (startIso, endIso) =>
  `${formatTime(startIso)} – ${formatTime(endIso)}`;

/** Start of today, local time. Used to hide events that have already run. */
export const startOfToday = () => {
  const now = new Date();
  now.setHours(0, 0, 0, 0);
  return now;
};

/** Saturday and Sunday of the coming weekend, as ISO date strings. */
export const comingWeekend = () => {
  const start = startOfToday();
  const daysUntilSaturday = (6 - start.getDay() + 7) % 7;
  const saturday = new Date(start);
  saturday.setDate(start.getDate() + daysUntilSaturday);
  const sunday = new Date(saturday);
  sunday.setDate(saturday.getDate() + 1);
  sunday.setHours(23, 59, 59, 999);
  return { from: saturday.toISOString(), to: sunday.toISOString() };
};
