/**
 * Formatarea valorilor pentru afișare. Toate momentele vin în TIMPUL MISIUNII (UTC); nu se convertesc la fusul
 * orar al calculatorului, altfel ora de pe navă ar depinde de unde rulează demo-ul.
 */

const LOCALE = "en-GB";
const MISSION_TIME_ZONE = "UTC";
const SECONDS_PER_MINUTE = 60;
const MINUTES_PER_HOUR = 60;
const ONE_DECIMAL = 1;
const TWO_DECIMALS = 2;
const PERCENT = 100;
const DASH = "—";

const timeFormat = new Intl.DateTimeFormat(LOCALE, { hour: "2-digit", minute: "2-digit", timeZone: MISSION_TIME_ZONE });
const dateFormat = new Intl.DateTimeFormat(LOCALE, { day: "numeric", month: "short", timeZone: MISSION_TIME_ZONE });
const fullFormat = new Intl.DateTimeFormat(LOCALE, { day: "numeric", month: "long", year: "numeric", hour: "2-digit", minute: "2-digit", timeZone: MISSION_TIME_ZONE });
const numberFormats: ReadonlyMap<number, Intl.NumberFormat> = new Map(
  [0, ONE_DECIMAL, TWO_DECIMALS].map((digits) => [digits, new Intl.NumberFormat(LOCALE, { maximumFractionDigits: digits })]),
);

/** "07:42" — ora misiunii. */
export function formatTime(iso: string | null | undefined): string {
  return iso ? timeFormat.format(new Date(iso)) : DASH;
}

/** „15 apr.” — data misiunii. */
export function formatDate(iso: string | null | undefined): string {
  return iso ? dateFormat.format(new Date(iso)) : DASH;
}

/** „15 apr., 07:42”. */
export function formatDateTime(iso: string | null | undefined): string {
  return iso ? `${formatDate(iso)}, ${formatTime(iso)}` : DASH;
}

/** „11 mai 2024, 02:10 UTC” — pentru momente reale, din afara misiunii (evenimentul NASA DONKI). */
export function formatFullDateTime(iso: string | null | undefined): string {
  return iso ? `${fullFormat.format(new Date(iso))} UTC` : DASH;
}

/** Număr cu punct zecimal (interfața e în engleză); `null` devine „—”. */
export function formatNumber(value: number | null | undefined, digits: number = ONE_DECIMAL): string {
  if (value === null || value === undefined) return DASH;
  return (numberFormats.get(digits) ?? numberFormats.get(ONE_DECIMAL))?.format(value) ?? String(value);
}

/** Număr cu semn explicit: „+7”, „−1,1”, „0”. */
export function formatSigned(value: number | null | undefined, digits: number = ONE_DECIMAL): string {
  if (value === null || value === undefined) return DASH;
  const body = formatNumber(Math.abs(value), digits);
  if (value > 0) return `+${body}`;
  return value < 0 ? `−${body}` : body;
}

/** Durată în secunde, pe scurt: „11 min 40 s”, „1 h 5 min”, „12 s”. */
export function formatDuration(totalSeconds: number | null | undefined): string {
  if (totalSeconds === null || totalSeconds === undefined) return DASH;
  const seconds = Math.max(0, Math.round(totalSeconds));
  const minutes = Math.floor(seconds / SECONDS_PER_MINUTE);
  const hours = Math.floor(minutes / MINUTES_PER_HOUR);
  if (hours) return `${hours} h ${minutes % MINUTES_PER_HOUR} min`;
  if (minutes) return `${minutes} min ${seconds % SECONDS_PER_MINUTE} s`;
  return `${seconds} s`;
}

/** Fracție 0–1 ca procent întreg: 0,72 → „72%”. */
export function formatPercent(fraction: number | null | undefined): string {
  if (fraction === null || fraction === undefined) return DASH;
  return `${Math.round(fraction * PERCENT)}%`;
}

/** Limitează o valoare într-un interval. */
export function clamp(value: number, min: number, max: number): number {
  return Math.min(max, Math.max(min, value));
}

/** Poziția unei valori într-un interval, ca procent 0–100 (pentru lățimi și poziții în CSS). */
export function toPercent(value: number, min: number, max: number): number {
  if (max === min) return 0;
  return clamp(((value - min) / (max - min)) * PERCENT, 0, PERCENT);
}
