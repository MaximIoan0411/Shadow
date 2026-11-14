/**
 * Puntea cu aplicația de desktop (electron/preload.cjs). În browser `window.shadowDesktop` nu există,
 * iar funcțiile de aici întorc `null`.
 */

export interface BackendStatus {
  /** external = pornit de altcineva; starting / running / failed = pornit de aplicație; disabled = nu s-a încercat. */
  readonly state: "external" | "starting" | "running" | "failed" | "disabled";
  /** Explicația pe înțelesul utilizatorului (de ce nu a pornit, ce comandă s-a rulat). */
  readonly detail: string;
  readonly url: string;
}

interface DesktopBridge {
  readonly platform: string;
  readonly backendStatus: () => Promise<BackendStatus>;
}

declare global {
  interface Window {
    readonly shadowDesktop?: DesktopBridge;
  }
}

export const isDesktop = (): boolean => typeof window !== "undefined" && Boolean(window.shadowDesktop);

export async function getBackendStatus(): Promise<BackendStatus | null> {
  if (typeof window === "undefined" || !window.shadowDesktop) return null;
  try {
    return await window.shadowDesktop.backendStatus();
  } catch {
    return null;
  }
}
