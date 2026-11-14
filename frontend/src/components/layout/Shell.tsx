"use client";
/**
 * Cadrul aplicației, după Quaternion (src/components/Chrome.tsx): bara laterală cu ecranele, antetul fiecărui ecran
 * și lumina de fundal. Fără ce ține de Electron (zona de tragere, butoanele ferestrei).
 *
 * Diferențe SHADOW:
 *  - jos în bara laterală stă contul autentificat (nume + inițiale, mereu vizibil) și „Schimbă astronautul”;
 *  - antetul arată ceasul misiunii, ziua, mediul și întârzierea legăturii cu Pământul;
 *  - ecranul „Coada ofițerului medical” apare doar pentru rolul `cmo`.
 */
import { Activity, ClipboardCheck, Gauge, LogOut, PanelLeft, Radio, ShieldCheck, Stethoscope, Timer } from "lucide-react";
import type { CSSProperties, ReactElement, ReactNode } from "react";
import { SCREEN_HUES, hueStyle, type Screen } from "@/lib/hues";
import { Dot, IconButton, Tip, cx } from "@/components/ui";

// ---------------------------------------------------------------- lumina de fundal

/** Aurora + rețeaua de puncte. Se pune ca prim copil al unui container `relative`. */
export function Backdrop({ live = false, stars = true }: { readonly live?: boolean; readonly stars?: boolean }): ReactElement {
  return (
    <>
      <div className="aurora" data-live={live ? "true" : "false"}>
        <i />
      </div>
      {stars && <div className="starfield" />}
    </>
  );
}

/** Rădăcina unui ecran: nuanțele lui, fundalul viu și conținutul deasupra. */
export function Screen({ screen, live, children, className }: { readonly screen: Screen; readonly live?: boolean; readonly children: ReactNode; readonly className?: string }): ReactElement {
  return (
    <div className={cx("relative flex h-full min-w-0 flex-col", className)} style={hueStyle(screen)}>
      <Backdrop live={live} />
      <div className="relative z-10 flex min-h-0 flex-1 flex-col">{children}</div>
    </div>
  );
}

// ---------------------------------------------------------------- bara laterală

export type NavItem = { readonly screen: Screen; readonly label: string; readonly href: string; readonly icon: typeof Activity };

export const SHIP_NAV: readonly NavItem[] = [
  { screen: "dashboard", label: "Corpul meu", href: "/dashboard", icon: Activity },
  { screen: "checkin", label: "Check-in", href: "/checkin", icon: ClipboardCheck },
  { screen: "pvt", label: "Test de reacție", href: "/pvt", icon: Timer },
  { screen: "alerts", label: "Alerte", href: "/alerts", icon: Gauge },
  { screen: "evidence", label: "Dovezi", href: "/evidence", icon: ShieldCheck },
];
export const CMO_NAV: NavItem = { screen: "cmo", label: "Coada medicală", href: "/cmo", icon: Stethoscope };

export type Account = { readonly displayName: string; readonly initials: string; readonly roleLabel: string };

export function Sidebar({
  active,
  items,
  account,
  collapsed,
  onToggle,
  onNavigate,
  onSwitchAccount,
}: {
  readonly active: Screen;
  readonly items: readonly NavItem[];
  readonly account: Account;
  readonly collapsed: boolean;
  readonly onToggle: () => void;
  readonly onNavigate: (item: NavItem) => void;
  readonly onSwitchAccount: () => void;
}): ReactElement {
  if (collapsed) {
    return (
      <aside className="sidebar-q flex w-[64px] shrink-0 flex-col items-center gap-1 py-3">
        <IconButton label="Arată meniul" onClick={onToggle}>
          <PanelLeft size={17} strokeWidth={1.8} />
        </IconButton>
        <div className="my-2 h-px w-6 bg-line" />
        {items.map((n) => (
          <Tip key={n.screen} label={n.label} side="right">
            <IconButton label={n.label} active={active === n.screen} onClick={() => onNavigate(n)}>
              <n.icon size={17} strokeWidth={1.8} style={active === n.screen ? { color: SCREEN_HUES[n.screen].a } : undefined} />
            </IconButton>
          </Tip>
        ))}
        <span className="flex-1" />
        <Tip label={`${account.displayName} · schimbă astronautul`} side="right">
          <button
            type="button"
            onClick={onSwitchAccount}
            aria-label={`${account.displayName}. Schimbă astronautul`}
            className="grid size-9 place-items-center rounded-full bg-surface-4 text-[12px] font-semibold text-fg"
          >
            {account.initials}
          </button>
        </Tip>
      </aside>
    );
  }
  return (
    <aside className="sidebar-q flex w-[248px] shrink-0 flex-col">
      <div className="flex h-[52px] shrink-0 items-center gap-2.5 pl-4 pr-2.5">
        <span className="num text-[13px] font-semibold tracking-[0.32em] text-fg">SHADOW</span>
        <span className="flex-1" />
        <IconButton label="Ascunde meniul" size="sm" onClick={onToggle}>
          <PanelLeft size={16} strokeWidth={1.8} />
        </IconButton>
      </div>

      <nav aria-label="Ecrane" className="flex flex-col gap-0.5 px-3 pt-3">
        {items.map((n) => {
          const on = active === n.screen;
          return (
            <button
              key={n.screen}
              type="button"
              onClick={() => onNavigate(n)}
              aria-current={on ? "page" : undefined}
              data-active={on || undefined}
              style={{ "--nav-hue": SCREEN_HUES[n.screen].a } as CSSProperties}
              className={cx("nav-q flex h-9 w-full items-center gap-3 rounded-xl px-3 text-[13.5px] transition-colors", on ? "text-fg" : "text-fg-2 hover:bg-white/[0.04] hover:text-fg")}
            >
              <n.icon size={16} strokeWidth={1.8} className={cx("shrink-0 transition-colors", on ? "text-[var(--nav-hue)]" : "text-fg-3")} />
              <span className="font-medium">{n.label}</span>
            </button>
          );
        })}
      </nav>

      <span className="flex-1" />

      <div className="p-3">
        <div className="flex items-center gap-3 rounded-xl border border-line px-3 py-2.5">
          <span className="grid size-8 shrink-0 place-items-center rounded-full bg-surface-4 text-[12px] font-semibold text-fg">{account.initials}</span>
          <span className="min-w-0 flex-1">
            <span className="block truncate text-[13px] font-medium text-fg">{account.displayName}</span>
            <span className="block truncate text-[11.5px] text-fg-4">{account.roleLabel}</span>
          </span>
          <Tip label="Schimbă astronautul">
            <IconButton label="Schimbă astronautul" size="sm" onClick={onSwitchAccount}>
              <LogOut size={15} strokeWidth={1.8} />
            </IconButton>
          </Tip>
        </div>
      </div>
    </aside>
  );
}

// ---------------------------------------------------------------- antetul

export type MissionInfo = {
  /** Ex. „Ziua 96 · 07:42” — formatat din MissionState.sim_now / mission_day. */
  readonly clock: string;
  /** EnvironmentInfo.name, ex. „Tranzit spre Marte”. */
  readonly environment: string;
  /** Ex. „11 min 40 s” — din LinkStatus.one_way_delay_s. */
  readonly delay: string;
  readonly linkOpen: boolean;
};

/** Antetul unui ecran: titlul în stânga, starea misiunii și uneltele ecranului în dreapta. */
export function Header({ title, mission, right }: { readonly title: ReactNode; readonly mission?: MissionInfo; readonly right?: ReactNode }): ReactElement {
  return (
    <header className="relative z-20 flex h-[52px] shrink-0 items-center gap-4 px-5">
      <h1 className="truncate text-[13.5px] font-medium text-fg">{title}</h1>
      <span className="flex-1" />
      {mission && (
        <div className="hidden items-center gap-3 text-[12.5px] text-fg-3 md:flex">
          <span className="num text-fg-2">{mission.clock}</span>
          <span className="text-fg-5">/</span>
          <span>{mission.environment}</span>
          <span className="text-fg-5">/</span>
          <Tip label={mission.linkOpen ? "Fereastra de comunicare e deschisă" : "Fereastra de comunicare e închisă"}>
            <span className="inline-flex items-center gap-2">
              <Radio size={13} strokeWidth={1.9} />
              <span className="num">{mission.delay}</span>
              <Dot hue={mission.linkOpen ? "var(--color-status-ok)" : "var(--color-status-watch)"} />
            </span>
          </Tip>
        </div>
      )}
      <div className="flex items-center gap-1">{right}</div>
    </header>
  );
}
