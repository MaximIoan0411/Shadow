"use client";
/**
 * Alerta completă și planul ei: ce s-a observat, dovezile, cauza, recomandarea din catalog (cu sursă), pașii,
 * istoricul și, dacă a ajuns acolo, răspunsul Pământului. Butoanele depind de rol și de nivel, după tabelul
 * din contract; backend-ul verifică oricum fiecare acțiune.
 */
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { useState, type ReactElement, type ReactNode } from "react";
import { AiChat } from "@/components/ai/AiChat";
import { SourceLine } from "@/components/body/ZonePanel";
import { Button, Card, Checkbox, Field, LevelTag, Notice, ProblemCard, SectionTitle, Segmented, Skeleton, StatusBadge, Tag, Textarea } from "@/components/ui";
import { Dialog } from "@/components/ui/overlays";
import { errorMessage, type Schemas } from "@/lib/api";
import * as api from "@/lib/endpoints";
import { formatDateTime, formatDuration, formatNumber } from "@/lib/format";
import { keys, useAlert, useMission } from "@/lib/queries";
import { ALERT_STATE_LABEL, LEVEL_CMO, LEVEL_EARTH, TOPIC_META } from "@/lib/status";
import { useToast } from "@/lib/toast";

type Alert = Schemas["Alert"];
type Role = Schemas["Role"];
type Outcome = Schemas["ResolveRequest"]["outcome"];
type EscalateLevel = Schemas["EscalateRequest"]["to_level"];
type HistoryAction = Alert["history"][number]["action"];

const HISTORY_LABEL = {
  created: "Alert created",
  acknowledged: "Seen",
  step_done: "Step ticked",
  escalated: "Escalated",
  packet_sent: "Packet sent to Earth",
  earth_replied: "Reply arrived from Earth",
  rechecked: "Rechecked by SHADOW",
  resolved: "Closed",
} as const satisfies Record<HistoryAction, string>;

const CAUSE_LABEL = {
  individual: "Individual cause",
  environmental: "Environmental cause: several crew members",
  unknown: "Unknown cause",
} as const satisfies Record<Alert["cause"], string>;

const OUTCOMES = [
  { value: "resolved", label: "Resolved" },
  { value: "false_alarm", label: "False alarm" },
  { value: "monitoring", label: "Still monitoring" },
] as const satisfies readonly { readonly value: Outcome; readonly label: string }[];

const NOTE_MAX = 500;
const RESOLVED = "resolved";
const ACTIVE = "active";
const CMO: Role = "cmo";

function Block({ title, right, children }: { readonly title: string; readonly right?: ReactNode; readonly children: ReactNode }): ReactElement {
  return (
    <section className="border-b border-line py-5 first:pt-0 last:border-b-0 last:pb-0">
      <div className="mb-2.5 flex items-center justify-between gap-3">
        <h3 className="text-caption font-medium uppercase tracking-[0.06em] text-fg-4">{title}</h3>
        {right}
      </div>
      {children}
    </section>
  );
}

/** Ce are voie contul curent să facă pe această alertă (tabelul „Butoanele, după rol” din contract). */
function permissions(alert: Alert, role: Role, ownCrewId: string | null): { readonly ack: boolean; readonly toCmo: boolean; readonly toEarth: boolean; readonly resolve: boolean } {
  const open = alert.state !== RESOLVED;
  const own = alert.crew_id === ownCrewId;
  const isCmo = role === CMO;
  return {
    ack: open && own && alert.state === ACTIVE,
    toCmo: open && own && alert.level < LEVEL_CMO,
    toEarth: open && isCmo && alert.level < LEVEL_EARTH,
    resolve: open && (isCmo || (own && alert.level < LEVEL_CMO)),
  };
}

function AlertBody({ alert, role, crewId }: { readonly alert: Alert; readonly role: Role; readonly crewId: string | null }): ReactElement {
  const queryClient = useQueryClient();
  const notify = useToast();
  const mission = useMission();
  const [escalateTo, setEscalateTo] = useState<EscalateLevel | null>(null);
  const [resolving, setResolving] = useState(false);
  const [note, setNote] = useState("");
  const [outcome, setOutcome] = useState<Outcome>("resolved");
  const topic = TOPIC_META[alert.topic];
  const can = permissions(alert, role, crewId);

  const onSaved = (next: Alert): void => {
    queryClient.setQueryData(keys.alert(next.id), next);
    void queryClient.invalidateQueries({ queryKey: keys.alerts });
    void queryClient.invalidateQueries({ queryKey: keys.crew(next.crew_id) });
    void queryClient.invalidateQueries({ queryKey: keys.link });
    setEscalateTo(null);
    setResolving(false);
    setNote("");
  };
  const onError = (error: unknown): void => {
    notify({ title: "The action failed", detail: errorMessage(error), status: "alert" });
    void queryClient.invalidateQueries({ queryKey: keys.alert(alert.id) });
  };

  const ack = useMutation({ mutationFn: () => api.ackAlert(alert.id), onSuccess: onSaved, onError });
  const step = useMutation({
    mutationFn: ({ stepId, done }: { readonly stepId: string; readonly done: boolean }) => api.setPlanStep(alert.id, stepId, done),
    onSuccess: onSaved,
    onError,
  });
  const escalate = useMutation({
    mutationFn: (toLevel: EscalateLevel) => api.escalateAlert(alert.id, { to_level: toLevel, note: note.trim() || null }),
    onSuccess: onSaved,
    onError,
  });
  const resolve = useMutation({
    mutationFn: () => api.resolveAlert(alert.id, { outcome, note: note.trim() || null }),
    onSuccess: onSaved,
    onError,
  });

  const delay = formatDuration(mission.data?.link.one_way_delay_s);
  const toEarth = escalateTo === LEVEL_EARTH;

  return (
    <div className="flex flex-col gap-5">
      <Card as="article" aria-labelledby="alert-title">
        <header className="mb-5">
          <p className="mb-2 flex flex-wrap items-center gap-2 text-small text-fg-3">
            <topic.icon size={14} strokeWidth={1.8} />
            {topic.label}
            <span className="text-fg-5">/</span>
            <span className="num">{formatDateTime(alert.created_at)}</span>
          </p>
          <h2 id="alert-title" className="text-title font-medium text-fg">
            {alert.title}
          </h2>
          <div className="mt-3 flex flex-wrap items-center gap-2">
            <StatusBadge status={alert.status} />
            <LevelTag level={alert.level} full />
            <Tag>{ALERT_STATE_LABEL[alert.state]}</Tag>
          </div>
        </header>

        <Block title="What was observed">
          <p className="text-lead leading-relaxed text-fg">{alert.explanation}</p>
        </Block>

        <Block title="Evidence">
          <ul className="grid gap-2.5 sm:grid-cols-3">
            {alert.evidence.map((item) => (
              <li key={item.metric_key} className="rounded-2xl border border-line bg-white/[0.02] p-3.5">
                <p className="text-small text-fg-3">{item.label}</p>
                <p className="mt-1.5 flex items-baseline gap-1.5">
                  <span className="text-display font-medium tracking-[-0.02em] text-fg">{formatNumber(item.value)}</span>
                  <span className="text-small text-fg-4">{item.unit}</span>
                </p>
                <p className="mt-2 text-small text-fg-2">{item.deviation_text}</p>
                {item.baseline !== null && item.baseline !== undefined && (
                  <p className="text-small text-fg-4">
                    your baseline <span className="num">{formatNumber(item.baseline)}</span>
                  </p>
                )}
              </li>
            ))}
          </ul>
        </Block>

        <Block title={CAUSE_LABEL[alert.cause]}>
          <p className="text-base leading-relaxed text-fg-2">{alert.cause_explanation}</p>
        </Block>

        <Block title="What to do" right={<Tag>from the catalog: {alert.recommendation.id}</Tag>}>
          <p className="text-base leading-relaxed text-fg">{alert.recommendation.action}</p>
          <p className="mt-2 text-small leading-relaxed text-fg-3">Applies when: {alert.recommendation.trigger}</p>
          <ul className="mt-3 flex flex-col gap-2">
            <SourceLine source={alert.recommendation.source} />
            <li className="text-small text-fg-3">
              NASA risk tracked:{" "}
              <a href={alert.recommendation.hrp_risk_url} target="_blank" rel="noreferrer">
                {alert.recommendation.hrp_risk}
              </a>
            </li>
          </ul>
        </Block>

        {Boolean(alert.plan_steps.length) && (
          <Block title="The plan, step by step">
            <div className="-mx-2 flex flex-col">
              {alert.plan_steps.map((item) => (
                <Checkbox key={item.id} checked={item.done} disabled={alert.state === RESOLVED || step.isPending} onChange={(done) => step.mutate({ stepId: item.id, done })}>
                  {item.text}
                </Checkbox>
              ))}
            </div>
            {alert.recheck_at && <p className="mt-3 text-small text-fg-3">SHADOW checks whether the plan worked on {formatDateTime(alert.recheck_at)}.</p>}
          </Block>
        )}

        {(alert.packet_id || alert.earth_reply) && (
          <Block title="Earth link">
            {alert.earth_reply ? (
              <Notice tone="ok" title="Reply from the flight surgeon on Earth">
                <span className="text-base text-fg">{alert.earth_reply}</span>
              </Notice>
            ) : (
              <Notice title={`The alert left for Earth in packet ${alert.packet_id}`}>The trip takes {delay} one way. The reply appears here when it arrives.</Notice>
            )}
          </Block>
        )}

        {(can.ack || can.toCmo || can.toEarth || can.resolve) && (
          <div className="flex flex-wrap gap-2 pt-5">
            {can.ack && (
              <Button variant="primary" busy={ack.isPending} onClick={() => ack.mutate()}>
                I've seen it
              </Button>
            )}
            {can.toCmo && <Button onClick={() => setEscalateTo(LEVEL_CMO)}>Notify the medical officer</Button>}
            {can.toEarth && <Button onClick={() => setEscalateTo(LEVEL_EARTH)}>Send to Earth</Button>}
            {can.resolve && (
              <Button variant="ghost" onClick={() => setResolving(true)}>
                Close alert
              </Button>
            )}
          </div>
        )}
      </Card>

      {alert.crew_id === crewId && <AiChat crewId={alert.crew_id} alertId={alert.id} title="Ask the AI doctor about this alert" variant="embedded" />}

      <Card as="section" aria-labelledby="history-title">
        <SectionTitle id="history-title">Alert history</SectionTitle>
        <ol className="flex flex-col">
          {alert.history.map((entry) => (
            <li key={`${entry.at}-${entry.action}`} className="flex flex-wrap items-baseline gap-x-3 gap-y-0.5 border-b border-line py-2.5 first:pt-0 last:border-b-0 last:pb-0">
              <span className="num w-28 shrink-0 text-small text-fg-4">{formatDateTime(entry.at)}</span>
              <span className="text-body text-fg">{HISTORY_LABEL[entry.action]}</span>
              <span className="text-small text-fg-3">{entry.actor}</span>
              {entry.note && <span className="w-full pl-[124px] text-small text-fg-3">{entry.note}</span>}
            </li>
          ))}
        </ol>
      </Card>

      <Dialog
        open={escalateTo !== null}
        onClose={() => setEscalateTo(null)}
        title={toEarth ? "Send this alert to Earth?" : "Notify the medical officer?"}
        footer={
          <>
            <Button variant="ghost" onClick={() => setEscalateTo(null)}>
              Cancel
            </Button>
            <Button variant="primary" busy={escalate.isPending} onClick={() => escalateTo && escalate.mutate(escalateTo)}>
              {toEarth ? "Send to Earth" : "Notify the medical officer"}
            </Button>
          </>
        }
      >
        <p>
          {toEarth
            ? `The alert leaves signed and encrypted. It reaches the flight surgeon after ${delay}, and the reply makes the same trip back.`
            : "The crew medical officer will see this alert, with its evidence and plan."}
        </p>
        <Field id="escalate-note" label="Note (optional)" className="mt-4">
          <Textarea id="escalate-note" maxLength={NOTE_MAX} value={note} onChange={(event) => setNote(event.target.value)} />
        </Field>
      </Dialog>

      <Dialog
        open={resolving}
        onClose={() => setResolving(false)}
        title="Close this alert?"
        footer={
          <>
            <Button variant="ghost" onClick={() => setResolving(false)}>
              Cancel
            </Button>
            <Button variant="primary" busy={resolve.isPending} onClick={() => resolve.mutate()}>
              Close alert
            </Button>
          </>
        }
      >
        <p className="mb-3">Choose how it ended. “Still monitoring” keeps it open and moves the recheck back by a day.</p>
        <Segmented<Outcome> label="How it ended" value={outcome} options={OUTCOMES} onChange={setOutcome} />
        <Field id="resolve-note" label="Note (optional)" className="mt-4">
          <Textarea id="resolve-note" maxLength={NOTE_MAX} value={note} onChange={(event) => setNote(event.target.value)} />
        </Field>
      </Dialog>
    </div>
  );
}

export function AlertDetail({ alertId, role, crewId }: { readonly alertId: string; readonly role: Role; readonly crewId: string | null }): ReactElement {
  const alert = useAlert(alertId);
  return (
    <>
      {alert.isPending && <Skeleton className="h-[560px] rounded-[var(--radius-card)]" />}
      {alert.isError && <ProblemCard title="The alert could not be loaded" detail={errorMessage(alert.error)} onRetry={() => void alert.refetch()} />}
      {alert.data && <AlertBody alert={alert.data} role={role} crewId={crewId} />}
    </>
  );
}
