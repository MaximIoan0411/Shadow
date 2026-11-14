"use client";
/**
 * SHADOW — componentele de bază. Portate din Quaternion (src/components/ui.tsx), cu aceleași clase și animații,
 * plus componentele specifice SHADOW (StatusBadge, Card, Metric, PillarTag, SectionTitle).
 *
 * Reguli (din Quaternion): butoane rotunde, raze 12 / 16 / 22, linii fine în loc de umbre grele, o singură animație
 * de intrare pe ecran, culoarea folosită ca informație. Reguli SHADOW: culoarea de stare apare mereu cu formă și
 * cuvânt; cifrele de instrumente sunt mono (clasa `num`).
 */
import { clsx } from "clsx";
import { RotateCcw, TriangleAlert } from "lucide-react";
import type { ButtonHTMLAttributes, CSSProperties, HTMLAttributes, ReactElement, ReactNode } from "react";
import { forwardRef } from "react";
import { Slider as RSlider, Switch as RSwitch, Tooltip as RTooltip } from "radix-ui";
import { PILLAR_HUE, STATUS_META } from "@/lib/hues";
import type { components } from "@/lib/shadow-api";

type Status = components["schemas"]["Status"];
type Pillar = components["schemas"]["Pillar"];

export const cx = clsx;

// ---------------------------------------------------------------- mișcare (preseturile Quaternion, pentru `motion`)

// cubic-bezier(0.22, 1, 0.36, 1), aceeași curbă ca --ease-out din tokens.css
const EASE_X1 = 0.22;
const EASE_X2 = 0.36;
const EASE_OUT: [number, number, number, number] = [EASE_X1, 1, EASE_X2, 1];
export const easeOut = EASE_OUT;

const POP_SECONDS = 0.16;
const POP_SCALE = 0.97;
const POP_LIFT_PX = 6;
const POP_EXIT_LIFT_PX = 3;
const RISE_PX = 10;
const RISE_SECONDS = 0.5;
const SLIDE_PX = 8;
const FADE_SECONDS = 0.15;
const SETTLE_SCALE = 0.96;

/** Meniuri și ferestre mici: o ridicare scurtă din buton. */
export const pop = {
  initial: { opacity: 0, y: POP_LIFT_PX, scale: POP_SCALE },
  animate: { opacity: 1, y: 0, scale: 1 },
  exit: { opacity: 0, y: POP_EXIT_LIFT_PX, scale: POP_SCALE },
  transition: { duration: POP_SECONDS, ease: EASE_OUT },
} as const;

/** Singura intrare pe un ecran: conținutul care se așază. */
export const rise = {
  initial: { opacity: 0, y: RISE_PX },
  animate: { opacity: 1, y: 0 },
  transition: { duration: RISE_SECONDS, ease: EASE_OUT },
} as const;

export const slideUp = { initial: { opacity: 0, y: SLIDE_PX }, animate: { opacity: 1, y: 0 }, exit: { opacity: 0, y: SLIDE_PX } } as const;
export const fade = { initial: { opacity: 0 }, animate: { opacity: 1 }, exit: { opacity: 0 }, transition: { duration: FADE_SECONDS } } as const;
export const settle = { initial: { scale: SETTLE_SCALE }, animate: { scale: 1 } } as const;

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
          className="z-50 rounded-lg border border-line-2 bg-surface-3 px-2.5 py-1.5 text-[12.5px] font-medium text-fg shadow-[0_8px_24px_rgb(var(--shade)/calc(0.5*var(--shade-k)))] data-[state=delayed-open]:animate-[fadeIn_120ms_ease-out]"
        >
          {label}
        </RTooltip.Content>
      </RTooltip.Portal>
    </RTooltip.Root>
  );
}

// ---------------------------------------------------------------- butoane

type ButtonVariant = "primary" | "secondary" | "ghost" | "danger";

const BUTTON_VARIANTS: Readonly<Record<ButtonVariant, string>> = {
  primary: "bg-platinum text-black hover:bg-white disabled:bg-white/10 disabled:text-fg-3 disabled:opacity-100",
  secondary: "bg-surface-3 text-fg border border-line-2 hover:bg-surface-4 hover:border-line-3",
  ghost: "text-fg-2 hover:text-fg hover:bg-white/[0.06]",
  danger: "text-danger hover:bg-danger/10",
};

type ButtonProps = ButtonHTMLAttributes<HTMLButtonElement> & {
  readonly variant?: ButtonVariant;
  readonly size?: "sm" | "md" | "lg";
};

const BUTTON_SIZE = { sm: "h-8 px-3 text-[13px]", md: "h-9 px-4 text-[13.5px]", lg: "h-12 px-6 text-[15px]" } as const;

export const Button = forwardRef<HTMLButtonElement, ButtonProps>(function Button(
  { variant = "secondary", size = "md", className, type = "button", ...rest },
  ref,
) {
  return (
    <button
      ref={ref}
      type={type}
      className={cx(
        "inline-flex select-none items-center justify-center gap-2 whitespace-nowrap rounded-full font-medium transition-colors duration-150 disabled:cursor-not-allowed disabled:opacity-40",
        BUTTON_SIZE[size],
        BUTTON_VARIANTS[variant],
        className,
      )}
      {...rest}
    />
  );
});

type IconButtonProps = ButtonHTMLAttributes<HTMLButtonElement> & {
  readonly label: string;
  readonly active?: boolean;
  readonly size?: "sm" | "md";
};

/** Buton rotund, doar cu iconiță; `label` devine numele accesibil. */
export const IconButton = forwardRef<HTMLButtonElement, IconButtonProps>(function IconButton(
  { label, active, size = "md", className, children, type = "button", ...rest },
  ref,
) {
  return (
    <button
      ref={ref}
      type={type}
      aria-label={label}
      className={cx(
        "inline-grid shrink-0 place-items-center rounded-full transition-colors duration-150 disabled:cursor-not-allowed disabled:opacity-40",
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

// ---------------------------------------------------------------- câmpuri

export function Switch({ checked, onChange, label }: { readonly checked: boolean; readonly onChange: (v: boolean) => void; readonly label: string }): ReactElement {
  return (
    <RSwitch.Root
      checked={checked}
      onCheckedChange={onChange}
      aria-label={label}
      className="relative h-[22px] w-[38px] shrink-0 rounded-full bg-white/[0.12] transition-colors duration-200 data-[state=checked]:bg-platinum"
    >
      <RSwitch.Thumb className="block size-[18px] translate-x-[2px] rounded-full bg-fg shadow-[0_1px_3px_rgb(var(--shade)/calc(0.5*var(--shade-k)))] transition-transform duration-200 ease-[cubic-bezier(0.22,1,0.36,1)] data-[state=checked]:translate-x-[18px] data-[state=checked]:bg-black" />
    </RSwitch.Root>
  );
}

export function Slider({
  value,
  min,
  max,
  step,
  onChange,
  label,
  hue,
}: {
  readonly value: number;
  readonly min: number;
  readonly max: number;
  readonly step: number;
  readonly onChange: (v: number) => void;
  readonly label: string;
  readonly hue?: string;
}): ReactElement {
  return (
    <RSlider.Root
      className="slider-q"
      value={[value]}
      min={min}
      max={max}
      step={step}
      onValueChange={([v]) => onChange(v)}
      aria-label={label}
      style={hue ? ({ "--slider-hue": hue } as CSSProperties) : undefined}
    >
      <RSlider.Track data-track="">
        <RSlider.Range data-range="" />
      </RSlider.Track>
      <RSlider.Thumb data-thumb="" />
    </RSlider.Root>
  );
}

const SEGMENT_SIZE = {
  sm: { track: "p-[3px]", button: "h-[26px] gap-1.5 px-3 text-[12.5px]" },
  md: { track: "p-1", button: "h-8 gap-2 px-3.5 text-[13px]" },
} as const;

/** Butoane-pastilă unul lângă altul (ex. comutatorul de mediu, scara 1–5 a stării de spirit). */
export function Segmented<TValue extends string>({
  value,
  options,
  onChange,
  label,
  size = "md",
  dense,
}: {
  readonly value: TValue;
  readonly options: readonly { readonly value: TValue; readonly label: string; readonly icon?: ReactNode }[];
  readonly onChange: (v: TValue) => void;
  readonly label: string;
  readonly size?: "sm" | "md";
  readonly dense?: boolean;
}): ReactElement {
  return (
    <div role="radiogroup" aria-label={label} className={cx("inline-flex w-fit rounded-full border border-line-2 bg-surface-2", SEGMENT_SIZE[size].track)}>
      {options.map((o) => (
        <button
          key={o.value}
          type="button"
          role="radio"
          aria-checked={o.value === value}
          onClick={() => onChange(o.value)}
          className={cx(
            "inline-flex items-center rounded-full font-medium transition-colors duration-150",
            SEGMENT_SIZE[size].button,
            dense && "min-w-8 justify-center !px-2.5",
            o.value === value ? "bg-white/[0.1] text-fg shadow-[inset_0_0_0_1px_rgb(var(--tint)/0.08)]" : "text-fg-3 hover:text-fg",
          )}
        >
          {o.icon}
          {o.label}
        </button>
      ))}
    </div>
  );
}

/** Câmp de text în stilul Quaternion (fundal surface-2, linie fină, focus luminos). */
export const Input = forwardRef<HTMLInputElement, React.InputHTMLAttributes<HTMLInputElement>>(function Input({ className, ...rest }, ref) {
  return (
    <input
      ref={ref}
      className={cx(
        "h-10 w-full rounded-xl border border-line-2 bg-surface-2 px-3.5 text-[14px] text-fg outline-none transition-colors placeholder:text-fg-5 hover:border-line-3 focus:border-line-3 focus:bg-surface-3 aria-[invalid=true]:border-danger/60",
        className,
      )}
      {...rest}
    />
  );
});

export function Kbd({ children }: { readonly children: ReactNode }): ReactElement {
  return (
    <kbd className="inline-flex h-5 min-w-5 items-center justify-center rounded-md border border-line-2 bg-white/[0.04] px-1.5 font-sans text-[11px] font-medium text-fg-3">
      {children}
    </kbd>
  );
}

// ---------------------------------------------------------------- decor viu (Quaternion)

const ORB_SIZE_PX = 56;

/** Sfera lucioasă în nuanțele ecranului; pentru stările goale (ex. „Nicio alertă”). */
export function Orb({ size = ORB_SIZE_PX, children, className }: { readonly size?: number; readonly children?: ReactNode; readonly className?: string }): ReactElement {
  return (
    <span aria-hidden="true" className={cx("orb", className)} style={{ "--orb-size": `${size}px` } as CSSProperties}>
      {children}
    </span>
  );
}

/** Punct luminos colorat (în Quaternion: modelul; în SHADOW: pilonul sau legătura). */
export function Dot({ hue, className }: { readonly hue: string; readonly className?: string }): ReactElement {
  return <span aria-hidden="true" className={cx("inline-block size-2 rounded-full", className)} style={{ background: hue, boxShadow: `0 0 10px ${hue}` }} />;
}

/** O eroare spusă simplu, cu o cale de a încerca din nou. `title`/`detail` vin de la backend (ApiError.message). */
export function ProblemCard({ title, detail, onRetry, className }: { readonly title: string; readonly detail?: string; readonly onRetry?: () => void; readonly className?: string }): ReactElement {
  return (
    <div role="alert" className={cx("flex items-start gap-3.5 rounded-2xl border border-danger/25 bg-danger/[0.06] p-4", className)}>
      <span className="grid size-8 shrink-0 place-items-center rounded-xl bg-danger/15 text-danger">
        <TriangleAlert size={16} strokeWidth={1.9} />
      </span>
      <div className="min-w-0 flex-1">
        <p className="text-[14px] font-medium text-fg">{title}</p>
        {detail && <p className="mt-0.5 text-[13px] leading-relaxed text-fg-3">{detail}</p>}
      </div>
      {onRetry && (
        <Button size="sm" onClick={onRetry} className="shrink-0">
          <RotateCcw size={13} strokeWidth={2} />
          Încearcă din nou
        </Button>
      )}
    </div>
  );
}

// ---------------------------------------------------------------- SHADOW

/** Card de sticlă (utilitarul `card-q` din Quaternion), raza 22. `as="section"` pentru regiuni cu titlu. */
export function Card({
  className,
  as: Tag = "div",
  ...rest
}: HTMLAttributes<HTMLElement> & { readonly as?: "div" | "section" | "article" | "aside" }): ReactElement {
  return <Tag className={cx("card-q rounded-[var(--radius-card)] p-5", className)} {...rest} />;
}

/** Titlu mic de secțiune, ca grupurile din bara laterală Quaternion („TODAY”). */
export function SectionTitle({ children, right, id }: { readonly children: ReactNode; readonly right?: ReactNode; readonly id?: string }): ReactElement {
  return (
    <div className="mb-3 flex items-baseline justify-between gap-3">
      <h2 id={id} className="text-[11.5px] font-medium uppercase tracking-[0.06em] text-fg-4">
        {children}
      </h2>
      {right}
    </div>
  );
}

/**
 * Starea: culoare + formă + cuvânt, mereu împreună (cerință de accesibilitate și de onestitate).
 * `compact` = doar forma și cuvântul, fără pastilă.
 */
export function StatusBadge({ status, label, compact, className }: { readonly status: Status; readonly label?: string; readonly compact?: boolean; readonly className?: string }): ReactElement {
  const m = STATUS_META[status];
  if (compact) {
    return (
      <span className={cx("inline-flex items-center gap-1.5 text-[12.5px] font-medium", className)} style={{ color: m.color }}>
        <span aria-hidden="true">{m.shape}</span>
        {label ?? m.label}
      </span>
    );
  }
  return (
    <span
      className={cx("inline-flex h-6 items-center gap-1.5 rounded-full border px-2.5 text-[12px] font-medium", className)}
      style={{ color: m.color, borderColor: `color-mix(in oklab, ${m.color} 30%, transparent)`, background: `color-mix(in oklab, ${m.color} 9%, transparent)` }}
    >
      <span aria-hidden="true" className="text-[10px] leading-none">
        {m.shape}
      </span>
      {label ?? m.label}
    </span>
  );
}

/** Eticheta unui pilon, cu punctul în culoarea lui. */
export function PillarTag({ pillar, name, className }: { readonly pillar: Pillar; readonly name: string; readonly className?: string }): ReactElement {
  return (
    <span className={cx("inline-flex items-center gap-2 text-[12.5px] font-medium text-fg-2", className)}>
      <Dot hue={PILLAR_HUE[pillar]} />
      {name}
    </span>
  );
}

/**
 * O valoare față de normalul personal: eticheta, cifra mono, unitatea, normalul și abaterea.
 * Datele vin direct din MetricValue (contract API) — frontend-ul nu calculează nimic.
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
  readonly deviation?: string;
  readonly status: Status;
  readonly simulated?: boolean;
}): ReactElement {
  return (
    <div className="rounded-2xl border border-line bg-white/[0.02] p-3.5">
      <div className="flex items-center justify-between gap-2">
        <span className="text-[12.5px] text-fg-3">{label}</span>
        <StatusBadge status={status} compact />
      </div>
      <div className="mt-1.5 flex items-baseline gap-1.5">
        <span className="text-[28px] font-medium leading-none tracking-[-0.02em] text-fg tabular-nums">{value ?? "—"}</span>
        <span className="text-[12.5px] text-fg-4">{unit}</span>
      </div>
      <div className="mt-2 flex items-center justify-between gap-2 text-[12px] text-fg-4">
        <span>
          {baseline != null && (
            <>
              normalul tău <span className="num text-fg-3">{baseline}</span>
            </>
          )}
          {deviation && <span className="num ml-1.5 text-fg-3">{deviation}</span>}
        </span>
        {simulated && <span className="rounded-full border border-line-2 px-2 py-0.5 text-[11px]">date simulate</span>}
      </div>
    </div>
  );
}
