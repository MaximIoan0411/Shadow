"use client";
/**
 * Sesiunea: cine e autentificat pe această stație de lucru. Fiecare astronaut are contul lui.
 *
 * Tokenul și utilizatorul stau doar în memorie (nu în localStorage): la reîncărcare sau la închiderea ferestrei
 * sesiunea dispare. Fiecare fereastră a aplicației are sesiunea ei, deci nava și Pământul pot sta alături.
 */
import { useQueryClient } from "@tanstack/react-query";
import { useRouter } from "next/navigation";
import { createContext, useCallback, useContext, useEffect, useMemo, useRef, useState, type ReactElement, type ReactNode } from "react";
import { setToken, setUnauthorizedHandler, type Schemas, type User } from "./api";
import * as api from "./endpoints";

type Role = Schemas["Role"];
type Cleanup = () => void | Promise<void>;

interface SessionValue {
  readonly user: User | null;
  /** Membrul de echipaj al contului; `null` pentru rolul `earth` și când nu e nimeni autentificat. */
  readonly crewId: string | null;
  readonly login: (username: string, password: string) => Promise<User>;
  /** „Schimbă astronautul”: oprește colectoarele, închide evenimentele, deconectează, golește datele. */
  readonly logout: () => Promise<void>;
  /** Înscrie ceva de oprit înainte de deconectare (colectorul de tastare, fluxul de evenimente). */
  readonly onBeforeLogout: (cleanup: Cleanup) => () => void;
}

export const LOGIN_PATH = "/login";

export const HOME_BY_ROLE = {
  astronaut: "/dashboard",
  cmo: "/cmo",
  earth: "/mission-control",
} as const satisfies Record<Role, string>;

const SessionContext = createContext<SessionValue | null>(null);

export function useSession(): SessionValue {
  const value = useContext(SessionContext);
  if (!value) throw new Error("useSession must be used inside <SessionProvider>.");
  return value;
}

export function SessionProvider({ children }: { readonly children: ReactNode }): ReactElement {
  const [user, setUser] = useState<User | null>(null);
  const cleanups = useRef(new Set<Cleanup>());
  const queryClient = useQueryClient();
  const router = useRouter();

  /** Șterge tot ce ține de contul curent, ca pe ecran să nu rămână nimic pentru următorul astronaut. */
  const forget = useCallback((): void => {
    setToken(null);
    queryClient.clear();
    setUser(null);
    router.replace(LOGIN_PATH);
  }, [queryClient, router]);

  useEffect(() => {
    setUnauthorizedHandler(forget);
    return () => setUnauthorizedHandler(null);
  }, [forget]);

  const login = useCallback(async (username: string, password: string): Promise<User> => {
    const response = await api.login({ username, password });
    setToken(response.access_token);
    setUser(response.user);
    return response.user;
  }, []);

  const logout = useCallback(async (): Promise<void> => {
    await Promise.allSettled([...cleanups.current].map(async (cleanup) => cleanup()));
    try {
      await api.logout();
    } catch {
      // Deconectarea locală are loc oricum: un server care nu răspunde nu trebuie să țină sesiunea deschisă.
    }
    forget();
  }, [forget]);

  const onBeforeLogout = useCallback((cleanup: Cleanup): (() => void) => {
    cleanups.current.add(cleanup);
    return () => {
      cleanups.current.delete(cleanup);
    };
  }, []);

  const value = useMemo<SessionValue>(
    () => ({ user, crewId: user?.crew_id ?? null, login, logout, onBeforeLogout }),
    [user, login, logout, onBeforeLogout],
  );

  return <SessionContext.Provider value={value}>{children}</SessionContext.Provider>;
}
