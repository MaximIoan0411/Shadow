"use client";
/**
 * Check-in-ul de dimineață. Formularul se construiește din schema trimisă de backend (`GET /checkin/schema`):
 * câmpurile, unitățile și cele trei texte explicative. O valoare imposibilă nu blochează formularul: restul se
 * salvează, iar câmpul respins primește mesajul lui („măsoară din nou”).
 */
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { useState, type FormEvent, type ReactElement } from "react";
import { PerceptionGapCard } from "@/components/body/PerceptionGap";
import { Page } from "@/components/layout/Shell";
import { Button, ButtonLink, Card, Field, Input, Notice, ProblemCard, SectionTitle, Segmented, Skeleton, StatusBadge, Textarea } from "@/components/ui";
import { errorMessage, type Schemas } from "@/lib/api";
import { submitCheckin } from "@/lib/endpoints";
import { formatTime } from "@/lib/format";
import { keys, useCheckinSchema, useCheckinToday } from "@/lib/queries";
import { useSession } from "@/lib/session";
import { useKeystrokes } from "@/lib/useKeystrokes";

type Indicator = Schemas["CheckinIndicator"];
type CheckinCreate = Schemas["CheckinCreate"];
type CheckinResult = Schemas["CheckinResult"];
type Values = Readonly<Record<string, string>>;

const NUMERIC_KEYS = ["systolic_mmhg", "diastolic_mmhg", "pulse_bpm", "glucose_mg_dl", "temperature_c", "sleep_hours"] as const;
const MOOD_KEY = "mood";
const MEALS_KEY = "meals_eaten";
const NOTE_KEY = "note";
const NOTE_MAX = 500;
const MOODS = ["1", "2", "3", "4", "5"] as const;
const MEAL_VALUES = ["all", "some", "none"] as const;
const CHOICE_LABEL: Readonly<Record<string, string>> = { all: "All", some: "Some", none: "None" };

type Meal = (typeof MEAL_VALUES)[number];
const isMeal = (value: string | undefined): value is Meal => MEAL_VALUES.some((meal) => meal === value);

/** „36,9” și „36.9” înseamnă același lucru; text gol sau nenumeric înseamnă „nu am măsurat”. */
function parseNumber(text: string | undefined): number | null {
  const trimmed = (text ?? "").trim().replace(",", ".");
  if (!trimmed) return null;
  const value = Number(trimmed);
  return Number.isFinite(value) ? value : null;
}

function toBody(values: Values): CheckinCreate {
  const meals = values[MEALS_KEY];
  return {
    mood: Number(values[MOOD_KEY]),
    ...Object.fromEntries(NUMERIC_KEYS.map((key) => [key, parseNumber(values[key])])),
    meals_eaten: isMeal(meals) ? meals : null,
    note: values[NOTE_KEY]?.trim() || null,
  };
}

/** Valorile deja salvate azi, ca text, pentru precompletarea formularului. */
function fromCheckin(checkin: Schemas["Checkin"] | null | undefined): Values {
  if (!checkin) return {};
  return Object.fromEntries(
    Object.entries(checkin.values)
      .filter(([, value]) => value !== null && value !== undefined)
      .map(([key, value]) => [key, String(value).replace(".", ",")]),
  );
}

function Explain({ indicator }: { readonly indicator: Indicator }): ReactElement {
  return (
    <details className="group text-small text-fg-3">
      <summary className="cursor-pointer list-none rounded-md text-fg-4 underline decoration-fg-5 underline-offset-2 transition-colors hover:text-fg-2">
        How to measure it and why it matters
      </summary>
      <dl className="mt-2 flex flex-col gap-2 rounded-xl border border-line bg-white/[0.02] p-3 leading-relaxed">
        <div>
          <dt className="font-medium text-fg-2">How to measure</dt>
          <dd>{indicator.how_to_measure}</dd>
        </div>
        <div>
          <dt className="font-medium text-fg-2">What the value means</dt>
          <dd>{indicator.what_it_means}</dd>
        </div>
        <div>
          <dt className="font-medium text-fg-2">Why it matters in space</dt>
          <dd>{indicator.why_in_space}</dd>
        </div>
        {indicator.source && (
          <dd>
            Source:{" "}
            <a href={indicator.source.url} target="_blank" rel="noreferrer">
              {indicator.source.citation}
            </a>
          </dd>
        )}
      </dl>
    </details>
  );
}

function IndicatorField({ indicator, value, error, onChange }: {
  readonly indicator: Indicator;
  readonly value: string;
  readonly error?: string;
  readonly onChange: (value: string) => void;
}): ReactElement {
  const id = `checkin-${indicator.key}`;
  if (indicator.input === "scale_1_5") {
    return (
      <div className="flex flex-col gap-2 sm:col-span-2">
        <p className="text-small font-medium text-fg-2">{indicator.label}</p>
        <div className="flex flex-wrap items-center gap-3">
          <span className="text-small text-fg-4">very bad</span>
          <Segmented label={indicator.label} value={MOODS.find((mood) => mood === value)} options={MOODS.map((mood) => ({ value: mood, label: mood }))} onChange={onChange} dense />
          <span className="text-small text-fg-4">very good</span>
        </div>
        <Explain indicator={indicator} />
      </div>
    );
  }
  if (indicator.input === "choice") {
    const choices = indicator.choices ?? [];
    return (
      <div className="flex flex-col gap-2 sm:col-span-2">
        <p className="text-small font-medium text-fg-2">{indicator.label}</p>
        <Segmented label={indicator.label} value={choices.find((choice) => choice === value)} options={choices.map((choice) => ({ value: choice, label: CHOICE_LABEL[choice] ?? choice }))} onChange={onChange} />
        <Explain indicator={indicator} />
      </div>
    );
  }
  return (
    <div className="flex flex-col gap-2">
      <Field id={id} label={indicator.label} error={error}>
        <div className="relative">
          <Input
            id={id}
            inputMode="decimal"
            autoComplete="off"
            value={value}
            onChange={(event) => onChange(event.target.value)}
            aria-invalid={Boolean(error)}
            aria-describedby={error ? `${id}-error` : undefined}
            className="num pr-16"
          />
          <span className="pointer-events-none absolute inset-y-0 right-3.5 flex items-center text-small text-fg-4">{indicator.unit}</span>
        </div>
      </Field>
      <Explain indicator={indicator} />
    </div>
  );
}

function ResultPanel({ result }: { readonly result: CheckinResult }): ReactElement {
  return (
    <div className="flex flex-col gap-5">
      <Notice tone={result.rejected.length ? "watch" : "ok"} title={result.message}>
        {result.rejected.length
          ? "Some values were rejected as impossible and were not saved. See the message next to each field and measure again."
          : `${result.streak.label}: ${result.streak.days} days in a row, best ${result.streak.best}.`}
      </Notice>
      <PerceptionGapCard gap={result.perception_gap} canCheckIn={false} />
      {Boolean(result.alerts_created.length) && (
        <Card as="section" aria-labelledby="new-alerts">
          <SectionTitle id="new-alerts">New alerts after this check-in</SectionTitle>
          <ul className="flex flex-col gap-2">
            {result.alerts_created.map((alert) => (
              <li key={alert.id} className="flex items-center justify-between gap-3">
                <span className="flex min-w-0 items-center gap-2 text-body text-fg">
                  <StatusBadge status={alert.status} compact />
                  <span className="truncate">{alert.title}</span>
                </span>
                <ButtonLink href={`/alerts?id=${alert.id}`} size="sm">
                  See the plan
                </ButtonLink>
              </li>
            ))}
          </ul>
        </Card>
      )}
    </div>
  );
}

function CheckinForm({ crewId, indicators, today }: { readonly crewId: string; readonly indicators: readonly Indicator[]; readonly today: Schemas["Checkin"] | null }): ReactElement {
  const queryClient = useQueryClient();
  const [values, setValues] = useState<Values>(() => fromCheckin(today));
  const [result, setResult] = useState<CheckinResult | null>(null);
  const keystrokes = useKeystrokes(crewId, "checkin_note");
  const submit = useMutation({
    mutationFn: async (body: CheckinCreate) => {
      await keystrokes.finish();
      return submitCheckin(crewId, body);
    },
    onSuccess: (saved) => {
      setResult(saved);
      queryClient.setQueryData(keys.checkinToday(crewId), saved.checkin);
      void queryClient.invalidateQueries({ queryKey: keys.crew(crewId) });
      void queryClient.invalidateQueries({ queryKey: keys.alerts });
    },
  });

  const rejectedBy = new Map(result?.rejected.map((rejection) => [rejection.field, rejection.message]));
  const set = (key: string, value: string): void => setValues((current) => ({ ...current, [key]: value }));
  const hasMood = Boolean(values[MOOD_KEY]);

  const onSubmit = (event: FormEvent<HTMLFormElement>): void => {
    event.preventDefault();
    if (hasMood) submit.mutate(toBody(values));
  };

  return (
    <div className="grid items-start gap-5 xl:grid-cols-[minmax(0,1fr)_400px]">
      <Card as="section" aria-labelledby="checkin-title">
        <SectionTitle id="checkin-title">How you are this morning</SectionTitle>
        <form onSubmit={onSubmit} className="flex flex-col gap-6">
          <div className="grid gap-x-5 gap-y-6 sm:grid-cols-2">
            {indicators.map((indicator) => (
              <IndicatorField
                key={indicator.key}
                indicator={indicator}
                value={values[indicator.key] ?? ""}
                error={rejectedBy.get(indicator.key)}
                onChange={(value) => set(indicator.key, value)}
              />
            ))}
          </div>
          <Field id="checkin-note" label="Free note (optional)" hint="SHADOW does not read what you write here, only the rhythm of your typing. The text stays in your own log.">
            <Textarea
              id="checkin-note"
              maxLength={NOTE_MAX}
              value={values[NOTE_KEY] ?? ""}
              onChange={(event) => set(NOTE_KEY, event.target.value)}
              onKeyDown={keystrokes.onKeyDown}
              onKeyUp={keystrokes.onKeyUp}
              aria-describedby="checkin-note-hint"
            />
          </Field>
          {submit.isError && <ProblemCard title="The check-in was not saved" detail={errorMessage(submit.error)} />}
          <div className="flex flex-wrap items-center gap-3">
            <Button type="submit" variant="primary" size="lg" busy={submit.isPending} disabled={!hasMood}>
              {today || result ? "Save again" : "Save check-in"}
            </Button>
            <p className="text-small text-fg-4">{hasMood ? "Only mood is required; the other fields can stay empty." : "Choose your mood first, from 1 to 5."}</p>
          </div>
        </form>
      </Card>

      <div className="flex flex-col gap-5">
        {result ? (
          <ResultPanel result={result} />
        ) : (
          <Notice title={today ? `Today's check-in is saved (${formatTime(today.created_at)})` : "You have not checked in yet today"}>
            {today ? "You can send another one at any time: it replaces the previous one." : "It takes a minute. Right after saving you see the gap between how you feel and what the data shows."}
          </Notice>
        )}
      </div>
    </div>
  );
}

export default function CheckinPage(): ReactElement {
  const { crewId } = useSession();
  const schema = useCheckinSchema();
  const today = useCheckinToday(crewId);
  const failure = schema.error ?? today.error;

  return (
    <Page>
      {(schema.isPending || today.isPending) && <Skeleton className="h-[520px] rounded-[var(--radius-card)]" />}
      {failure && (
        <ProblemCard
          title="The form could not be loaded"
          detail={errorMessage(failure)}
          onRetry={() => {
            void schema.refetch();
            void today.refetch();
          }}
        />
      )}
      {crewId && schema.data && today.isSuccess && <CheckinForm key={crewId} crewId={crewId} indicators={schema.data.indicators} today={today.data} />}
    </Page>
  );
}
