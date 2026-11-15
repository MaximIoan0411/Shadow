"use client";
/**
 * Alertele contului: lista în stânga, alerta aleasă în dreapta (`/alerts?id=al-1042`).
 * Ofițerul medical ajunge aici și din coada lui, cu alerta altui membru al echipajului.
 */
import { useSearchParams } from "next/navigation";
import { useEffect, useRef, type ReactElement } from "react";
import { AlertDetail } from "@/components/alerts/AlertDetail";
import { AlertList, sortAlerts } from "@/components/alerts/AlertList";
import { Page } from "@/components/layout/Shell";
import { SummaryOutbox } from "@/components/link/SummaryOutbox";
import { Card, EmptyState, ProblemCard, SectionTitle, Skeleton } from "@/components/ui";
import { errorMessage } from "@/lib/api";
import { useAlerts } from "@/lib/queries";
import { useSession } from "@/lib/session";

const ID_PARAM = "id";
const RESOLVED = "resolved";
/** Sub această lățime lista și alerta stau una sub alta (vezi `xl:grid-cols` mai jos). */
const STACKED = "(max-width: 1279px)";

export default function AlertsPage(): ReactElement | null {
  const { user, crewId } = useSession();
  const requestedId = useSearchParams().get(ID_PARAM);
  const alerts = useAlerts(crewId);
  const detailRef = useRef<HTMLDivElement>(null);

  // pe ecran îngust alerta aleasă e sub listă: o aducem în ecran, altfel atingerea pare să nu facă nimic
  useEffect(() => {
    if (requestedId && window.matchMedia(STACKED).matches) detailRef.current?.scrollIntoView({ behavior: "smooth", block: "start" });
  }, [requestedId]);

  if (!user) return null;

  const list = alerts.data ?? [];
  const open = list.filter((alert) => alert.state !== RESOLVED);
  const closed = list.filter((alert) => alert.state === RESOLVED);
  const selectedId = requestedId ?? sortAlerts(open)[0]?.id ?? null;

  return (
    <Page>
      <div className="grid items-start gap-5 xl:grid-cols-[360px_minmax(0,1fr)]">
        <div className="flex flex-col gap-5">
          <Card as="section" aria-labelledby="alerts-open">
            <SectionTitle id="alerts-open">Your open alerts</SectionTitle>
            {alerts.isPending && <Skeleton className="h-28 rounded-2xl" />}
            {alerts.isError && <ProblemCard title="The alerts could not be loaded" detail={errorMessage(alerts.error)} onRetry={() => void alerts.refetch()} />}
            {alerts.isSuccess && !open.length && <EmptyState title="No open alerts">All your values are within your in-flight baseline.</EmptyState>}
            <AlertList alerts={open} selectedId={selectedId} />
            {Boolean(closed.length) && (
              <div className="mt-5">
                <SectionTitle>Closed</SectionTitle>
                <AlertList alerts={closed} selectedId={selectedId} />
              </div>
            )}
          </Card>
          {crewId && <SummaryOutbox crewId={crewId} />}
        </div>
        <div ref={detailRef} className="min-w-0 scroll-mt-4">
          {selectedId ? (
            <AlertDetail key={selectedId} alertId={selectedId} role={user.role} crewId={crewId} />
          ) : (
            alerts.isSuccess && <EmptyState title="Pick an alert from the list">Its evidence, action plan and history appear here.</EmptyState>
          )}
        </div>
      </div>
    </Page>
  );
}
