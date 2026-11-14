"use client";
/**
 * Cadrul aplicației: fundalul, bara laterală cu ecranele și contul, antetul cu starea misiunii.
 * În aplicația de desktop antetul ține loc de bară de titlu (de el se trage fereastra).
 */
import {
  Activity,
  Bell,
  ClipboardCheck,
  Dumbbell,
  FlaskConical,
  Keyboard,
  LogOut,
  MessageCircleQuestion,
  PanelLeft,
  Radiation,
  Radio,
  SatelliteDish,
  ShieldCheck,
  Stethoscope,
  type LucideIcon,
} from "lucide-react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import type { ReactElement, ReactNode } from "react";
import { IconButton, StatusMark, Tag, Tip, cx } from "@/components/ui";
import { Select } from "@/components/ui/Select";
import type { Schemas } from "@/lib/api";
import { formatDuration, formatTime } from "@/lib/format";
import { ROLE_LABEL } from "@/lib/status";

type Role = Schemas["Role"];

// ---------------------------------------------------------------- fundal și logo

/** Rețeaua de puncte și lumina de sus. `alert` = lumina devine roșie (doar în timpul unei alerte de radiații). */
export function Backdrop({ alert = false }: { readonly alert?: boolean }): ReactElement {
  return <div aria-hidden="true" className="backdrop" data-tone={alert ? "alert" : "calm"} />;
}

/** Semnul SHADOW (din logo) și numele. Singurul loc din cadru unde apare portocaliul. */
export function Brand({ compact }: { readonly compact?: boolean }): ReactElement {
  return (
    <span className="flex items-center gap-2.5">
      {/* eslint-disable-next-line @next/next/no-img-element -- imagine locală, exportul static nu optimizează imagini */}
      <img src="/brand/mark-96.png" srcSet="/brand/mark-96.png 1x, /brand/mark-192.png 2x" alt="" width={55} height={32} className="h-8 w-auto" />
      {!compact && <span className="code text-body font-semibold tracking-[0.32em] text-fg">SHADOW</span>}
    </span>
  );
}

// ---------------------------------------------------------------- bara laterală

export interface NavItem {
  readonly href: string;
  readonly label: string;
  readonly icon: LucideIcon;
  /** Număr mic lângă etichetă (alertele deschise). */
  readonly count?: number;
  /** Starea de arătat lângă număr; fără ea, numărul e neutru. */
  readonly countStatus?: Schemas["Status"];
}

const SHIP_NAV: readonly NavItem[] = [
  { href: "/dashboard", label: "My body", icon: Activity },
  { href: "/checkin", label: "Check-in", icon: ClipboardCheck },
  { href: "/rhythm", label: "Rhythm and reaction", icon: Keyboard },
  { href: "/exercise", label: "Exercise", icon: Dumbbell },
  { href: "/alerts", label: "Alerts", icon: Bell },
  { href: "/ai", label: "AI doctor", icon: MessageCircleQuestion },
  { href: "/radiation", label: "Radiation", icon: Radiation },
  { href: "/evidence", label: "Evidence", icon: ShieldCheck },
];
const CMO_NAV: NavItem = { href: "/cmo", label: "Medical queue", icon: Stethoscope };
const EARTH_NAV: readonly NavItem[] = [
  { href: "/mission-control", label: "Link with the ship", icon: SatelliteDish },
  { href: "/mission-control/evidence", label: "Evidence", icon: ShieldCheck },
];

const NAV_BY_ROLE = {
  astronaut: SHIP_NAV,
  cmo: [CMO_NAV, ...SHIP_NAV],
  earth: EARTH_NAV,
} as const satisfies Record<Role, readonly NavItem[]>;

/** Ecranele din meniu pentru un rol, cu numărul de alerte pus pe „Alerte”. */
export function navFor(role: Role, alerts?: { readonly count: number; readonly status: Schemas["Status"] }): readonly NavItem[] {
  return NAV_BY_ROLE[role].map((item) =>
    item.href === "/alerts" && alerts?.count ? { ...item, count: alerts.count, countStatus: alerts.status } : item,
  );
}

export interface Account {
  readonly displayName: string;
  readonly initials: string;
  readonly role: Role;
}

const isActive = (pathname: string, href: string): boolean => pathname === href || pathname === `${href}/`;

export function Sidebar({
  items,
  account,
  collapsed,
  onToggle,
  onSwitchAccount,
}: {
  readonly items: readonly NavItem[];
  readonly account: Account;
  readonly collapsed: boolean;
  readonly onToggle: () => void;
  readonly onSwitchAccount: () => void;
}): ReactElement {
  const pathname = usePathname();
  return (
    <aside className={cx("sidebar-q flex shrink-0 flex-col transition-[width] duration-200 ease-[var(--ease-out)]", collapsed ? "w-[64px] items-center" : "w-[248px]")}>
      <div className={cx("app-drag flex h-[52px] shrink-0 items-center", collapsed ? "justify-center" : "gap-2 pl-4 pr-2.5")}>
        {!collapsed && <Brand />}
        {!collapsed && <span className="flex-1" />}
        <IconButton label={collapsed ? "Show menu" : "Hide menu"} size="sm" onClick={onToggle} className="app-no-drag">
          <PanelLeft size={16} strokeWidth={1.8} />
        </IconButton>
      </div>

      <nav aria-label="Screens" className={cx("flex flex-col gap-0.5 pt-3", collapsed ? "items-center" : "px-3")}>
        {items.map((item) => {
          const on = isActive(pathname, item.href);
          const link = (
            <Link
              key={item.href}
              href={item.href}
              aria-current={on ? "page" : undefined}
              aria-label={collapsed ? item.label : undefined}
              className={cx(
                "flex h-9 items-center rounded-xl text-body no-underline transition-colors",
                collapsed ? "w-9 justify-center" : "w-full gap-3 px-3",
                on ? "bg-white/[0.08] text-fg" : "text-fg-3 hover:bg-white/[0.04] hover:text-fg",
              )}
            >
              <item.icon size={16} strokeWidth={1.8} className="shrink-0" />
              {!collapsed && <span className="flex-1 font-medium">{item.label}</span>}
              {!collapsed && item.count !== undefined && (
                <span className="flex items-center gap-1.5 text-small text-fg-2">
                  {item.countStatus && <StatusMark status={item.countStatus} />}
                  <span className="num">{item.count}</span>
                </span>
              )}
            </Link>
          );
          return collapsed ? (
            <Tip key={item.href} label={item.count ? `${item.label} (${item.count})` : item.label} side="right">
              {link}
            </Tip>
          ) : (
            link
          );
        })}
      </nav>

      <span className="flex-1" />

      <div className={cx("p-3", collapsed && "px-0")}>
        {collapsed ? (
          <Tip label={`${account.displayName}: switch account`} side="right">
            <button
              type="button"
              onClick={onSwitchAccount}
              aria-label={`${account.displayName}. Switch account`}
              className="grid size-9 place-items-center rounded-full bg-surface-4 text-small font-semibold text-fg"
            >
              {account.initials}
            </button>
          </Tip>
        ) : (
          <div className="flex items-center gap-3 rounded-xl border border-line px-3 py-2.5">
            <span aria-hidden="true" className="grid size-8 shrink-0 place-items-center rounded-full bg-surface-4 text-small font-semibold text-fg">
              {account.initials}
            </span>
            <span className="min-w-0 flex-1">
              <span className="block truncate text-body font-medium text-fg">{account.displayName}</span>
              <span className="block truncate text-caption text-fg-4">{ROLE_LABEL[account.role]}</span>
            </span>
            <Tip label="Switch account">
              <IconButton label="Switch account" size="sm" onClick={onSwitchAccount}>
                <LogOut size={15} strokeWidth={1.8} />
              </IconButton>
            </Tip>
          </div>
        )}
      </div>
    </aside>
  );
}

// ---------------------------------------------------------------- antetul

interface HeaderProps {
  readonly title: ReactNode;
  readonly mission?: Schemas["MissionState"];
  readonly environments?: readonly Schemas["EnvironmentInfo"][];
  /** Lipsește pentru rolurile care nu pot schimba mediul (Pământul). */
  readonly onEnvironmentChange?: (id: Schemas["EnvironmentId"]) => void;
  /** Fluxul de evenimente a căzut și se reîncearcă: datele de pe ecran pot fi vechi. */
  readonly reconnecting: boolean;
  readonly onOpenDemo?: () => void;
}

/** Antetul: titlul ecranului în stânga; ziua și ora misiunii, mediul și legătura cu Pământul în dreapta. */
export function Header({ title, mission, environments, onEnvironmentChange, reconnecting, onOpenDemo }: HeaderProps): ReactElement {
  return (
    <header className="app-drag relative z-20 flex h-[52px] shrink-0 items-center gap-4 px-6">
      <h1 className="truncate text-body font-medium text-fg">{title}</h1>
      <span className="flex-1" />
      {mission && (
        <div className="app-no-drag hidden items-center gap-4 text-small text-fg-3 md:flex">
          {reconnecting && <Tag>Reconnecting…</Tag>}
          <Tip label={`Day ${mission.mission_day} din ${mission.total_days}; the clock runs ${mission.time_scale} times faster`}>
            <span className="num flex items-center gap-2 text-fg-2">
              <span>Day {mission.mission_day}</span>
              <span className="text-fg">{formatTime(mission.sim_now)}</span>
            </span>
          </Tip>
          {environments && onEnvironmentChange ? (
            <Select
              size="sm"
              label="Mission environment"
              value={mission.environment.id}
              options={environments.map((environment) => ({ value: environment.id, label: environment.name }))}
              onChange={onEnvironmentChange}
            />
          ) : (
            <span>{mission.environment.name}</span>
          )}
          <Tip label={mission.link.window_open ? "Earth link: the communication window is open" : "Earth link: the communication window is closed"}>
            <span className="inline-flex items-center gap-2">
              <Radio size={13} strokeWidth={1.9} />
              <span className="num text-fg-2">{formatDuration(mission.link.one_way_delay_s)}</span>
              <span className="text-fg-4">{mission.link.window_open ? "open" : "closed"}</span>
            </span>
          </Tip>
        </div>
      )}
      {onOpenDemo && (
        <Tip label="Demo panel (Ctrl+Shift+D)">
          <IconButton label="Open the demo panel" size="sm" onClick={onOpenDemo} className="app-no-drag">
            <FlaskConical size={15} strokeWidth={1.8} />
          </IconButton>
        </Tip>
      )}
    </header>
  );
}

/** Zona de conținut a unui ecran: derulează singură, cu lățime maximă și spațiere constante. */
export function Page({ children, narrow }: { readonly children: ReactNode; readonly narrow?: boolean }): ReactElement {
  return (
    <div className="scroll-q min-h-0 flex-1 overflow-y-auto">
      <div className={cx("mx-auto flex flex-col gap-5 px-6 pb-16 pt-4", narrow ? "max-w-[860px]" : "max-w-[1240px]")}>{children}</div>
    </div>
  );
}
