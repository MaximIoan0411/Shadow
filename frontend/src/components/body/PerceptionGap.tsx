"use client";
/**
 * Decalajul de percepție: ideea centrală a proiectului. Două bare pe aceeași scară, „cum spui că te simți” și
 * „ce arată datele”, iar diferența dintre ele e singurul lucru colorat. Trebuie înțeles în cinci secunde.
 */
import type { ReactElement } from "react";
import { ButtonLink, Card, SectionTitle, StatusBadge } from "@/components/ui";
import type { Schemas } from "@/lib/api";
import { formatNumber, toPercent } from "@/lib/format";
import { STATUS_META } from "@/lib/status";

const SCALE_MAX = 100;

function ScoreBar({ label, score, tone, gapFrom, gapColor }: {
  readonly label: string;
  readonly score: number;
  readonly tone: "said" | "measured";
  /** Unde începe segmentul de decalaj pe această bară; lipsește pe bara care nu îl poartă. */
  readonly gapFrom?: number;
  readonly gapColor?: string;
}): ReactElement {
  return (
    <div>
      <div className="mb-1.5 flex items-baseline justify-between gap-3">
        <span className="text-small text-fg-3">{label}</span>
        <span className="num text-body font-medium text-fg">{formatNumber(score, 0)}</span>
      </div>
      <div className="relative h-2.5 overflow-hidden rounded-full bg-white/[0.07]">
        <div
          className={tone === "said" ? "absolute inset-y-0 left-0 rounded-full bg-fg-4" : "absolute inset-y-0 left-0 rounded-full bg-fg"}
          style={{ width: `${toPercent(score, 0, SCALE_MAX)}%` }}
        />
        {gapFrom !== undefined && gapColor && gapFrom > score && (
          <div
            className="absolute inset-y-0 rounded-r-full"
            style={{
              left: `${toPercent(score, 0, SCALE_MAX)}%`,
              width: `${toPercent(gapFrom - score, 0, SCALE_MAX)}%`,
              background: `repeating-linear-gradient(135deg, ${gapColor} 0 3px, transparent 3px 6px)`,
            }}
          />
        )}
      </div>
    </div>
  );
}

export function PerceptionGapCard({ gap, canCheckIn }: { readonly gap: Schemas["PerceptionGap"]; readonly canCheckIn: boolean }): ReactElement {
  const { self_score: said, objective_score: measured } = gap;
  const complete = said !== null && said !== undefined && measured !== null && measured !== undefined;

  return (
    <Card as="section" aria-labelledby="gap-title">
      <SectionTitle id="gap-title" right={complete ? <StatusBadge status={gap.status} /> : undefined}>
        Perception gap
      </SectionTitle>

      {complete ? (
        <>
          <p className="flex items-baseline gap-3">
            <span className="text-hero font-medium tracking-[-0.03em] text-fg">{formatNumber(Math.abs(gap.gap ?? said - measured), 0)}</span>
            <span className="text-body leading-snug text-fg-3">
              points between how you say you feel
              <br />
              and what the data shows
            </span>
          </p>
          <div className="mt-5 flex flex-col gap-3.5">
            <ScoreBar label="How you say you feel" score={said} tone="said" />
            <ScoreBar label="What the data shows" score={measured} tone="measured" gapFrom={said} gapColor={STATUS_META[gap.status].color} />
          </div>
          <p className="mt-5 text-base leading-relaxed text-fg">{gap.explanation}</p>
          {Boolean(gap.contributing_signals?.length) && (
            <ul className="mt-3 flex flex-col gap-1 text-body text-fg-3">
              {gap.contributing_signals?.map((signal) => (
                <li key={signal} className="flex gap-2">
                  <span aria-hidden="true" className="text-fg-5">
                    –
                  </span>
                  {signal}
                </li>
              ))}
            </ul>
          )}
        </>
      ) : (
        <div className="flex flex-col items-start gap-3">
          <p className="text-base leading-relaxed text-fg-2">{gap.explanation}</p>
          {canCheckIn && (
            <ButtonLink href="/checkin" variant="primary">
              Do today's check-in
            </ButtonLink>
          )}
        </div>
      )}
    </Card>
  );
}
