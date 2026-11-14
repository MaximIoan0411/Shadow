"use client";
/**
 * Ecranul ofițerului medical: alertele de nivel 2 și 3 din tot echipajul (cele mai grave întâi), starea
 * generală a fiecărui membru și legătura cu Pământul. Alerta escaladată de un astronaut apare aici singură,
 * prin evenimentele live.
 */
import { useRouter } from "next/navigation";
import { useEffect, useState, type ReactElement } from "react";
import { AlertList } from "@/components/alerts/AlertList";
import { Page } from "@/components/layout/Shell";
import { LinkConsole } from "@/components/link/LinkConsole";
import { ButtonLink, Card, EmptyState, LevelTag, ProblemCard, SectionTitle, Skeleton, StatusBadge } from "@/components/ui";
import { Tabs } from "@/components/ui/overlays";
import { errorMessage } from "@/lib/api";
import { useCmoQueue, useCrewList } from "@/lib/queries";
import { HOME_BY_ROLE, useSession } from "@/lib/session";

type View = "queue" | "link";
const CMO_ROLE = "cmo";

function Queue(): ReactElement {
  const queue = useCmoQueue(true);
  const crew = useCrewList(true);
  const names = new Map(crew.data?.map((row) => [row.member.id, row.member.display_name]));

  return (
    <div className="grid items-start gap-5 xl:grid-cols-[minmax(0,1fr)_400px]">
      <Card as="section" aria-labelledby="queue-title">
        <SectionTitle id="queue-title">Alerts waiting for you</SectionTitle>
        {queue.isPending && <Skeleton className="h-28 rounded-2xl" />}
        {queue.isError && <ProblemCard title="The queue could not be loaded" detail={errorMessage(queue.error)} onRetry={() => void queue.refetch()} />}
        {queue.isSuccess && !queue.data.length && <EmptyState title="No level 2 or 3 alerts">When an astronaut notifies you, the alert appears here without reloading.</EmptyState>}
        {queue.data && <AlertList alerts={queue.data} crewNames={names} />}
      </Card>

      <Card as="section" aria-labelledby="crew-title">
        <SectionTitle id="crew-title">Crew</SectionTitle>
        {crew.isPending && <Skeleton className="h-40 rounded-2xl" />}
        {crew.isError && <ProblemCard title="The crew could not be loaded" detail={errorMessage(crew.error)} onRetry={() => void crew.refetch()} />}
        <ul className="flex flex-col">
          {crew.data?.map((row) => (
            <li key={row.member.id} className="flex items-center gap-3 border-b border-line py-3 first:pt-0 last:border-b-0 last:pb-0">
              <span aria-hidden="true" className="grid size-9 shrink-0 place-items-center rounded-full bg-surface-4 text-small font-semibold text-fg">
                {row.member.initials}
              </span>
              <span className="min-w-0 flex-1">
                <span className="block truncate text-body font-medium text-fg">{row.member.display_name}</span>
                <span className="mt-0.5 flex flex-wrap items-center gap-2 text-small text-fg-3">
                  <StatusBadge status={row.overall_status} compact />
                  {Boolean(row.active_alerts) && <span>{row.active_alerts} open alerts</span>}
                  {row.highest_level && <LevelTag level={row.highest_level} />}
                </span>
              </span>
              <ButtonLink href={`/dashboard?crew=${row.member.id}`} size="sm" variant="ghost">
                View body
              </ButtonLink>
            </li>
          ))}
        </ul>
        <p className="mt-4 text-small leading-relaxed text-fg-4">Only the overall status is shown here. When you open a crew member's data, the access is written to a log they can read.</p>
      </Card>
    </div>
  );
}

export default function CmoPage(): ReactElement | null {
  const { user } = useSession();
  const router = useRouter();
  const [view, setView] = useState<View>("queue");
  const allowed = user?.role === CMO_ROLE;

  useEffect(() => {
    if (user && !allowed) router.replace(HOME_BY_ROLE[user.role]);
  }, [user, allowed, router]);

  if (!user || !allowed) return null;
  return (
    <Page>
      <Tabs<View>
        label="Medical officer screens"
        value={view}
        onChange={setView}
        items={[
          { value: "queue", label: "Medical queue", content: <Queue /> },
          { value: "link", label: "Earth link", content: <LinkConsole role={user.role} /> },
        ]}
      />
    </Page>
  );
}
