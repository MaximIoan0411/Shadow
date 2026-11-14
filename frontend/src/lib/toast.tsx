"use client";
/**
 * Notificările scurte din colțul ecranului (o alertă nouă, un mesaj sosit de pe Pământ, o valoare respinsă).
 * Dispar singure; cele importante au și un loc permanent în aplicație, deci nimic nu se pierde odată cu ele.
 */
import { X } from "lucide-react";
import { createContext, useCallback, useContext, useMemo, useRef, useState, type ReactElement, type ReactNode } from "react";
import { STATUS_META, type Status } from "./status";

export interface ToastInput {
  readonly title: string;
  readonly detail?: string;
  /** Starea pe care o anunță; fără ea, notificarea e neutră. */
  readonly status?: Status;
}

interface ToastItem extends ToastInput {
  readonly id: number;
}

type Notify = (toast: ToastInput) => void;

const VISIBLE_MS = 7000;
const MAX_VISIBLE = 4;

const ToastContext = createContext<Notify | null>(null);

export function useToast(): Notify {
  const notify = useContext(ToastContext);
  if (!notify) throw new Error("useToast must be used inside <ToastProvider>.");
  return notify;
}

export function ToastProvider({ children }: { readonly children: ReactNode }): ReactElement {
  const [items, setItems] = useState<readonly ToastItem[]>([]);
  const nextId = useRef(0);

  const dismiss = useCallback((id: number): void => {
    setItems((current) => current.filter((item) => item.id !== id));
  }, []);

  const notify = useCallback<Notify>(
    (toast) => {
      nextId.current += 1;
      const id = nextId.current;
      setItems((current) => [...current, { ...toast, id }].slice(-MAX_VISIBLE));
      setTimeout(() => dismiss(id), VISIBLE_MS);
    },
    [dismiss],
  );

  const value = useMemo(() => notify, [notify]);

  return (
    <ToastContext.Provider value={value}>
      {children}
      <div aria-live="polite" role="status" className="pointer-events-none fixed bottom-5 right-5 z-[60] flex w-[360px] max-w-[calc(100vw-40px)] flex-col gap-2">
        {items.map((item) => (
          <div key={item.id} className="float-q pointer-events-auto flex animate-[select-in_180ms_var(--ease-out)] items-start gap-3 rounded-2xl p-3.5">
            {item.status && (
              <span aria-hidden="true" className="mt-0.5 text-small leading-none" style={{ color: STATUS_META[item.status].color }}>
                {STATUS_META[item.status].shape}
              </span>
            )}
            <div className="min-w-0 flex-1">
              <p className="text-body font-medium text-fg">{item.title}</p>
              {item.detail && <p className="mt-0.5 text-small text-fg-3">{item.detail}</p>}
            </div>
            <button
              type="button"
              aria-label="Dismiss notification"
              onClick={() => dismiss(item.id)}
              className="grid size-6 shrink-0 place-items-center rounded-full text-fg-4 transition-colors hover:bg-white/[0.07] hover:text-fg"
            >
              <X size={14} strokeWidth={1.9} />
            </button>
          </div>
        ))}
      </div>
    </ToastContext.Provider>
  );
}
