"use client";
import { useCallback, useEffect, useRef, useState, type RefObject } from "react";

/** Lățimea curentă a unui element, urmărită cu ResizeObserver. `0` până la prima măsurare. */
export function useElementWidth<TElement extends HTMLElement>(): readonly [RefObject<TElement | null>, number] {
  const ref = useRef<TElement | null>(null);
  const [width, setWidth] = useState(0);

  useEffect(() => {
    const element = ref.current;
    if (!element) return undefined;
    const observer = new ResizeObserver(([entry]) => {
      if (entry) setWidth(Math.round(entry.contentRect.width));
    });
    observer.observe(element);
    return () => observer.disconnect();
  }, []);

  return [ref, width] as const;
}

/** Ține cea mai nouă versiune a unei funcții fără să repornească efectele care o folosesc. */
export function useLatest<TValue>(value: TValue): RefObject<TValue> {
  const ref = useRef(value);
  useEffect(() => {
    ref.current = value;
  }, [value]);
  return ref;
}

/** Scurtătură de tastatură la nivel de fereastră: `useHotkey((e) => e.ctrlKey && e.shiftKey && e.code === "KeyD", toggle)`. */
export function useHotkey(matches: (event: KeyboardEvent) => boolean, handler: () => void): void {
  const matchRef = useLatest(matches);
  const handlerRef = useLatest(handler);

  const onKeyDown = useCallback(
    (event: KeyboardEvent): void => {
      if (!matchRef.current(event)) return;
      event.preventDefault();
      handlerRef.current();
    },
    [matchRef, handlerRef],
  );

  useEffect(() => {
    window.addEventListener("keydown", onKeyDown);
    return () => window.removeEventListener("keydown", onKeyDown);
  }, [onKeyDown]);
}
