"use client";
/**
 * SHADOW — componentele de bază ale sistemului de design (v2). Documentația: DESIGN.md; catalogul viu: /kit.
 *
 * Reguli: tonuri neutre peste tot; culoarea apare doar ca stare, prin <StatusBadge /> / <StatusMark /> /
 * <Notice />, mereu cu forma și cuvântul ei. Butoanele sunt pastile, razele sunt 12 / 16 / 22, cifrele de
 * instrumente sunt mono (clasa `num`).
 */
import { clsx } from "clsx";
import { Check, RotateCcw } from "lucide-react";
import Link from "next/link";
import { Checkbox as RCheckbox, Slider as RSlider, Switch as RSwitch, Tooltip as RTooltip } from "radix-ui";
import { forwardRef } from "react";
import type { ButtonHTMLAttributes, HTMLAttributes, InputHTMLAttributes, ReactElement, ReactNode, TextareaHTMLAttributes } from "react";
import { formatNumber, formatSigned, toPercent } from "@/lib/format";
import { STATUS_META, levelLabel, levelShort, type Level, type Status } from "@/lib/status";

export const cx = clsx;

// ---------------------------------------------------------------- mișcare (preseturi pentru `motion`)

// cubic-bezier(0.22, 1, 0.36, 1): aceeași curbă ca --ease-out din tokens.css
const EASE_X1 = 0.22;
const EASE_X2 = 0.36;
const EASE_OUT: [number, number, number, number] = [EASE_X1, 1, EASE_X2, 1];
const RISE_PX = 10;
const RISE_SECONDS = 0.5;
const FADE_SECONDS = 0.15;

export const easeOut = EASE_OUT;

/** Singura intrare pe un ecran: conținutul care se așază. */
export const rise = {
  initial: { opacity: 0, y: RISE_PX },
  animate: { opacity: 1, y: 0 },
  transition: { duration: RISE_SECONDS, ease: EASE_OUT },
} as const;

export const fade = { initial: { opacity: 0 }, animate: { opacity: 1 }, exit: { opacity: 0 }, transition: { duration: FADE_SECONDS } } as const;

// ---------------------------------------------------------------- tooltip

export function TooltipProvider({ children }: { readonly children: ReactNode }): ReactElement {
  return <RTooltip.Provider delayDuration={350}>{children}</RTooltip.Provider>;
}

export function Tip({
  label,
  side = "top",
  children,
}: {
  readonly label: ReactNode;
  readonly side?: "top" | "bottom" | "left" | "right";
  readonly children: ReactElement;
}): ReactElement {
  return (
    <RTooltip.Root>
      <RTooltip.Trigger asChild>{children}</RTooltip.Trigger>
      <RTooltip.Portal>
        <RTooltip.Content
          side={side}
          sideOffset={8}
          className="z-[70] max-w-[280px] rounded-lg border border-line-2 bg-surface-4 px-2.5 py-1.5 text-small font-medium text-fg shadow-[0_8px_24px_rgb(0_0_0/0.5)] data-[state=delayed-open]:animate-[fadeIn_120ms_ease-out]"
        >
          {label}
        </RTooltip.Content>
      </RTooltip.Portal>
    </RTooltip.Root>
  );
}

// ---------------------------------------------------------------- butoane

type ButtonVariant = "primary" | "secondary" | "ghost";
type ButtonSize = "sm" | "md" | "lg";

const BUTTON_VARIANTS = {
  /** Acțiunea principală a ecranului. Cel mult una pe ecran. */
  primary: "bg-solid text-on-solid hover:bg-white disabled:bg-white/10 disabled:text-fg-4",
  secondary: "border border-line-2 bg-surface-3 text-fg hover:border-line-3 hover:bg-surface-4 disabled:text-fg-4",
  ghost: "text-fg-2 hover:bg-white/[0.06] hover:text-fg disabled:text-fg-4",
} as const satisfies Record<ButtonVariant, string>;

const BUTTON_SIZES = {
  sm: "h-8 px-3 text-small",
  md: "h-9 px-4 text-body",
  lg: "h-12 px-6 text-lead",
} as const satisfies Record<ButtonSize, string>;

type ButtonProps = ButtonHTMLAttributes<HTMLButtonElement> & {
  readonly variant?: ButtonVariant;
  readonly size?: ButtonSize;
  /** Arată că acțiunea e în curs și blochează a doua apăsare. */
  readonly busy?: boolean;
};

export const Button = forwardRef<HTMLButtonElement, ButtonProps>(function Button(
  { variant = "secondary", size = "md", busy, disabled, className, type = "button", children, ...rest },
  ref,
) {
  return (
    <button
      ref={ref}
      type={type}
      disabled={disabled || busy}
      aria-busy={busy || undefined}
      className={cx(
        "inline-flex select-none items-center justify-center gap-2 whitespace-nowrap rounded-full font-medium transition-colors duration-150 disabled:cursor-not-allowed",
        BUTTON_SIZES[size],
        BUTTON_VARIANTS[variant],
        className,
      )}
      {...rest}
    >
      {busy && <Spinner />}
      {children}
    </button>
  );
});

/** Un link care arată ca un buton: pentru navigare („Deschide alerta”), nu pentru acțiuni. */
export function ButtonLink({
  href,
  variant = "secondary",
  size = "md",
  className,
  children,
}: {
  readonly href: string;
  readonly variant?: ButtonVariant;
  readonly size?: ButtonSize;
  readonly className?: string;
  readonly children: ReactNode;
}): ReactElement {
  return (
    <Link
      href={href}
      className={cx(
        "inline-flex select-none items-center justify-center gap-2 whitespace-nowrap rounded-full font-medium no-underline transition-colors duration-150",
        BUTTON_SIZES[size],
        BUTTON_VARIANTS[variant],
        className,
      )}
    >
      {children}
    </Link>
  );
}

type IconButtonProps = ButtonHTMLAttributes<HTMLButtonElement> & {
  /** Numele accesibil; butonul are doar iconiță. */
  readonly label: string;
  readonly active?: boolean;
  readonly size?: "sm" | "md";
};

export const IconButton = forwardRef<HTMLButtonElement, IconButtonProps>(function IconButton(
  { label, active, size = "md", className, children, type = "button", ...rest },
  ref,
) {
  return (
    <button
      ref={ref}
      type={type}
      aria-label={label}
      aria-pressed={active}
      className={cx(
        "inline-grid shrink-0 place-items-center rounded-full transition-colors duration-150 disabled:cursor-not-allowed disabled:text-fg-5",
        size === "md" ? "size-9" : "size-8",
        active ? "bg-white/[0.1] text-fg" : "text-fg-3 hover:bg-white/[0.07] hover:text-fg",
        className,
      )}
      {...rest}
    >
      {children}
    </button>
  );
});

export function Spinner({ className }: { readonly className?: string }): ReactElement {
  return (
    <span
      aria-hidden="true"
      className={cx("inline-block size-3.5 animate-[spin_700ms_linear_infinite] rounded-full border-2 border-current border-r-transparent", className)}
    />
  );
}

// ---------------------------------------------------------------- câmpuri

const FIELD_BASE =
  "w-full rounded-xl border border-line-4 bg-surface-2 px-3.5 text-base text-fg outline-none transition-colors placeholder:text-fg-4 hover:border-fg-4 focus:border-fg-3 focus:bg-surface-3 aria-[invalid=true]:border-alert disabled:cursor-not-allowed disabled:border-line-2 disabled:text-fg-4";

export const Input = forwardRef<HTMLInputElement, InputHTMLAttributes<HTMLInputElement>>(function Input({ className, ...rest }, ref) {
  return <input ref={ref} className={cx(FIELD_BASE, "h-10", className)} {...rest} />;
});

export const Textarea = forwardRef<HTMLTextAreaElement, TextareaHTMLAttributes<HTMLTextAreaElement>>(function Textarea(
  { className, ...rest },
  ref,
) {
  return <textarea ref={ref} className={cx(FIELD_BASE, "min-h-24 resize-y py-2.5 leading-relaxed", className)} {...rest} />;
});

/** Eticheta, câmpul, indiciul și eroarea unui câmp, legate corect pentru cititoarele de ecran. */
export function Field({
  id,
  label,
  hint,
  error,
  children,
  className,
}: {
  /** Același `id` ca al câmpului din `children`. */
  readonly id: string;
  readonly label: ReactNode;
  readonly hint?: ReactNode;
  readonly error?: ReactNode;
  readonly children: ReactNode;
  readonly className?: string;
}): ReactElement {
  return (
    <div className={cx("flex flex-col gap-1.5", className)}>
      <label htmlFor={id} className="text-small font-medium text-fg-2">
        {label}
      </label>
      {children}
      {hint && !error && (
        <p id={`${id}-hint`} className="text-small text-fg-4">
          {hint}
        </p>
      )}
      {error && (
        <p id={`${id}-error`} role="alert" className="flex items-start gap-1.5 text-small text-fg-2">
          <StatusMark status="alert" className="mt-0.5" />
          {error}
        </p>
      )}
    </div>
  );
}

export function Switch({ checked, onChange, label }: { readonly checked: boolean; readonly onChange: (value: boolean) => void; readonly label: string }): ReactElement {
  return (
    <RSwitch.Root
      checked={checked}
      onCheckedChange={onChange}
      aria-label={label}
      className="relative h-[22px] w-[38px] shrink-0 rounded-full border border-line-4 bg-surface-3 transition-colors duration-200 data-[state=checked]:border-solid data-[state=checked]:bg-solid"
    >
      <RSwitch.Thumb className="block size-4 translate-x-[2px] rounded-full bg-fg transition-transform duration-200 ease-[cubic-bezier(0.22,1,0.36,1)] data-[state=checked]:translate-x-[18px] data-[state=checked]:bg-on-solid" />
    </RSwitch.Root>
  );
}

/** Bifa unui pas din plan. Eticheta e în `children`. */
export function Checkbox({
  checked,
  onChange,
  disabled,
  children,
}: {
  readonly checked: boolean;
  readonly onChange: (value: boolean) => void;
  readonly disabled?: boolean;
  readonly children: ReactNode;
}): ReactElement {
  return (
    <label className={cx("flex cursor-pointer items-start gap-3 rounded-xl px-2 py-2 transition-colors hover:bg-white/[0.04]", disabled && "cursor-not-allowed")}>
      <RCheckbox.Root
        checked={checked}
        disabled={disabled}
        onCheckedChange={(value) => onChange(value === true)}
        className="mt-0.5 grid size-[18px] shrink-0 place-items-center rounded-md border border-line-4 bg-surface-2 transition-colors data-[state=checked]:border-solid data-[state=checked]:bg-solid"
      >
        <RCheckbox.Indicator>
          <Check size={13} strokeWidth={3} className="text-on-solid" />
        </RCheckbox.Indicator>
      </RCheckbox.Root>
      <span className={cx("text-base leading-snug", checked ? "text-fg-3 line-through decoration-fg-5" : "text-fg")}>{children}</span>
    </label>
  );
}

export function Slider({
  value,
  min,
  max,
  step,
  onChange,
  label,
}: {
  readonly value: number;
  readonly min: number;
  readonly max: number;
  readonly step: number;
  readonly onChange: (value: number) => void;
  readonly label: string;
}): ReactElement {
  return (
    <RSlider.Root className="slider-q" value={[value]} min={min} max={max} step={step} onValueChange={([next]) => onChange(next ?? value)} aria-label={label}>
      <RSlider.Track data-track="">
        <RSlider.Range data-range="" />
      </RSlider.Track>
      <RSlider.Thumb data-thumb="" aria-label={label} />
    </RSlider.Root>
  );
}

const SEGMENT_SIZE = {
  sm: { track: "p-[3px]", button: "h-[26px] gap-1.5 px-3 text-small" },
  md: { track: "p-1", button: "h-8 gap-2 px-3.5 text-body" },
} as const;

/** Alegere unică din câteva opțiuni scurte (mediul, scara 1–5, „la bord / pe Pământ”). */
export function Segmented<TValue extends string>({
  value,
  options,
  onChange,
  label,
  size = "md",
  dense,
}: {
  readonly value: TValue | undefined;
  readonly options: readonly { readonly value: TValue; readonly label: string; readonly icon?: ReactNode }[];
  readonly onChange: (value: TValue) => void;
  readonly label: string;
  readonly size?: keyof typeof SEGMENT_SIZE;
  readonly dense?: boolean;
}): ReactElement {
  return (
    <div role="radiogroup" aria-label={label} className={cx("inline-flex w-fit rounded-full border border-line-2 bg-surface-2", SEGMENT_SIZE[size].track)}>
      {options.map((option) => (
        <button
          key={option.value}
          type="button"
          role="radio"
          aria-checked={option.value === value}
          onClick={() => onChange(option.value)}
          className={cx(
            "inline-flex items-center rounded-full font-medium transition-colors duration-150",
            SEGMENT_SIZE[size].button,
            dense && "min-w-9 justify-center !px-2.5",
            option.value === value ? "bg-solid text-on-solid" : "text-fg-3 hover:text-fg",
          )}
        >
          {option.icon}
          {option.label}
        </button>
      ))}
    </div>
  );
}

export function Kbd({ children }: { readonly children: ReactNode }): ReactElement {
  return (
    <kbd className="inline-flex h-5 min-w-5 items-center justify-center rounded-md border border-line-2 bg-white/[0.04] px-1.5 font-sans text-caption font-medium text-fg-3">
      {children}
    </kbd>
  );
}

// ---------------------------------------------------------------- suprafețe și titluri

type CardTag = "div" | "section" | "article" | "aside";

/** Cardul de bază, raza 22. `as="section"` + `aria-labelledby` pentru regiunile cu titlu. */
export function Card({ className, as: Tag = "div", ...rest }: HTMLAttributes<HTMLElement> & { readonly as?: CardTag }): ReactElement {
  return <Tag className={cx("card-q rounded-[var(--radius-card)] p-5", className)} {...rest} />;
}

/** Titlul mic al unei secțiuni, cu un element opțional în dreapta (o stare, un buton). */
export function SectionTitle({ children, right, id }: { readonly children: ReactNode; readonly right?: ReactNode; readonly id?: string }): ReactElement {
  return (
    <div className="mb-3 flex min-h-6 items-center justify-between gap-3">
      <h2 id={id} className="text-caption font-medium uppercase tracking-[0.06em] text-fg-4">
        {children}
      </h2>
      {right}
    </div>
  );
}

/** Etichetă neutră: „date simulate”, „ipoteză”, „Nivel 2”. Nu poartă niciodată culoare. */
export function Tag({ children, className }: { readonly children: ReactNode; readonly className?: string }): ReactElement {
  return (
    <span className={cx("inline-flex h-[22px] items-center gap-1.5 whitespace-nowrap rounded-full border border-line-2 px-2 text-caption font-medium text-fg-3", className)}>
      {children}
    </span>
  );
}

/** Nivelul de triaj: „Nivel 2”, sau cu `full` și cine se ocupă („Nivel 2 · ofițerul medical”). */
export function LevelTag({ level, full }: { readonly level: Level; readonly full?: boolean }): ReactElement {
  return <Tag>{full ? levelLabel(level) : levelShort(level)}</Tag>;
}

// ---------------------------------------------------------------- stare

/** Iconița stării, cât textul din jur, cu linie subțire. Decorativă: cuvântul stării îl dă cine o folosește. */
export function StatusIcon({ status, className }: { readonly status: Status; readonly className?: string }): ReactElement {
  const Icon = STATUS_META[status].icon;
  return <Icon aria-hidden="true" size="1.08em" strokeWidth={2} className={cx("shrink-0", className)} />;
}

/** Doar iconița colorată a stării; cuvântul e citit de cititoarele de ecran. Pentru locuri înguste. */
export function StatusMark({ status, className }: { readonly status: Status; readonly className?: string }): ReactElement {
  const meta = STATUS_META[status];
  return (
    <span className={cx("inline-flex shrink-0 items-center leading-none", className)} style={{ color: meta.color }}>
      <StatusIcon status={status} />
      <span className="sr-only">{meta.label}</span>
    </span>
  );
}

/**
 * Starea: culoare + iconiță + cuvânt, mereu împreună. `compact` = fără pastilă, pentru rânduri dense.
 * Singura componentă (cu StatusMark și Notice) care are voie să folosească o culoare de stare.
 */
export function StatusBadge({
  status,
  label,
  compact,
  className,
}: {
  readonly status: Status;
  /** Înlocuiește cuvântul implicit („În limite”, „De urmărit”, „Alertă”, „Fără date”). */
  readonly label?: string;
  readonly compact?: boolean;
  readonly className?: string;
}): ReactElement {
  const meta = STATUS_META[status];
  if (compact) {
    return (
      <span className={cx("inline-flex items-center gap-1.5 whitespace-nowrap text-small font-medium", className)} style={{ color: meta.color }}>
        <StatusIcon status={status} />
        {label ?? meta.label}
      </span>
    );
  }
  return (
    <span
      className={cx("inline-flex h-6 items-center gap-1.5 whitespace-nowrap rounded-full border px-2.5 text-small font-medium", className)}
      style={{
        color: meta.color,
        borderColor: `color-mix(in oklab, ${meta.color} 32%, transparent)`,
        background: `color-mix(in oklab, ${meta.color} 10%, transparent)`,
      }}
    >
      <StatusIcon status={status} />
      {label ?? meta.label}
    </span>
  );
}

type NoticeTone = "neutral" | "watch" | "alert" | "ok";

const NOTICE_TONE = {
  neutral: "border-line-2 bg-white/[0.03]",
  ok: "border-ok/30 bg-ok/[0.07]",
  watch: "border-watch/30 bg-watch/[0.07]",
  alert: "border-alert/35 bg-alert/[0.08]",
} as const satisfies Record<NoticeTone, string>;

/** Mesaj pe toată lățimea: o eroare, o avertizare, o confirmare. Tonul colorat are și forma stării. */
export function Notice({
  tone = "neutral",
  title,
  children,
  action,
  className,
}: {
  readonly tone?: NoticeTone;
  readonly title: ReactNode;
  readonly children?: ReactNode;
  readonly action?: ReactNode;
  readonly className?: string;
}): ReactElement {
  return (
    <div role={tone === "alert" ? "alert" : "status"} className={cx("flex items-start gap-3 rounded-2xl border p-4", NOTICE_TONE[tone], className)}>
      {tone !== "neutral" && <StatusMark status={tone} className="mt-[3px] text-base" />}
      <div className="min-w-0 flex-1">
        <p className="text-base font-medium text-fg">{title}</p>
        {children && <div className="mt-0.5 text-body leading-relaxed text-fg-3">{children}</div>}
      </div>
      {action && <div className="shrink-0">{action}</div>}
    </div>
  );
}

/** O eroare de la backend, spusă simplu, cu o cale de a încerca din nou. */
export function ProblemCard({ title, detail, onRetry, className }: { readonly title: string; readonly detail?: string; readonly onRetry?: () => void; readonly className?: string }): ReactElement {
  return (
    <Notice
      tone="alert"
      title={title}
      className={className}
      action={
        onRetry && (
          <Button size="sm" onClick={onRetry}>
            <RotateCcw size={13} strokeWidth={2} />
            Try again
          </Button>
        )
      }
    >
      {detail}
    </Notice>
  );
}

/** Stare goală: spune ce lipsește și, dacă se poate, ce e de făcut. */
export function EmptyState({ title, children, action }: { readonly title: string; readonly children?: ReactNode; readonly action?: ReactNode }): ReactElement {
  return (
    <div className="flex flex-col items-center gap-2 rounded-2xl border border-dashed border-line-2 px-6 py-10 text-center">
      <p className="text-base font-medium text-fg-2">{title}</p>
      {children && <p className="max-w-[46ch] text-body text-fg-4">{children}</p>}
      {action && <div className="mt-2">{action}</div>}
    </div>
  );
}

export function Skeleton({ className }: { readonly className?: string }): ReactElement {
  return <div aria-hidden="true" className={cx("skeleton", className)} />;
}

// ---------------------------------------------------------------- valori

/** Bară subțire: o valoare într-un interval. Neutră; `status` îi dă culoare doar când valoarea e o stare. */
export function Meter({
  value,
  max,
  label,
  status,
  className,
}: {
  readonly value: number;
  readonly max: number;
  readonly label: string;
  readonly status?: Status;
  readonly className?: string;
}): ReactElement {
  return (
    <div
      role="meter"
      aria-label={label}
      aria-valuemin={0}
      aria-valuemax={max}
      aria-valuenow={value}
      className={cx("h-1.5 w-full overflow-hidden rounded-full bg-white/[0.08]", className)}
    >
      <div
        className="h-full rounded-full transition-[width] duration-500 ease-[var(--ease-out)]"
        style={{ width: `${toPercent(value, 0, max)}%`, background: status ? STATUS_META[status].color : "var(--color-fg-2)" }}
      />
    </div>
  );
}

/**
 * O valoare față de normalul personal. Datele vin direct din `MetricValue` (contract): frontend-ul doar le
 * formatează, nu calculează nici abaterea, nici starea.
 */
export function Metric({
  label,
  value,
  unit,
  baseline,
  deviation,
  status,
  simulated,
}: {
  readonly label: string;
  readonly value: number | null | undefined;
  readonly unit: string;
  readonly baseline?: number | null;
  readonly deviation?: number | null;
  readonly status: Status;
  readonly simulated?: boolean;
}): ReactElement {
  return (
    <div className="rounded-2xl border border-line bg-white/[0.02] p-3.5">
      <div className="flex items-center justify-between gap-2">
        <span className="text-small text-fg-3">{label}</span>
        <StatusBadge status={status} compact />
      </div>
      <div className="mt-1.5 flex items-baseline gap-1.5">
        <span className="text-display font-medium tracking-[-0.02em] text-fg">{formatNumber(value)}</span>
        <span className="text-small text-fg-4">{unit}</span>
      </div>
      <div className="mt-2 flex min-h-[22px] items-center justify-between gap-2 text-small text-fg-4">
        <span>
          {baseline !== null && baseline !== undefined && (
            <>
              your baseline <span className="num text-fg-3">{formatNumber(baseline)}</span>
            </>
          )}
          {deviation !== null && deviation !== undefined && <span className="num ml-2 text-fg-2">{formatSigned(deviation)}</span>}
        </span>
        {simulated && <Tag>simulated data</Tag>}
      </div>
    </div>
  );
}
