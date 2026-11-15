"use client";
/**
 * Straturile care se deschid peste ecran: panoul lateral (detaliile unei zone, panoul de demo), fereastra de
 * confirmare și filele. Toate pe Radix: focusul rămâne înăuntru, Esc le închide, cititoarele de ecran le anunță.
 */
import { X } from "lucide-react";
import { Dialog as RDialog, Tabs as RTabs } from "radix-ui";
import type { ReactElement, ReactNode } from "react";
import { IconButton, cx } from "./index";

const OVERLAY = "fixed inset-0 z-40 bg-black/55 data-[state=open]:animate-[fadeIn_160ms_ease-out]";

/** Panou care intră din dreapta. Conținutul din spate rămâne vizibil, ca să nu se piardă contextul. */
export function Sheet({
  open,
  onClose,
  title,
  description,
  eyebrow,
  children,
  wide,
}: {
  readonly open: boolean;
  readonly onClose: () => void;
  readonly title: ReactNode;
  /** Citită de cititoarele de ecran la deschidere; opțională. */
  readonly description?: string;
  /** Rând mic deasupra titlului (iconița și numele zonei). */
  readonly eyebrow?: ReactNode;
  readonly children: ReactNode;
  readonly wide?: boolean;
}): ReactElement {
  return (
    <RDialog.Root open={open} onOpenChange={(next) => !next && onClose()}>
      <RDialog.Portal>
        <RDialog.Overlay className={OVERLAY} />
        <RDialog.Content
          {...(description ? {} : { "aria-describedby": undefined })}
          className={cx(
            "float-q fixed bottom-3 right-3 top-3 z-50 flex w-[calc(100vw-24px)] flex-col rounded-[var(--radius-card)] outline-none data-[state=open]:animate-[sheet-in_240ms_var(--ease-out)]",
            wide ? "max-w-[720px]" : "max-w-[560px]",
          )}
        >
          <header className="flex shrink-0 items-start gap-3 border-b border-line px-6 pb-4 pt-5">
            <div className="min-w-0 flex-1">
              {eyebrow && <div className="mb-1 flex items-center gap-2 text-small text-fg-3">{eyebrow}</div>}
              <RDialog.Title className="text-title font-medium text-fg">{title}</RDialog.Title>
              {description && <RDialog.Description className="sr-only">{description}</RDialog.Description>}
            </div>
            <RDialog.Close asChild>
              <IconButton label="Close panel" size="sm">
                <X size={16} strokeWidth={1.9} />
              </IconButton>
            </RDialog.Close>
          </header>
          <div className="scroll-q min-h-0 flex-1 overflow-y-auto px-6 py-5">{children}</div>
        </RDialog.Content>
      </RDialog.Portal>
    </RDialog.Root>
  );
}

/** Fereastră mică în centru, pentru o întrebare sau o confirmare. */
export function Dialog({
  open,
  onClose,
  title,
  children,
  footer,
}: {
  readonly open: boolean;
  readonly onClose: () => void;
  readonly title: ReactNode;
  readonly children: ReactNode;
  /** Butoanele; acțiunea principală ultima (în dreapta). */
  readonly footer?: ReactNode;
}): ReactElement {
  return (
    <RDialog.Root open={open} onOpenChange={(next) => !next && onClose()}>
      <RDialog.Portal>
        <RDialog.Overlay className={OVERLAY} />
        <RDialog.Content
          aria-describedby={undefined}
          className="float-q fixed left-1/2 top-1/2 z-50 w-[calc(100vw-40px)] max-w-[460px] -translate-x-1/2 -translate-y-1/2 rounded-[var(--radius-card)] p-6 outline-none data-[state=open]:animate-[fadeIn_160ms_ease-out]"
        >
          <RDialog.Title className="text-title font-medium text-fg">{title}</RDialog.Title>
          <div className="mt-3 text-base leading-relaxed text-fg-2">{children}</div>
          {footer && <div className="mt-6 flex justify-end gap-2">{footer}</div>}
        </RDialog.Content>
      </RDialog.Portal>
    </RDialog.Root>
  );
}

export interface TabItem<TValue extends string> {
  readonly value: TValue;
  readonly label: string;
  /** Un număr mic lângă etichetă (câte elemente sunt în filă). */
  readonly count?: number;
  readonly content: ReactNode;
}

/** File: aceeași zonă a ecranului, mai multe vederi. Săgețile stânga/dreapta mută între ele. */
export function Tabs<TValue extends string>({
  value,
  onChange,
  items,
  label,
}: {
  readonly value: TValue;
  readonly onChange: (value: TValue) => void;
  readonly items: readonly TabItem<TValue>[];
  readonly label: string;
}): ReactElement {
  return (
    <RTabs.Root
      value={value}
      onValueChange={(next) => {
        const chosen = items.find((item) => item.value === next);
        if (chosen) onChange(chosen.value);
      }}
    >
      <RTabs.List aria-label={label} className="flex gap-1 overflow-x-auto border-b border-line [scrollbar-width:none]">
        {items.map((item) => (
          <RTabs.Trigger
            key={item.value}
            value={item.value}
            className="relative -mb-px flex h-10 shrink-0 items-center gap-2 whitespace-nowrap border-b-2 border-transparent px-3 text-body font-medium text-fg-3 transition-colors hover:text-fg data-[state=active]:border-solid data-[state=active]:text-fg"
          >
            {item.label}
            {item.count !== undefined && <span className="num text-caption text-fg-4">{item.count}</span>}
          </RTabs.Trigger>
        ))}
      </RTabs.List>
      {items.map((item) => (
        <RTabs.Content key={item.value} value={item.value} className="pt-5 outline-none">
          {item.content}
        </RTabs.Content>
      ))}
    </RTabs.Root>
  );
}
