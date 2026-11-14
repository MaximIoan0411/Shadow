"use client";
// Listă derulantă în stilul aplicației, în locul <select>-ului sistemului.
// Construită pe Radix Select: tastatura, căutarea după litere și cititoarele de ecran merg ca la una nativă.
import { Check, ChevronDown } from "lucide-react";
import { Select as Radix } from "radix-ui";
import type { ReactElement, ReactNode } from "react";
import { cx } from "./index";

export interface SelectOption<TValue extends string> {
  readonly value: TValue;
  readonly label: ReactNode;
  /** A doua linie, mai discretă, sub etichetă. */
  readonly detail?: ReactNode;
}

/** Radix keeps "" for "nothing chosen", so an option whose value is "" travels under this name inside the component. */
const EMPTY = "\u0000empty";
const MENU_OFFSET_PX = 6;

type SelectSize = "sm" | "md" | "toolbar";

const SIZE: Readonly<Record<SelectSize, string>> = {
  sm: "h-8 rounded-full pl-3 pr-2 text-small",
  md: "h-10 rounded-xl pl-3.5 pr-2.5 text-body",
  /** As tall as a Segmented control (a 32px button inside 4px padding and a 1px border), for rows that mix the two. */
  toolbar: "h-[42px] rounded-full pl-4 pr-3 text-body",
};

export function Select<TValue extends string>({
  value,
  options,
  onChange,
  label,
  placeholder = "Choose…",
  size = "md",
  className,
  disabled,
}: {
  readonly value: TValue | undefined;
  readonly options: readonly SelectOption<TValue>[];
  readonly onChange: (value: TValue) => void;
  /** Read by screen readers; also the tooltip. */
  readonly label: string;
  readonly placeholder?: string;
  readonly size?: SelectSize;
  readonly className?: string;
  readonly disabled?: boolean;
}): ReactElement {
  const inner = (v: string): string => v || EMPTY;
  const outer = (v: string): TValue | undefined => options.find((o) => inner(o.value) === v)?.value;
  return (
    <Radix.Root
      value={value === undefined ? undefined : inner(value)}
      onValueChange={(v) => {
        const chosen = outer(v);
        if (chosen !== undefined) onChange(chosen);
      }}
      disabled={disabled}
    >
      <Radix.Trigger
        aria-label={label}
        title={label}
        className={cx(
          "group inline-flex min-w-0 items-center gap-2 border border-line-4 bg-surface-2 font-medium text-fg-2 outline-none transition-colors hover:border-fg-4 hover:text-fg data-[state=open]:border-fg-3 data-[state=open]:bg-surface-3 data-[state=open]:text-fg disabled:cursor-not-allowed disabled:border-line-2 disabled:text-fg-4",
          SIZE[size],
          className,
        )}
      >
        <span className="min-w-0 flex-1 truncate text-left">
          <Radix.Value placeholder={placeholder} />
        </span>
        <Radix.Icon asChild>
          <ChevronDown size={13} strokeWidth={2} className="shrink-0 text-fg-4 transition-transform duration-200 group-data-[state=open]:rotate-180" />
        </Radix.Icon>
      </Radix.Trigger>
      <Radix.Portal>
        <Radix.Content
          position="popper"
          sideOffset={MENU_OFFSET_PX}
          className="z-[80] max-h-[var(--radix-select-content-available-height)] min-w-[var(--radix-select-trigger-width)] overflow-hidden rounded-2xl border border-line-2 bg-surface-3 p-1.5 shadow-[0_24px_60px_-12px_rgb(0_0_0/0.85)] data-[state=open]:animate-[select-in_140ms_ease-out]"
        >
          <Radix.Viewport className="scroll-q">
            {options.map((o) => (
              <Radix.Item
                key={inner(o.value)}
                value={inner(o.value)}
                className="relative flex cursor-default select-none items-center gap-2.5 rounded-xl py-2 pl-3 pr-8 text-body text-fg-2 outline-none transition-colors data-[highlighted]:bg-white/[0.07] data-[highlighted]:text-fg data-[state=checked]:text-fg"
              >
                <span className="min-w-0 flex-1">
                  <Radix.ItemText>
                    <span className="block truncate">{o.label}</span>
                  </Radix.ItemText>
                  {o.detail && <span className="block truncate text-caption text-fg-4">{o.detail}</span>}
                </span>
                <Radix.ItemIndicator className="absolute right-2.5">
                  <Check size={14} strokeWidth={2.2} />
                </Radix.ItemIndicator>
              </Radix.Item>
            ))}
          </Radix.Viewport>
        </Radix.Content>
      </Radix.Portal>
    </Radix.Root>
  );
}
