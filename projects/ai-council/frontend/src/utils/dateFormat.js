export const DATE_FORMAT_OPTIONS = {
  auto: undefined,
  'MM/DD/YYYY': { year: 'numeric', month: '2-digit', day: '2-digit' },
  'DD/MM/YYYY': { year: 'numeric', month: '2-digit', day: '2-digit' },
  'YYYY-MM-DD': { year: 'numeric', month: '2-digit', day: '2-digit' },
};

export const DATE_FORMAT_LOCALES = {
  auto: undefined,
  'MM/DD/YYYY': 'en-US',
  'DD/MM/YYYY': 'en-GB',
  'YYYY-MM-DD': 'sv-SE',
};

export function formatDatePart(date, dateFormat) {
  const d = date instanceof Date ? date : new Date(date);
  const locale = DATE_FORMAT_LOCALES[dateFormat] || undefined;
  const opts = DATE_FORMAT_OPTIONS[dateFormat] || undefined;
  return d.toLocaleDateString(locale, opts);
}

export function formatTimePart(isoString, dateFormat) {
  const d = new Date(isoString);
  const locale = DATE_FORMAT_LOCALES[dateFormat] || undefined;
  return d.toLocaleTimeString(locale, { hour: 'numeric', minute: '2-digit' });
}

export function formatTimestamp(isoString, dateFormat) {
  const datePart = formatDatePart(isoString, dateFormat);
  const timePart = formatTimePart(isoString, dateFormat);
  return `${datePart} ${timePart}`;
}
