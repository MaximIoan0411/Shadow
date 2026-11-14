"use client";
/**
 * Ecranul astronautului: corpul interactiv, decalajul de percepție și ce e de făcut azi.
 * Un singur apel aduce tot (`GET /crew/{id}/dashboard`); derulatorul îl repetă cu `as_of_day`.
 * Ofițerul medical poate deschide ecranul altui membru cu `?crew=cm-2` (accesul se scrie în jurnal).
 */
import { Check, Circle } from "lucide-react";
import { useSearchParams } from "next/navigation";
import { useState, type ReactElement } from "react";
import { BodyFigure } from "@/components/body/BodyFigure";
import { PerceptionGapCard } from "@/components/body/PerceptionGap";
import { ZonePanel } from "@/components/body/ZonePanel";
import { MissionTimeline } from "@/components/layout/MissionTimeline";
import { Page } from "@/components/layout/Shell";
import { ButtonLink, Card, LevelTag, Notice, ProblemCard, SectionTitle, Skeleton, Tag } from "@/components/ui";
import { errorMessage, type Schemas } from "@/lib/api";
import { formatDateTime, formatPercent, formatTime } from "@/lib/format";
import { useDashboard, useMessages, useMission, useTimeline } from "@/lib/queries";
import { useSession } from "@/lib/session";
import { PILLAR_META, type Pillar } from "@/lib/status";

type Dashboard = Schemas["Dashboard"];

const CREW_PARAM = "crew";
const CMO_ROLE = "cmo";
const MAX_MESSAGES = 3;

function TopAlert({ alert }: { readonly alert: Schemas["AlertBrief"] }): ReactElement {
  return (
    <Notice
      tone={alert.status === "alert" ? "alert" : "watch"}
      title={alert.title}
      action={
        <ButtonLink href={`/alerts?id=${alert.id}`} size="sm">
          See the plan
        </ButtonLink>
      }
    >
      <span className="flex flex-wrap items-center gap-2">
        <LevelTag level={alert.level} full />
        <span>since {formatDateTime(alert.created_at)}</span>
      </span>
    </Notice>
  );
}

function CrossSignals({ signals }: { readonly signals: Dashboard["cross_signals"] }): ReactElement | null {
  if (!signals.length) return null;
  return (
    <Card as="section" aria-labelledby="cross-title">
      <SectionTitle id="cross-title">Signals that connect</SectionTitle>
      <div className="flex flex-col gap-4">
        {signals.map((signal) => (
          <div key={signal.id}>
            <div className="flex flex-wrap items-center justify-between gap-2">
              <p className="text-base font-medium text-fg">{signal.title}</p>
              <Tag>confidence {formatPercent(signal.confidence)}</Tag>
            </div>
            <p className="mt-1 text-body leading-relaxed text-fg-3">{signal.explanation}</p>
            <ul className="mt-2 flex flex-wrap gap-1.5">
              {signal.signals.map((item) => (
                <li key={item}>
                  <Tag>{item}</Tag>
                </li>
              ))}
            </ul>
            <p className="mt-2 flex flex-wrap items-center gap-3 text-small text-fg-4">
              {signal.pillars.map((pillar) => {
                const Icon = PILLAR_META[pillar].icon;
                return (
                  <span key={pillar} className="flex items-center gap-1.5">
                    <Icon size={13} strokeWidth={1.8} />
                    {PILLAR_META[pillar].zone}
                  </span>
                );
              })}
            </p>
          </div>
        ))}
      </div>
    </Card>
  );
}

function Today({ dashboard }: { readonly dashboard: Dashboard }): ReactElement {
  return (
    <Card as="section" aria-labelledby="today-title">
      <SectionTitle id="today-title">Today</SectionTitle>
      <ul className="flex flex-col">
        {dashboard.reminders.map((reminder) => (
          <li key={reminder.id} className="flex items-center gap-3 border-b border-line py-2.5 first:pt-0 last:border-b-0">
            {reminder.done ? <Check size={15} strokeWidth={2.2} className="shrink-0 text-fg-3" aria-label="Done" /> : <Circle size={15} strokeWidth={1.8} className="shrink-0 text-fg-5" aria-label="To do" />}
            <span className={reminder.done ? "flex-1 text-body text-fg-4 line-through decoration-fg-5" : "flex-1 text-body text-fg"}>{reminder.label}</span>
            {reminder.overdue && !reminder.done && <Tag>overdue</Tag>}
            <span className="num text-small text-fg-4">{formatTime(reminder.due_at)}</span>
          </li>
        ))}
      </ul>
      <dl className="mt-4 grid grid-cols-3 gap-2">
        {dashboard.streaks.map((streak) => (
          <div key={streak.key} className="rounded-2xl border border-line bg-white/[0.02] p-3">
            <dt className="text-caption leading-snug text-fg-4">{streak.label}</dt>
            <dd className="mt-1.5 text-fg">
              <span className="text-title font-medium">{streak.days}</span> <span className="text-small text-fg-3">days in a row</span>
              <span className="mt-0.5 block text-caption text-fg-4">best {streak.best}</span>
            </dd>
          </div>
        ))}
      </dl>
    </Card>
  );
}

function EarthMessages({ crewId }: { readonly crewId: string }): ReactElement | null {
  const messages = useMessages(crewId);
  if (!messages.data?.length) return null;
  return (
    <Card as="section" aria-labelledby="messages-title">
      <SectionTitle id="messages-title">Arrived from Earth</SectionTitle>
      <ul className="flex flex-col gap-3">
        {messages.data.slice(0, MAX_MESSAGES).map((message) => (
          <li key={message.packet_id} className="rounded-2xl border border-line bg-white/[0.02] p-3">
            <p className="flex flex-wrap items-center justify-between gap-2 text-small text-fg-3">
              <span className="font-medium text-fg-2">{message.sender}</span>
              <span className="num">arrived {formatDateTime(message.delivered_at)}</span>
            </p>
            <p className="mt-1.5 text-base leading-relaxed text-fg">{message.body}</p>
            {message.alert_id && (
              <ButtonLink href={`/alerts?id=${message.alert_id}`} size="sm" variant="ghost" className="-ml-3 mt-1">
                Open alert
              </ButtonLink>
            )}
          </li>
        ))}
      </ul>
    </Card>
  );
}

function DashboardSkeleton(): ReactElement {
  return (
    <div className="grid items-start gap-5 xl:grid-cols-[minmax(0,1fr)_400px]">
      <Skeleton className="h-[560px] rounded-[var(--radius-card)]" />
      <div className="flex flex-col gap-5">
        <Skeleton className="h-[300px] rounded-[var(--radius-card)]" />
        <Skeleton className="h-[240px] rounded-[var(--radius-card)]" />
      </div>
    </div>
  );
}

export default function DashboardPage(): ReactElement {
  const { user, crewId: ownCrewId } = useSession();
  const requestedCrew = useSearchParams().get(CREW_PARAM);
  const crewId = user?.role === CMO_ROLE && requestedCrew ? requestedCrew : ownCrewId;
  const viewingOther = crewId !== ownCrewId;

  const [asOfDay, setAsOfDay] = useState<number | null>(null);
  const [pillar, setPillar] = useState<Pillar | null>(null);
  const mission = useMission();
  const dashboard = useDashboard(crewId, asOfDay ?? undefined);
  const timeline = useTimeline(crewId);
  const data = dashboard.data;

  return (
    <Page>
      {viewingOther && data && (
        <Notice title={`Viewing data for ${data.crew.display_name}`} action={<ButtonLink href="/cmo" size="sm">Back to the queue</ButtonLink>}>
          Your access to another crew member's data is written to the access log.
        </Notice>
      )}
      {asOfDay !== null && (
        <Notice title={`Viewing day ${asOfDay} from history`}>Values, zone colours and panels are the ones from that day. Plans cannot be ticked in history.</Notice>
      )}
      {data?.top_alert && asOfDay === null && <TopAlert alert={data.top_alert} />}

      {dashboard.isPending && <DashboardSkeleton />}
      {dashboard.isError && <ProblemCard title="The dashboard could not be loaded" detail={errorMessage(dashboard.error)} onRetry={() => void dashboard.refetch()} />}

      {data && crewId && (
        <div className="grid items-start gap-5 xl:grid-cols-[minmax(0,1fr)_400px]">
          <div className="flex min-w-0 flex-col gap-5">
            <Card as="section" aria-label="Your body, by zone" className="py-6">
              <BodyFigure pillars={data.pillars} selected={pillar} onSelect={setPillar} />
            </Card>
            {timeline.data && mission.data && (
              <MissionTimeline
                days={timeline.data.days}
                totalDays={mission.data.total_days}
                currentDay={mission.data.mission_day}
                selectedDay={asOfDay}
                onSelect={setAsOfDay}
              />
            )}
          </div>
          <div className="flex flex-col gap-5">
            <PerceptionGapCard gap={data.perception_gap} canCheckIn={!viewingOther && asOfDay === null} />
            <CrossSignals signals={data.cross_signals} />
            <Today dashboard={data} />
            {asOfDay === null && <EarthMessages crewId={crewId} />}
          </div>
        </div>
      )}

      {crewId && (
        <ZonePanel
          crewId={crewId}
          pillar={pillar}
          asOfDay={asOfDay ?? undefined}
          summary={data?.pillars.find((summary) => summary.pillar === pillar)}
          onClose={() => setPillar(null)}
        />
      )}
    </Page>
  );
}
