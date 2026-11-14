"use client";
/**
 * Derulatorul misiunii: câte un pătrățel pentru fiecare zi (140), în limbajul din puncte al logo-ului.
 * Zilele în limite rămân neutre; doar abaterile au culoare, ca ochiul să le găsească imediat. Zilele care
 * încă nu au avut loc sunt stinse. Derulatorul doar citește istoricul, nu schimbă ceasul misiunii.
 */
import type { KeyboardEvent, PointerEvent, ReactElement } from "react";
import { Button, Card, SectionTitle, StatusBadge, Tag, cx } from "@/components/ui";
import type { Schemas } from "@/lib/api";
import { clamp, formatDate, toPercent } from "@/lib/format";
import type { Status } from "@/lib/status";

type TimelineDay = Schemas["TimelineDay"];

interface MissionTimelineProps {
  readonly days: readonly TimelineDay[];
  readonly totalDays: number;
  readonly currentDay: number;
  /** `null` = se afișează ziua curentă (în direct). */
  readonly selectedDay: number | null;
  readonly onSelect: (day: number | null) => void;
}

const WEEK = 7;

const CELL_TONE = {
  ok: "bg-fg-5",
  unknown: "bg-white/[0.14]",
  watch: "bg-watch",
  alert: "bg-alert",
} as const satisfies Record<Status, string>;

/** Cu cât mută fiecare tastă ziua selectată. Home și End sar la capete. */
const KEY_DELTA: Readonly<Record<string, number>> = { ArrowLeft: -1, ArrowDown: -1, ArrowRight: 1, ArrowUp: 1, PageDown: -WEEK, PageUp: WEEK };

export function MissionTimeline({ days, totalDays, currentDay, selectedDay, onSelect }: MissionTimelineProps): ReactElement {
  const shown = selectedDay ?? currentDay;
  const byDay = new Map(days.map((day) => [day.day, day]));
  const shownDay = byDay.get(shown);
  const select = (day: number): void => onSelect(day >= currentDay ? null : Math.max(1, day));

  const dayAt = (event: PointerEvent<HTMLDivElement>): number => {
    const bounds = event.currentTarget.getBoundingClientRect();
    const fraction = (event.clientX - bounds.left) / bounds.width;
    return clamp(Math.ceil(fraction * totalDays), 1, currentDay);
  };

  const onKeyDown = (event: KeyboardEvent<HTMLDivElement>): void => {
    const delta = KEY_DELTA[event.key];
    const target = { Home: 1, End: currentDay }[event.key] ?? (delta === undefined ? undefined : shown + delta);
    if (target === undefined) return;
    event.preventDefault();
    select(clamp(target, 1, currentDay));
  };

  return (
    <Card as="section" aria-labelledby="timeline-title">
      <SectionTitle
        id="timeline-title"
        right={
          <span className="flex flex-wrap items-center justify-end gap-2">
            {shownDay?.events?.map((event) => <Tag key={event}>{event}</Tag>)}
            {shownDay && <StatusBadge status={shownDay.overall_status} compact />}
            <span className="num text-small text-fg-2">
              Day {shown}
              {shownDay ? `, ${formatDate(shownDay.date)}` : ""}
            </span>
            {selectedDay !== null && (
              <Button size="sm" onClick={() => onSelect(null)}>
                Back to today
              </Button>
            )}
          </span>
        }
      >
        The mission, day by day
      </SectionTitle>

      <div
        role="slider"
        tabIndex={0}
        aria-label="Day shown"
        aria-valuemin={1}
        aria-valuemax={currentDay}
        aria-valuenow={shown}
        aria-valuetext={`Day ${shown} din ${totalDays}`}
        onKeyDown={onKeyDown}
        onPointerDown={(event) => {
          event.currentTarget.setPointerCapture(event.pointerId);
          select(dayAt(event));
        }}
        onPointerMove={(event) => {
          if (event.buttons) select(dayAt(event));
        }}
        className="grid cursor-pointer touch-none select-none gap-[2px] rounded-md py-2"
        style={{ gridTemplateColumns: `repeat(${totalDays}, minmax(0, 1fr))` }}
      >
        {Array.from({ length: totalDays }, (_, index) => {
          const number = index + 1;
          const day = byDay.get(number);
          const future = number > currentDay;
          return (
            <span
              key={number}
              aria-hidden="true"
              className={cx(
                "h-4 rounded-[2px] transition-transform duration-150",
                future ? "bg-white/[0.05]" : CELL_TONE[day?.overall_status ?? "unknown"],
                number === shown && "scale-y-[1.75] outline outline-2 outline-offset-1 outline-solid",
                Boolean(day?.events?.length) && number !== shown && "scale-y-[1.35]",
              )}
            />
          );
        })}
      </div>

      <div className="relative mt-1 h-5 text-caption text-fg-4">
        <span className="absolute left-0">day 1</span>
        <span className="absolute -translate-x-1/2 whitespace-nowrap text-fg-3" style={{ left: `${toPercent(currentDay - 1 / (1 + 1), 0, totalDays)}%` }}>
          today, day {currentDay}
        </span>
        <span className="absolute right-0">day {totalDays}</span>
      </div>

      <p className="mt-2 flex flex-wrap items-center gap-x-4 gap-y-1 text-small text-fg-4">
        <span className="flex items-center gap-1.5">
          <span aria-hidden="true" className="size-2.5 rounded-[2px] bg-fg-5" /> within limits
        </span>
        <StatusBadge status="watch" compact />
        <StatusBadge status="alert" compact />
        <span className="flex items-center gap-1.5">
          <span aria-hidden="true" className="size-2.5 rounded-[2px] bg-white/[0.05]" /> not yet happened
        </span>
        <span>Drag, or use the arrow keys, to see a past day.</span>
      </p>
    </Card>
  );
}
