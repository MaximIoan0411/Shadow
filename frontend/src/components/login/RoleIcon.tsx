/**
 * Icoanele de rol ale echipajului, pentru ecranul de intrare: comandant, specialist de misiune, ofițer medical
 * și inginer de zbor; medicul de zbor de pe Pământ folosește crucea ofițerului medical. Desenele sunt ale echipei (originalele: `docs/design/icons`); aici sunt aceleași trasee,
 * cu linia în culoarea textului curent, ca să se poată schimba după starea casetei.
 */
import type { ReactElement } from "react";

const ICONS = {
  // steaua și cele două trese
  comandant: (
    <>
      <path d="M12 2.4L13.03 5.18L15.99 5.3L13.66 7.14L14.47 10L12 8.35L9.53 10L10.34 7.14L8.01 5.3L10.97 5.18Z" />
      <path d="M5 13.5L12 17L19 13.5" />
      <path d="M5 18L12 21.5L19 18" />
    </>
  ),
  // planeta cu orbita ei
  specialist2: (
    <>
      <circle cx="12" cy="12" r="6" />
      <path d="M2.04 15.63A10.6 3.8 -20 0 0 21.96 8.37" />
      <circle cx="20" cy="4" r="1.2" fill="currentColor" stroke="none" />
    </>
  ),
  // crucea medicală cu pulsul
  medic: (
    <>
      <path d="M9 3.5H15V9H20.5V15H15V20.5H9V15H3.5V9H9Z" />
      <path d="M6.5 12H9.5L10.75 9.75L12.75 14.25L14 12H17.5" />
    </>
  ),
  // roata dințată
  inginer: (
    <>
      <path d="M19.05 10.11L21.51 10.66L21.51 13.34L19.05 13.89L18.32 15.65L19.67 17.78L17.78 19.67L15.65 18.32L13.89 19.05L13.34 21.51L10.66 21.51L10.11 19.05L8.35 18.32L6.22 19.67L4.33 17.78L5.68 15.65L4.95 13.89L2.49 13.34L2.49 10.66L4.95 10.11L5.68 8.35L4.33 6.22L6.22 4.33L8.35 5.68L10.11 4.95L10.66 2.49L13.34 2.49L13.89 4.95L15.65 5.68L17.78 4.33L19.67 6.22L18.32 8.35Z" />
      <circle cx="12" cy="12" r="3" />
    </>
  ),
} as const satisfies Record<string, ReactElement>;

/** Conturile care folosesc icoana altui rol: medicul de zbor de pe Pământ are crucea medicală, ca ofițerul medical. */
const SHARED = { earth: "medic" } as const satisfies Record<string, keyof typeof ICONS>;

type IconName = keyof typeof ICONS;

const DEFAULT_SIZE = 22;

const isIconName = (username: string): username is IconName => username in ICONS;
const isShared = (username: string): username is keyof typeof SHARED => username in SHARED;

/** Numele icoanei unui cont: a lui, sau cea împrumutată de la alt rol; `null` dacă nu are. */
function iconFor(username: string): IconName | null {
  if (isIconName(username)) return username;
  return isShared(username) ? SHARED[username] : null;
}

/** Are contul acesta o icoană de rol? */
export const hasRoleIcon = (username: string): boolean => iconFor(username) !== null;

/** Icoana de rol a unui cont, după numele lui de utilizator; `null` dacă nu are una. */
export function RoleIcon({ username, size = DEFAULT_SIZE }: { readonly username: string; readonly size?: number }): ReactElement | null {
  const icon = iconFor(username);
  if (!icon) return null;
  return (
    <svg viewBox="0 0 24 24" width={size} height={size} fill="none" stroke="currentColor" strokeWidth="1.75" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
      {ICONS[icon]}
    </svg>
  );
}
