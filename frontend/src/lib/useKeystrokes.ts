"use client";
import { useCallback, useEffect, useRef } from "react";
import { createKeystrokeCollector, type KeystrokeCollector, type Schemas } from "./api";
import { useLatest } from "./hooks";
import { useSession } from "./session";

type Context = Schemas["KeystrokeBatch"]["context"];
type KeyClass = Schemas["KeyEvent"]["key_class"];

interface Handlers {
  readonly onResult?: (result: Schemas["KeystrokeResult"]) => void;
  readonly onStroke?: (holdMs: number, keyClass: KeyClass) => void;
}

interface KeystrokeBindings {
  /** Se pun pe câmpul urmărit: `<textarea onKeyDown={…} onKeyUp={…} />`. */
  readonly onKeyDown: (event: { readonly code: string; readonly repeat?: boolean }) => void;
  readonly onKeyUp: (event: { readonly code: string; readonly key: string }) => void;
  /** Trimite ce a rămas și închide sesiunea de tastare; următoarea tastă începe una nouă. */
  readonly finish: () => Promise<void>;
}

/**
 * Leagă un câmp de text de colectorul de tastare. Sesiunea începe la prima tastă și se oprește la `finish()`,
 * la ieșirea de pe ecran și la schimbarea astronautului. Se trimit doar timpii și clasa tastei, niciodată textul.
 */
export function useKeystrokes(crewId: string | null, context: Context, handlers: Handlers = {}): KeystrokeBindings {
  const { onBeforeLogout } = useSession();
  const collector = useRef<KeystrokeCollector | null>(null);
  const latest = useLatest(handlers);

  const finish = useCallback(async (): Promise<void> => {
    const current = collector.current;
    collector.current = null;
    await current?.stop();
  }, []);

  useEffect(() => {
    const unregister = onBeforeLogout(finish);
    return () => {
      unregister();
      void finish();
    };
  }, [onBeforeLogout, finish]);

  const ensure = useCallback((): KeystrokeCollector | null => {
    if (!crewId) return null;
    collector.current ??= createKeystrokeCollector(crewId, context, {
      onResult: (result) => latest.current.onResult?.(result),
      onStroke: (holdMs, keyClass) => latest.current.onStroke?.(holdMs, keyClass),
    });
    return collector.current;
  }, [crewId, context, latest]);

  const onKeyDown = useCallback<KeystrokeBindings["onKeyDown"]>((event) => ensure()?.onKeyDown(event), [ensure]);
  const onKeyUp = useCallback<KeystrokeBindings["onKeyUp"]>((event) => collector.current?.onKeyUp(event), []);

  return { onKeyDown, onKeyUp, finish };
}
