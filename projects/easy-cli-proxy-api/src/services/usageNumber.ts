const MILLION = 1_000_000;
const BILLION = 1_000_000_000;

export const formatUsageNumber = (value: number, locale: string) => {
  const amount = Number.isFinite(value) ? value : 0;
  const absolute = Math.abs(amount);
  const roundedMillions = Math.round((absolute / MILLION) * 10) / 10;
  const useBillions = absolute >= BILLION || roundedMillions >= 1_000;
  const divisor = useBillions ? BILLION : absolute >= MILLION ? MILLION : 1;
  const unit = useBillions ? 'B' : absolute >= MILLION ? 'M' : '';
  const formatted = new Intl.NumberFormat(locale, {
    maximumFractionDigits: divisor === 1 ? 0 : 1,
  }).format(amount / divisor);

  return `${formatted}${unit}`;
};
