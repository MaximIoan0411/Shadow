"use client";
/**
 * Testul de reacție (PVT-B): un pătrat se aprinde la intervale aleatoare de 1–4 secunde, iar tu apeși cât de
 * repede poți. Testul rulează integral aici; la sfârșit toate încercările pleacă într-un singur apel, iar
 * rezultatul (viteza, lapsusurile, abaterea față de normalul tău) îl calculează backend-ul.
 */
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { useCallback, useEffect, useRef, useState, type ReactElement } from "react";
import { Button, Card, Notice, ProblemCard, SectionTitle, Segmented, StatusBadge, cx } from "@/components/ui";
import { errorMessage, type Schemas } from "@/lib/api";
import { submitPvt } from "@/lib/endpoints";
import { formatDateTime, formatNumber, formatSigned } from "@/lib/format";
import { keys, usePvtHistory } from "@/lib/queries";

type Trial = Schemas["PvtTrial"];
type PvtResult = Schemas["PvtResult"];
type Phase = "idle" | "waiting" | "stimulus" | "feedback" | "done";

const DURATIONS = [
  { value: "180", label: "3 minutes" },
  { value: "30", label: "30 seconds" },
] as const;
type DurationValue = (typeof DURATIONS)[number]["value"];

const MIN_DELAY_MS = 1000;
const DELAY_SPREAD_MS = 3000;
const RESPONSE_LIMIT_MS = 3000;
const FEEDBACK_MS = 650;
const MS_PER_SECOND = 1000;
const TWO_DECIMALS = 2;
const HISTORY_ROWS = 5;
const RESPONSE_KEYS: readonly string[] = ["Space", "Enter"];

const PHASE_TEXT = {
  idle: "Press “Start test”, then keep your finger on the Space bar.",
  waiting: "Wait…",
  stimulus: "Now!",
  feedback: "",
  done: "Done. The result appears alongside.",
} as const satisfies Record<Phase, string>;

/** Tot ce se schimbă în timpul testului fără să redeseneze ecranul. */
interface Run {
  startedAtMs: number;
  startedAtIso: string;
  durationMs: number;
  shownAtMs: number;
  trials: Trial[];
  timer: ReturnType<typeof setTimeout> | null;
}

function ResultView({ result }: { readonly result: PvtResult }): ReactElement {
  return (
    <div>
      <div className="mb-3 flex flex-wrap items-center gap-2">
        <StatusBadge status={result.status} />
        <span className="text-small text-fg-4">{formatDateTime(result.at)}</span>
      </div>
      <dl className="grid grid-cols-2 gap-2.5">
        <div className="rounded-2xl border border-line bg-white/[0.02] p-3.5">
          <dt className="text-small text-fg-3">Mean speed</dt>
          <dd className="mt-1.5 flex items-baseline gap-1.5">
            <span className="text-display font-medium tracking-[-0.02em] text-fg">{formatNumber(result.mean_speed, TWO_DECIMALS)}</span>
            <span className="text-small text-fg-4">responses/s</span>
          </dd>
          <dd className="mt-2 text-small text-fg-4">
            your baseline <span className="num text-fg-3">{formatNumber(result.baseline_speed, TWO_DECIMALS)}</span>
            {result.deviation_sd !== null && result.deviation_sd !== undefined && <span className="num ml-2 text-fg-2">{formatSigned(result.deviation_sd)} SD</span>}
          </dd>
        </div>
        <div className="rounded-2xl border border-line bg-white/[0.02] p-3.5">
          <dt className="text-small text-fg-3">Mean reaction time</dt>
          <dd className="mt-1.5 flex items-baseline gap-1.5">
            <span className="text-display font-medium tracking-[-0.02em] text-fg">{formatNumber(result.mean_rt_ms, 0)}</span>
            <span className="text-small text-fg-4">ms</span>
          </dd>
          <dd className="mt-2 text-small text-fg-4">{result.n_trials} trials</dd>
        </div>
        <div className="rounded-2xl border border-line bg-white/[0.02] p-3.5">
          <dt className="text-small text-fg-3">Lapses</dt>
          <dd className="mt-1.5 text-display font-medium tracking-[-0.02em] text-fg">{result.lapses}</dd>
          <dd className="mt-2 text-small text-fg-4">responses of 355 ms or slower</dd>
        </div>
        <div className="rounded-2xl border border-line bg-white/[0.02] p-3.5">
          <dt className="text-small text-fg-3">False starts</dt>
          <dd className="mt-1.5 text-display font-medium tracking-[-0.02em] text-fg">{result.false_starts}</dd>
          <dd className="mt-2 text-small text-fg-4">presses before the signal</dd>
        </div>
      </dl>
    </div>
  );
}

export function PvtTest({ crewId, missionNow }: { readonly crewId: string; readonly missionNow: string | undefined }): ReactElement {
  const queryClient = useQueryClient();
  const history = usePvtHistory(crewId);
  const [duration, setDuration] = useState<DurationValue>("180");
  const [phase, setPhase] = useState<Phase>("idle");
  const [lastRt, setLastRt] = useState<number | null>(null);
  const run = useRef<Run | null>(null);

  const submit = useMutation({
    mutationFn: (body: Schemas["PvtSubmit"]) => submitPvt(crewId, body),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: keys.pvt(crewId) });
      void queryClient.invalidateQueries({ queryKey: keys.crew(crewId) });
    },
  });
  const { mutate: sendResult } = submit;

  const clearTimer = (): void => {
    if (run.current?.timer) clearTimeout(run.current.timer);
  };

  const finish = useCallback((): void => {
    const current = run.current;
    if (!current) return;
    if (current.timer) clearTimeout(current.timer);
    run.current = null;
    setPhase("done");
    if (current.trials.length) sendResult({ started_at: current.startedAtIso, duration_s: current.durationMs / MS_PER_SECOND, trials: current.trials });
  }, [sendResult]);

  const scheduleStimulus = useCallback((): void => {
    const current = run.current;
    if (!current) return;
    if (performance.now() - current.startedAtMs >= current.durationMs) return finish();
    setPhase("waiting");
    current.timer = setTimeout(() => {
      current.shownAtMs = performance.now();
      setPhase("stimulus");
      current.timer = setTimeout(() => {
        // Niciun răspuns în 3 secunde: încercarea se notează ca lapsus (`rt_ms = null`).
        current.trials.push({ stimulus_at_ms: current.shownAtMs - current.startedAtMs, rt_ms: null, false_start: false });
        scheduleStimulus();
      }, RESPONSE_LIMIT_MS);
    }, MIN_DELAY_MS + Math.random() * DELAY_SPREAD_MS);
  }, [finish]);

  const start = (): void => {
    submit.reset();
    setLastRt(null);
    run.current = {
      startedAtMs: performance.now(),
      startedAtIso: missionNow ?? new Date().toISOString(),
      durationMs: Number(duration) * MS_PER_SECOND,
      shownAtMs: 0,
      trials: [],
      timer: null,
    };
    scheduleStimulus();
  };

  const respond = useCallback((): void => {
    const current = run.current;
    if (!current) return;
    const now = performance.now();
    if (phase === "waiting") {
      current.trials.push({ stimulus_at_ms: now - current.startedAtMs, rt_ms: null, false_start: true });
      if (current.timer) clearTimeout(current.timer);
      setLastRt(null);
      setPhase("feedback");
      current.timer = setTimeout(scheduleStimulus, FEEDBACK_MS);
      return;
    }
    if (phase !== "stimulus") return;
    const reaction = now - current.shownAtMs;
    current.trials.push({ stimulus_at_ms: current.shownAtMs - current.startedAtMs, rt_ms: reaction, false_start: false });
    if (current.timer) clearTimeout(current.timer);
    setLastRt(reaction);
    setPhase("feedback");
    current.timer = setTimeout(scheduleStimulus, FEEDBACK_MS);
  }, [phase, scheduleStimulus]);

  useEffect(() => {
    const onKeyDown = (event: KeyboardEvent): void => {
      if (!run.current || event.repeat || !RESPONSE_KEYS.includes(event.code)) return;
      event.preventDefault();
      respond();
    };
    window.addEventListener("keydown", onKeyDown);
    return () => window.removeEventListener("keydown", onKeyDown);
  }, [respond]);

  useEffect(() => clearTimer, []);

  const running = phase === "waiting" || phase === "stimulus" || phase === "feedback";
  const feedbackText = lastRt === null ? "Too early" : `${formatNumber(lastRt, 0)} ms`;
  const latest = submit.data ?? history.data?.[0];

  return (
    <div className="grid items-start gap-5 xl:grid-cols-[minmax(0,1fr)_400px]">
      <Card as="section" aria-labelledby="pvt-title">
        <SectionTitle id="pvt-title" right={<Segmented<DurationValue> size="sm" label="Test length" value={duration} options={DURATIONS} onChange={(value) => !running && setDuration(value)} />}>
          Reaction test
        </SectionTitle>
        <button
          type="button"
          onPointerDown={respond}
          disabled={!running}
          aria-label="Response area: press when it lights up"
          className={cx(
            "grid h-[280px] w-full place-items-center rounded-2xl border transition-colors duration-75",
            phase === "stimulus" ? "border-solid bg-solid text-on-solid" : "border-line-2 bg-white/[0.02] text-fg-3",
          )}
        >
          <span aria-live="polite" className={cx("text-center", phase === "feedback" ? "num text-hero font-medium text-fg" : "text-title font-medium")}>
            {phase === "feedback" ? feedbackText : PHASE_TEXT[phase]}
          </span>
        </button>
        <div className="mt-4 flex flex-wrap items-center gap-3">
          {running ? (
            <Button onClick={finish}>Stop test</Button>
          ) : (
            <Button variant="primary" size="lg" onClick={start}>
              {phase === "done" ? "Repeat test" : "Start test"}
            </Button>
          )}
          <p className="text-small text-fg-4">Press Space (or tap the square) as soon as it lights up. Pressing early counts as a false start.</p>
        </div>
      </Card>

      <div className="flex flex-col gap-5">
        <Card as="section" aria-labelledby="pvt-result">
          <SectionTitle id="pvt-result">{submit.data ? "This result" : "Latest result"}</SectionTitle>
          {submit.isPending && <Notice title="Calculating the result…" />}
          {submit.isError && <ProblemCard title="The result was not saved" detail={errorMessage(submit.error)} />}
          {!submit.isPending && latest && <ResultView result={latest} />}
          {!submit.isPending && !latest && !history.isPending && <p className="text-body text-fg-3">You have not taken a reaction test yet.</p>}
        </Card>

        {Boolean(history.data?.length) && (
          <Card as="section" aria-labelledby="pvt-history">
            <SectionTitle id="pvt-history">Earlier tests</SectionTitle>
            <table className="w-full text-small">
              <thead>
                <tr className="text-left text-caption text-fg-4">
                  <th scope="col" className="pb-2 font-medium">When</th>
                  <th scope="col" className="pb-2 text-right font-medium">Speed</th>
                  <th scope="col" className="pb-2 text-right font-medium">Lapses</th>
                  <th scope="col" className="pb-2 text-right font-medium">Status</th>
                </tr>
              </thead>
              <tbody>
                {history.data?.slice(0, HISTORY_ROWS).map((item) => (
                  <tr key={item.id} className="border-t border-line">
                    <td className="py-2 text-fg-2">{formatDateTime(item.at)}</td>
                    <td className="num py-2 text-right text-fg">{formatNumber(item.mean_speed, TWO_DECIMALS)}</td>
                    <td className="num py-2 text-right text-fg">{item.lapses}</td>
                    <td className="py-2 text-right">
                      <StatusBadge status={item.status} compact />
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </Card>
        )}
      </div>
    </div>
  );
}
