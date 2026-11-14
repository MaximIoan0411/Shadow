"use client";
/**
 * Cadrul complet al unui cont autentificat: păzește accesul după rol, ține abonamentul la evenimente și pune
 * în jurul ecranului bara laterală, antetul, banner-ul de radiații și panoul de demo.
 */
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { usePathname, useRouter } from "next/navigation";
import { Suspense, useEffect, useState, type ReactElement, type ReactNode } from "react";
import { RadiationBanner } from "@/components/radiation/RadiationBanner";
import { errorMessage, type Schemas } from "@/lib/api";
import { setEnvironment } from "@/lib/endpoints";
import { EventsProvider, useEvents } from "@/lib/events";
import { useHotkey } from "@/lib/hooks";
import { keys, useAlerts, useEnvironments, useMission, useRadiationStatus } from "@/lib/queries";
import { HOME_BY_ROLE, LOGIN_PATH, useSession } from "@/lib/session";
import { statusRank } from "@/lib/status";
import { useToast } from "@/lib/toast";
import { DemoPanel } from "./DemoPanel";
import { Backdrop, Header, Sidebar, navFor } from "./Shell";

type Role = Schemas["Role"];

const TITLES: Readonly<Record<string, string>> = {
  "/dashboard": "My body",
  "/checkin": "Morning check-in",
  "/rhythm": "Rhythm and reaction",
  "/exercise": "Exercise",
  "/alerts": "Alerts",
  "/ai": "AI doctor",
  "/radiation": "Radiation",
  "/evidence": "Evidence",
  "/cmo": "Medical queue",
  "/mission-control": "Mission control",
  "/mission-control/evidence": "Evidence",
};

const SHIP_ROLES: readonly Role[] = ["astronaut", "cmo"];
const DEMO_KEY = "KeyD";
const OPEN_STATES: readonly Schemas["AlertState"][] = ["active", "acknowledged", "escalated"];

const trimSlash = (pathname: string): string => (pathname.length > 1 && pathname.endsWith("/") ? pathname.slice(0, -1) : pathname);

function Frame({ user, children }: { readonly user: Schemas["User"]; readonly children: ReactNode }): ReactElement {
  const { logout } = useSession();
  const { connection } = useEvents();
  const pathname = trimSlash(usePathname());
  const queryClient = useQueryClient();
  const notify = useToast();
  const [collapsed, setCollapsed] = useState(false);
  const [demoOpen, setDemoOpen] = useState(false);
  const onShip = SHIP_ROLES.includes(user.role);

  const mission = useMission();
  const environments = useEnvironments();
  const alerts = useAlerts(onShip ? (user.crew_id ?? null) : null);
  const radiation = useRadiationStatus(onShip);

  const changeEnvironment = useMutation({
    mutationFn: setEnvironment,
    onSuccess: (next) => {
      queryClient.setQueryData(keys.mission, next);
      void queryClient.invalidateQueries({ queryKey: keys.link });
    },
    onError: (error) => notify({ title: "The environment did not change", detail: errorMessage(error), status: "alert" }),
  });

  useHotkey(
    (event) => event.ctrlKey && event.shiftKey && event.code === DEMO_KEY,
    () => setDemoOpen((open) => !open),
  );

  const openAlerts = (alerts.data ?? []).filter((alert) => OPEN_STATES.includes(alert.state));
  const worst = openAlerts.reduce<Schemas["Status"]>((current, alert) => (statusRank(alert.status) > statusRank(current) ? alert.status : current), "unknown");
  const items = navFor(user.role, { count: openAlerts.length, status: worst });
  const stormActive = Boolean(radiation.data?.alert_active);

  return (
    <div className="relative flex h-full overflow-hidden bg-bg">
      <Sidebar
        items={items}
        account={{ username: user.username, displayName: user.display_name, initials: user.initials, role: user.role }}
        collapsed={collapsed}
        onToggle={() => setCollapsed((value) => !value)}
        onSwitchAccount={() => void logout()}
      />
      <div className="relative flex min-w-0 flex-1 flex-col">
        <Backdrop alert={stormActive} />
        <div className="relative z-10 flex min-h-0 flex-1 flex-col">
          <Header
            title={TITLES[pathname] ?? "SHADOW"}
            mission={mission.data}
            environments={environments.data}
            onEnvironmentChange={onShip ? (id) => changeEnvironment.mutate(id) : undefined}
            reconnecting={connection === "lost"}
            onOpenDemo={() => setDemoOpen(true)}
          />
          {radiation.data && <RadiationBanner status={radiation.data} />}
          <main className="flex min-h-0 flex-1 flex-col">
            <Suspense fallback={null}>{children}</Suspense>
          </main>
        </div>
      </div>
      <DemoPanel open={demoOpen} onClose={() => setDemoOpen(false)} mission={mission.data} />
    </div>
  );
}

/**
 * Învelește ecranele unei zone a aplicației. `area` spune cui îi aparține zona: nava (astronaut, ofițer medical)
 * sau Pământul. Un cont din cealaltă zonă e trimis la ecranul lui; fără cont, la autentificare.
 */
export function AppShell({ area, children }: { readonly area: "ship" | "earth"; readonly children: ReactNode }): ReactElement | null {
  const { user } = useSession();
  const router = useRouter();
  const allowed = user ? (area === "ship") === SHIP_ROLES.includes(user.role) : false;

  useEffect(() => {
    if (!user) router.replace(LOGIN_PATH);
    else if (!allowed) router.replace(HOME_BY_ROLE[user.role]);
  }, [user, allowed, router]);

  if (!user || !allowed) return null;
  return (
    <EventsProvider>
      <Frame user={user}>{children}</Frame>
    </EventsProvider>
  );
}
