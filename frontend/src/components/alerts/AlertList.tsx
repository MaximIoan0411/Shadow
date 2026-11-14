"use client";
import Link from "next/link";
import type { ReactElement } from "react";
import { LevelTag, StatusBadge, Tag, cx } from "@/components/ui";
import type { Schemas } from "@/lib/api";
import { formatDateTime } from "@/lib/format";
import { ALERT_STATE_LABEL, TOPIC_META, statusRank } from "@/lib/status";

type AlertBrief = Schemas["AlertBrief"];

/** Cele mai grave întâi; la aceeași gravitate, nivelul mai mare, apoi cele mai noi. */
export function sortAlerts(alerts: readonly AlertBrief[]): AlertBrief[] {
  return alerts.toSorted(
    (a, b) => statusRank(b.status) - statusRank(a.status) || b.level - a.level || b.created_at.localeCompare(a.created_at),
  );
}

/** Lista de alerte: fiecare rând duce la alerta lui. `crewNames` arată al cui e rândul (coada ofițerului medical). */
export function AlertList({ alerts, selectedId, crewNames }: {
  readonly alerts: readonly AlertBrief[];
  readonly selectedId?: string | null;
  readonly crewNames?: ReadonlyMap<string, string>;
}): ReactElement {
  return (
    <ul className="flex flex-col gap-2">
      {sortAlerts(alerts).map((alert) => {
        const topic = TOPIC_META[alert.topic];
        const selected = alert.id === selectedId;
        return (
          <li key={alert.id}>
            <Link
              href={`/alerts?id=${alert.id}`}
              aria-current={selected ? "true" : undefined}
              className={cx(
                "block rounded-2xl border p-3.5 no-underline transition-colors",
                selected ? "border-line-4 bg-white/[0.07]" : "border-line-2 bg-white/[0.02] hover:border-line-3 hover:bg-white/[0.05]",
              )}
            >
              <span className="flex items-center justify-between gap-2">
                <span className="flex min-w-0 items-center gap-2 text-small text-fg-3">
                  <topic.icon size={14} strokeWidth={1.8} className="shrink-0" />
                  <span className="truncate">{crewNames?.get(alert.crew_id) ?? topic.label}</span>
                </span>
                <StatusBadge status={alert.status} compact />
              </span>
              <span className="mt-1.5 block text-base font-medium leading-snug text-fg">{alert.title}</span>
              <span className="mt-2 flex flex-wrap items-center gap-2">
                <LevelTag level={alert.level} />
                <Tag>{ALERT_STATE_LABEL[alert.state]}</Tag>
                <span className="num text-caption text-fg-4">{formatDateTime(alert.created_at)}</span>
              </span>
            </Link>
          </li>
        );
      })}
    </ul>
  );
}
