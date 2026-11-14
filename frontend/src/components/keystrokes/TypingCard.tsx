"use client";
/**
 * Tastarea: un câmp în care scrii orice, iar SHADOW îți arată ritmul. Se trimit doar timpii apăsărilor și clasa
 * tastei (literă, spațiu, ștergere), niciodată textul. Barele live arată durata fiecărei apăsări, fără litere.
 */
import { useQueryClient } from "@tanstack/react-query";
import { useState, type ReactElement } from "react";
import { LineChart } from "@/components/charts/LineChart";
import { Card, Meter, Notice, SectionTitle, StatusBadge, Tag, Textarea, cx } from "@/components/ui";
import type { Schemas } from "@/lib/api";
import { formatDateTime, formatNumber, formatPercent, formatSigned, toPercent } from "@/lib/format";
import { keys, useKeystrokeSummary } from "@/lib/queries";
import { useKeystrokes } from "@/lib/useKeystrokes";

type Features = Schemas["KeystrokeFeatures"];
type KeyClass = Schemas["KeyEvent"]["key_class"];

interface Stroke {
  readonly id: number;
  readonly holdMs: number;
  readonly keyClass: KeyClass;
}

const MAX_BARS = 96;
const BAR_MAX_MS = 260;
const BAR_MIN_PERCENT = 6;
const FATIGUE_MAX = 100;
const BASELINE_SESSIONS = 7;
const RECENT_SESSIONS = 6;
const TYPING_FIELD_ID = "typing-field";

const BAR_TONE = {
  char: "bg-fg-2",
  space: "bg-fg-4",
  enter: "bg-fg-4",
  other: "bg-fg-5",
  backspace: "border border-fg-3 bg-transparent",
} as const satisfies Record<KeyClass, string>;

function Compare({ label, value, baseline, unit, digits = 0 }: {
  readonly label: string;
  readonly value: number | undefined;
  readonly baseline: number | undefined;
  readonly unit: string;
  readonly digits?: number;
}): ReactElement {
  const delta = value !== undefined && baseline !== undefined ? value - baseline : null;
  return (
    <div className="rounded-2xl border border-line bg-white/[0.02] p-3.5">
      <p className="text-small text-fg-3">{label}</p>
      <p className="mt-1.5 flex items-baseline gap-1.5">
        <span className="text-display font-medium tracking-[-0.02em] text-fg">{formatNumber(value, digits)}</span>
        <span className="text-small text-fg-4">{unit}</span>
      </p>
      <p className="mt-2 text-small text-fg-4">
        your baseline <span className="num text-fg-3">{formatNumber(baseline, digits)}</span>
        {delta !== null && <span className="num ml-2 text-fg-2">{formatSigned(delta, digits)}</span>}
      </p>
    </div>
  );
}

export function TypingCard({ crewId }: { readonly crewId: string }): ReactElement {
  const queryClient = useQueryClient();
  const summary = useKeystrokeSummary(crewId);
  const [strokes, setStrokes] = useState<readonly Stroke[]>([]);
  const [live, setLive] = useState<Schemas["KeystrokeResult"] | null>(null);
  const [text, setText] = useState("");

  const keystrokes = useKeystrokes(crewId, "free_typing", {
    onStroke: (holdMs, keyClass) => setStrokes((current) => [...current, { id: (current.at(-1)?.id ?? 0) + 1, holdMs, keyClass }].slice(-MAX_BARS)),
    onResult: (result) => {
      setLive(result);
      void queryClient.invalidateQueries({ queryKey: keys.keystrokes(crewId) });
    },
  });

  const current: Features | null | undefined = live?.features ?? summary.data?.current;
  const baseline: Features | null | undefined = live?.baseline ?? summary.data?.baseline;
  const fatigue = live?.fatigue_index ?? summary.data?.fatigue_index;
  const status = live?.status ?? summary.data?.status ?? "unknown";
  const baselineReady = live?.baseline_ready ?? summary.data?.baseline_ready ?? false;
  const sessions = summary.data?.sessions ?? [];

  return (
    <div className="grid items-start gap-5 xl:grid-cols-[minmax(0,1fr)_400px]">
      <Card as="section" aria-labelledby="typing-title">
        <SectionTitle id="typing-title" right={<Tag>no text, rhythm only</Tag>}>
          Type something
        </SectionTitle>
        <label htmlFor={TYPING_FIELD_ID} className="sr-only">
          Free typing field
        </label>
        <Textarea
          id={TYPING_FIELD_ID}
          value={text}
          onChange={(event) => setText(event.target.value)}
          onKeyDown={keystrokes.onKeyDown}
          onKeyUp={keystrokes.onKeyUp}
          placeholder="Write a sentence or two, about anything."
          aria-describedby="typing-privacy"
          className="min-h-32 text-lead"
        />
        <p id="typing-privacy" className="mt-2 text-small text-fg-3">
          SHADOW does not read what you type, only the rhythm: how long you hold each key and how long until the next one.
        </p>

        <div aria-hidden="true" className="mt-5 flex h-24 items-end gap-[3px] overflow-hidden rounded-xl border border-line bg-white/[0.02] px-3 py-2">
          {strokes.map((stroke) => (
            <span
              key={stroke.id}
              className={cx("w-[5px] shrink-0 rounded-t-[2px]", BAR_TONE[stroke.keyClass])}
              style={{ height: `${Math.max(BAR_MIN_PERCENT, toPercent(stroke.holdMs, 0, BAR_MAX_MS))}%` }}
            />
          ))}
          {!strokes.length && <span className="self-center text-small text-fg-4">One bar per key press: the longer you hold the key, the taller the bar.</span>}
        </div>
        <p className="mt-2 flex flex-wrap gap-x-4 gap-y-1 text-caption text-fg-4">
          <span className="flex items-center gap-1.5">
            <span className="size-2 rounded-[2px] bg-fg-2" /> letter
          </span>
          <span className="flex items-center gap-1.5">
            <span className="size-2 rounded-[2px] bg-fg-4" /> space
          </span>
          <span className="flex items-center gap-1.5">
            <span className="size-2 rounded-[2px] border border-fg-3" /> delete
          </span>
          <span>Your rhythm is sent every 5 seconds.</span>
        </p>

        {sessions.length > 1 && (
          <div className="mt-6 border-t border-line pt-5">
            <h3 className="mb-2.5 text-caption font-medium uppercase tracking-[0.06em] text-fg-4">Your speed, session by session</h3>
            <LineChart
              title="Typing speed per session, in keys per minute"
              unit="taste/min"
              baseline={baseline?.keys_per_min}
              series={[
                {
                  key: "keys_per_min",
                  label: "Speed",
                  points: sessions.map((session, index) => ({ x: index, xLabel: formatDateTime(session.at), value: session.keys_per_min, status: session.status })),
                },
              ]}
            />
          </div>
        )}
      </Card>

      <div className="flex flex-col gap-5">
        <Card as="section" aria-labelledby="rhythm-title">
          <SectionTitle id="rhythm-title" right={<StatusBadge status={status} />}>
            Your rhythm
          </SectionTitle>
          {!baselineReady && (
            <Notice title="Your baseline is still forming" className="mb-3">
              It takes {BASELINE_SESSIONS} typing sessions; until then there are no deviations.
              {live ? ` You have ${live.baseline_sessions}.` : ""}
            </Notice>
          )}
          <div className="grid grid-cols-2 gap-2.5">
            <Compare label="Speed" value={current?.keys_per_min} baseline={baseline?.keys_per_min} unit="taste/min" />
            <Compare label="Hold" value={current?.hold_ms_mean} baseline={baseline?.hold_ms_mean} unit="ms" />
            <Compare label="Between keys" value={current?.flight_ms_mean} baseline={baseline?.flight_ms_mean} unit="ms" />
            <div className="rounded-2xl border border-line bg-white/[0.02] p-3.5">
              <p className="text-small text-fg-3">Deletions</p>
              <p className="mt-1.5 text-display font-medium tracking-[-0.02em] text-fg">{formatPercent(current?.backspace_rate)}</p>
              <p className="mt-2 text-small text-fg-4">
                your baseline <span className="num text-fg-3">{formatPercent(baseline?.backspace_rate)}</span>
              </p>
            </div>
          </div>
          <div className="mt-4">
            <p className="mb-1.5 flex items-baseline justify-between text-small text-fg-3">
              Fatigue index
              <span className="num text-body font-medium text-fg">{formatNumber(fatigue, 0)} of 100</span>
            </p>
            <Meter value={fatigue ?? 0} max={FATIGUE_MAX} label="Fatigue index" status={status} />
            <p className="mt-2 text-small text-fg-4">0 means exactly like your baseline; 100, the largest deviation.</p>
          </div>
        </Card>

        {Boolean(sessions.length) && (
          <Card as="section" aria-labelledby="sessions-title">
            <SectionTitle id="sessions-title">Recent sessions</SectionTitle>
            <table className="w-full text-small">
              <thead>
                <tr className="text-left text-caption text-fg-4">
                  <th scope="col" className="pb-2 font-medium">When</th>
                  <th scope="col" className="pb-2 text-right font-medium">Keys/min</th>
                  <th scope="col" className="pb-2 text-right font-medium">Fatigue</th>
                  <th scope="col" className="pb-2 text-right font-medium">Status</th>
                </tr>
              </thead>
              <tbody>
                {sessions.slice(-RECENT_SESSIONS).toReversed().map((session) => (
                  <tr key={session.session_id} className="border-t border-line">
                    <td className="py-2 text-fg-2">{formatDateTime(session.at)}</td>
                    <td className="num py-2 text-right text-fg">{formatNumber(session.keys_per_min, 0)}</td>
                    <td className="num py-2 text-right text-fg">{formatNumber(session.fatigue_index, 0)}</td>
                    <td className="py-2 text-right">
                      <StatusBadge status={session.status} compact />
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
