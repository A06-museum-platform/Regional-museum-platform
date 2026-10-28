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

/*
 * Calendar dates (a visit day, with no time attached) travel as plain
 * 'YYYY-MM-DD' strings. `new Date('2026-10-18')` parses that as UTC midnight,
 * which is the previous evening anywhere west of Greenwich — so build them
 * from parts, in local time, instead.
 */

/** Date object -> 'YYYY-MM-DD' in local time. */
export const toIsoDate = (date) => {
  const pad = (n) => String(n).padStart(2, '0');
  return `${date.getFullYear()}-${pad(date.getMonth() + 1)}-${pad(date.getDate())}`;
};

/** 'YYYY-MM-DD' -> Date at local midnight. */
export const fromIsoDate = (isoDate) => {
  const [year, month, day] = isoDate.split('-').map(Number);
  return new Date(year, month - 1, day);
};

/** 'YYYY-MM-DD' -> 'Saturday 24 October 2026'. */
export const formatCalendarDate = (isoDate) =>
  fromIsoDate(isoDate).toLocaleDateString(AU, {
    weekday: 'long',
    day: 'numeric',
    month: 'long',
    year: 'numeric',
  });

/** Today plus `days`, as 'YYYY-MM-DD'. */
export const isoDateFromToday = (days = 0) => {
  const date = startOfToday();
  date.setDate(date.getDate() + days);
  return toIsoDate(date);
};
