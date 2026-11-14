"use client";
/**
 * Pilonul Încărcarea: sesiunile de exerciții de azi, scorul de încărcare osoasă față de țintă și proiecția
 * pierderii osoase (o estimare, nu o măsurătoare). Scorurile le calculează backend-ul.
 */
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { Plus, Trash2 } from "lucide-react";
import { useState, type FormEvent, type ReactElement } from "react";
import { Page } from "@/components/layout/Shell";
import { Button, Card, Field, IconButton, Input, Meter, Notice, ProblemCard, SectionTitle, Segmented, Skeleton, Tag } from "@/components/ui";
import { errorMessage, type Schemas } from "@/lib/api";
import { addExerciseSession } from "@/lib/endpoints";
import { formatNumber, formatTime } from "@/lib/format";
import { keys, useExerciseToday, useMission } from "@/lib/queries";
import { useSession } from "@/lib/session";

type ExerciseToday = Schemas["ExerciseToday"];
type Kind = Schemas["ExerciseSessionCreate"]["kind"];

interface SetDraft {
  readonly id: number;
  readonly exercise: string;
  readonly reps: string;
  readonly load: string;
}

const KINDS = [
  { value: "resistance", label: "Resistance" },
  { value: "aerobic", label: "Aerobic" },
] as const satisfies readonly { readonly value: Kind; readonly label: string }[];

const KIND_LABEL = { resistance: "Resistance", aerobic: "Aerobic" } as const satisfies Record<Kind, string>;
const SIMULATED = "simulated";
const TWO_DECIMALS = 2;
const DEFAULT_DURATION = "40";
const EMPTY_SET = { exercise: "", reps: "", load: "" } as const;

const toNumber = (text: string): number => Number(text.trim().replace(",", "."));

function Summary({ today }: { readonly today: ExerciseToday }): ReactElement {
  return (
    <Card as="section" aria-labelledby="loading-title">
      <SectionTitle id="loading-title" right={<Tag>{`${today.completed_sessions} of ${today.planned_sessions} sessions`}</Tag>}>
        Today's loading
      </SectionTitle>
      <p className="flex items-baseline gap-2">
        <span className="text-hero font-medium tracking-[-0.03em] text-fg">{formatNumber(today.loading_score, 0)}</span>
        <span className="text-body text-fg-3">of a target of {formatNumber(today.loading_target, 0)}</span>
      </p>
      <Meter className="mt-4" value={today.loading_score} max={today.loading_target} label="Loading score against the target" />
      {today.split_recommended && (
        <Notice className="mt-4" title="Split the workout">
          {today.recommendation_text}
        </Notice>
      )}
      <p className="mt-4 text-small text-fg-3">
        {today.streak.label}: <span className="num text-fg">{today.streak.days}</span> days in a row, best <span className="num text-fg-2">{today.streak.best}</span>.
      </p>
    </Card>
  );
}

function Projection({ projection }: { readonly projection: ExerciseToday["projection"] }): ReactElement {
  return (
    <Card as="section" aria-labelledby="projection-title">
      <SectionTitle id="projection-title" right={<Tag>estimate</Tag>}>
        Bone density, projection per month
      </SectionTitle>
      <dl className="grid grid-cols-2 gap-2.5">
        <div className="rounded-2xl border border-line bg-white/[0.02] p-3.5">
          <dt className="text-small text-fg-3">With the current plan</dt>
          <dd className="mt-1.5 text-display font-medium tracking-[-0.02em] text-fg">{formatNumber(projection.current_plan_pct_month, TWO_DECIMALS)}%</dd>
        </div>
        <div className="rounded-2xl border border-line bg-white/[0.02] p-3.5">
          <dt className="text-small text-fg-3">With split training</dt>
          <dd className="mt-1.5 text-display font-medium tracking-[-0.02em] text-fg">{formatNumber(projection.split_plan_pct_month, TWO_DECIMALS)}%</dd>
        </div>
      </dl>
      <p className="mt-3 text-small leading-relaxed text-fg-3">{projection.note} Bone density cannot be measured on board.</p>
    </Card>
  );
}

function Sessions({ sessions }: { readonly sessions: ExerciseToday["sessions"] }): ReactElement {
  return (
    <Card as="section" aria-labelledby="sessions-title">
      <SectionTitle id="sessions-title">Today's sessions</SectionTitle>
      {!sessions.length && <p className="text-body text-fg-3">No session logged today.</p>}
      <ul className="flex flex-col gap-3">
        {sessions.map((session) => (
          <li key={session.id} className="rounded-2xl border border-line bg-white/[0.02] p-3.5">
            <p className="flex flex-wrap items-center justify-between gap-2">
              <span className="text-base font-medium text-fg">
                {KIND_LABEL[session.kind]}, {formatNumber(session.duration_min, 0)} min
              </span>
              <span className="flex items-center gap-2 text-small text-fg-3">
                {session.source === SIMULATED && <Tag>simulated data</Tag>}
                <span className="num">{formatTime(session.started_at)}</span>
              </span>
            </p>
            {Boolean(session.sets?.length) && (
              <ul className="mt-2 flex flex-col gap-1 text-body text-fg-3">
                {session.sets?.map((set) => (
                  <li key={`${set.exercise}-${set.reps}-${set.load_kg}`} className="flex justify-between gap-3">
                    <span>{set.exercise}</span>
                    <span className="num text-fg-2">
                      {set.reps} × {formatNumber(set.load_kg)} kg
                    </span>
                  </li>
                ))}
              </ul>
            )}
            <p className="mt-2 text-small text-fg-4">
              loading score <span className="num text-fg-2">{formatNumber(session.loading_score, 0)}</span>
            </p>
          </li>
        ))}
      </ul>
    </Card>
  );
}

function SessionForm({ crewId, missionNow }: { readonly crewId: string; readonly missionNow: string | undefined }): ReactElement {
  const queryClient = useQueryClient();
  const [kind, setKind] = useState<Kind>("resistance");
  const [duration, setDuration] = useState(DEFAULT_DURATION);
  const [sets, setSets] = useState<readonly SetDraft[]>([{ id: 1, ...EMPTY_SET }]);

  const save = useMutation({
    mutationFn: (body: Schemas["ExerciseSessionCreate"]) => addExerciseSession(crewId, body),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: keys.crew(crewId) });
      setSets([{ id: 1, ...EMPTY_SET }]);
    },
  });

  const update = (id: number, patch: Partial<SetDraft>): void => setSets((current) => current.map((set) => (set.id === id ? { ...set, ...patch } : set)));
  const filled = sets.filter((set) => set.exercise.trim() && toNumber(set.reps) >= 1 && toNumber(set.load) >= 0 && set.load.trim());
  const durationMin = toNumber(duration);
  const valid = durationMin > 0 && (kind === "aerobic" || Boolean(filled.length));

  const onSubmit = (event: FormEvent<HTMLFormElement>): void => {
    event.preventDefault();
    if (!valid) return;
    save.mutate({
      kind,
      started_at: missionNow ?? new Date().toISOString(),
      duration_min: durationMin,
      sets: kind === "aerobic" ? [] : filled.map((set) => ({ exercise: set.exercise.trim(), reps: Math.round(toNumber(set.reps)), load_kg: toNumber(set.load) })),
    });
  };

  return (
    <Card as="section" aria-labelledby="add-session">
      <SectionTitle id="add-session">Log a session</SectionTitle>
      <form onSubmit={onSubmit} className="flex flex-col gap-4">
        <div className="flex flex-wrap items-end gap-4">
          <div className="flex flex-col gap-1.5">
            <span className="text-small font-medium text-fg-2">Session type</span>
            <Segmented<Kind> label="Session type" value={kind} options={KINDS} onChange={setKind} />
          </div>
          <Field id="exercise-duration" label="Duration (minutes)" className="w-36">
            <Input id="exercise-duration" inputMode="decimal" className="num" value={duration} onChange={(event) => setDuration(event.target.value)} />
          </Field>
        </div>

        {kind === "resistance" && (
          <fieldset className="flex flex-col gap-2">
            <legend className="mb-1.5 text-small font-medium text-fg-2">Sets</legend>
            {sets.map((set, index) => (
              <div key={set.id} className="grid grid-cols-[minmax(0,1fr)_84px_96px_36px] items-center gap-2">
                <Input aria-label={`Exercise in set ${index + 1}`} placeholder="e.g. ARED squats" value={set.exercise} onChange={(event) => update(set.id, { exercise: event.target.value })} />
                <Input aria-label={`Reps in set ${index + 1}`} placeholder="reps" inputMode="numeric" className="num" value={set.reps} onChange={(event) => update(set.id, { reps: event.target.value })} />
                <Input aria-label={`Load in set ${index + 1}, in kilograms`} placeholder="kg" inputMode="decimal" className="num" value={set.load} onChange={(event) => update(set.id, { load: event.target.value })} />
                <IconButton label={`Remove set ${index + 1}`} size="sm" disabled={sets.length === 1} onClick={() => setSets((current) => current.filter((item) => item.id !== set.id))}>
                  <Trash2 size={14} strokeWidth={1.8} />
                </IconButton>
              </div>
            ))}
            <Button size="sm" variant="ghost" className="self-start" onClick={() => setSets((current) => [...current, { id: (current.at(-1)?.id ?? 0) + 1, ...EMPTY_SET }])}>
              <Plus size={14} strokeWidth={2} />
              Add a set
            </Button>
          </fieldset>
        )}

        {save.isError && <ProblemCard title="The session was not saved" detail={errorMessage(save.error)} />}
        {save.isSuccess && <Notice tone="ok" title="Session saved">The loading score and the streak have been updated.</Notice>}
        <Button type="submit" variant="primary" className="self-start" busy={save.isPending} disabled={!valid}>
          Save session
        </Button>
      </form>
    </Card>
  );
}

export default function ExercisePage(): ReactElement {
  const { crewId } = useSession();
  const today = useExerciseToday(crewId);
  const mission = useMission();

  return (
    <Page>
      {today.isPending && <Skeleton className="h-[420px] rounded-[var(--radius-card)]" />}
      {today.isError && <ProblemCard title="Exercise data could not be loaded" detail={errorMessage(today.error)} onRetry={() => void today.refetch()} />}
      {today.data && crewId && (
        <div className="grid items-start gap-5 xl:grid-cols-[minmax(0,1fr)_400px]">
          <div className="flex min-w-0 flex-col gap-5">
            <Summary today={today.data} />
            <SessionForm crewId={crewId} missionNow={mission.data?.sim_now} />
          </div>
          <div className="flex flex-col gap-5">
            <Sessions sessions={today.data.sessions} />
            <Projection projection={today.data.projection} />
          </div>
        </div>
      )}
    </Page>
  );
}
