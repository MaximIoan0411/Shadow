"use client";
/**
 * Panoul unei zone a corpului. Ordinea secțiunilor e cea cerută de brief: funcția, pericolul spațial, valorile,
 * graficul, explicația, planul, sursele, limitele oneste. Tot conținutul vine din `PillarDetail`.
 */
import { useMutation, useQueryClient } from "@tanstack/react-query";
import type { ReactElement, ReactNode } from "react";
import { LineChart, type ChartSeries } from "@/components/charts/LineChart";
import { ButtonLink, Checkbox, Metric, ProblemCard, Skeleton, StatusBadge, Tag } from "@/components/ui";
import { Sheet } from "@/components/ui/overlays";
import { errorMessage, type Schemas } from "@/lib/api";
import { setPlanStep } from "@/lib/endpoints";
import { formatDateTime, formatNumber } from "@/lib/format";
import { keys, usePillar } from "@/lib/queries";
import { HAZARD_LABEL, PILLAR_META, TOPIC_META, type Pillar } from "@/lib/status";
import { useToast } from "@/lib/toast";

type PillarDetail = Schemas["PillarDetail"];
type Source = Schemas["SourceRef"];

const SIMULATED = "simulated";
const SKELETON_ROWS = ["a", "b", "c"] as const;

/** Seria unui grafic din contract, în forma pe care o desenează LineChart. */
export function toChartSeries(series: Schemas["MetricSeries"]): ChartSeries {
  return {
    key: series.metric_key,
    label: series.label,
    points: series.points.map((point) => ({ x: point.day, xLabel: `Day ${point.day}`, value: point.value, status: point.status })),
  };
}

function Section({ title, children }: { readonly title: string; readonly children: ReactNode }): ReactElement {
  return (
    <section className="border-b border-line py-5 first:pt-0 last:border-b-0">
      <h3 className="mb-2.5 text-caption font-medium uppercase tracking-[0.06em] text-fg-4">{title}</h3>
      {children}
    </section>
  );
}

/** O sursă științifică, cu marcajul „ipoteză” când nu e verificată sau pragul e ales de echipă. */
export function SourceLine({ source }: { readonly source: Source }): ReactElement {
  const hypothesis = source.verification === "unverified" || source.derivation === "derived";
  return (
    <li className="flex flex-wrap items-center gap-x-2 gap-y-1 text-small leading-relaxed">
      <a href={source.url} target="_blank" rel="noreferrer" className="text-fg-2">
        {source.citation}
      </a>
      {hypothesis && <Tag>hypothesis</Tag>}
      {source.evidence_strength && <span className="text-small text-fg-4">evidence: {source.evidence_strength}</span>}
    </li>
  );
}

function PanelBody({ detail, crewId, readOnly }: { readonly detail: PillarDetail; readonly crewId: string; readonly readOnly: boolean }): ReactElement {
  const queryClient = useQueryClient();
  const notify = useToast();
  const alertId = detail.active_alert_id;
  const step = useMutation({
    mutationFn: ({ stepId, done }: { readonly stepId: string; readonly done: boolean }) => setPlanStep(alertId ?? "", stepId, done),
    onSuccess: (alert) => {
      queryClient.setQueryData(keys.alert(alert.id), alert);
      void queryClient.invalidateQueries({ queryKey: keys.crew(crewId) });
    },
    onError: (error) => notify({ title: "The step was not saved", detail: errorMessage(error), status: "alert" }),
  });

  return (
    <div>
      <div className="mb-5 flex flex-wrap items-center gap-2">
        <StatusBadge status={detail.status} />
        {detail.score !== null && detail.score !== undefined && (
          <Tag>
            score <span className="num text-fg-2">{formatNumber(detail.score, 0)}</span> of 100
          </Tag>
        )}
        {detail.data_is_simulated && <Tag>simulated data</Tag>}
      </div>

      <Section title="What this part of the body does">
        <p className="text-base leading-relaxed text-fg">{detail.function_text}</p>
      </Section>

      <Section title={`Space hazard: ${HAZARD_LABEL[detail.hazard]}`}>
        <p className="text-base leading-relaxed text-fg-2">{detail.hazard_text}</p>
      </Section>

      <Section title="Your values, against your baseline">
        <div className="grid gap-2.5 sm:grid-cols-2">
          {detail.metrics.map((metric) => (
            <Metric
              key={metric.key}
              label={metric.label}
              value={metric.value}
              unit={metric.unit}
              baseline={metric.baseline}
              deviation={metric.deviation_abs}
              status={metric.status}
              simulated={metric.source === SIMULATED}
            />
          ))}
        </div>
      </Section>

      <Section title={`${detail.chart.label}, recent days`}>
        <LineChart
          title={`${detail.chart.label}, in ${detail.chart.unit}, by day`}
          series={[toChartSeries(detail.chart)]}
          unit={detail.chart.unit}
          baseline={detail.chart.baseline}
          bandLow={detail.chart.band_low}
          bandHigh={detail.chart.band_high}
          threshold={detail.chart.threshold}
          thresholdLabel={detail.chart.threshold_label}
        />
      </Section>

      <Section title="What is happening now">
        <p className="text-lead leading-relaxed text-fg">{detail.explanation}</p>
      </Section>

      {Boolean(detail.plan_steps.length) && (
        <Section title="Action plan">
          <div className="-mx-2 flex flex-col">
            {detail.plan_steps.map((item) => (
              <Checkbox key={item.id} checked={item.done} disabled={readOnly || !alertId || step.isPending} onChange={(done) => step.mutate({ stepId: item.id, done })}>
                {item.text}
              </Checkbox>
            ))}
          </div>
          <div className="mt-3 flex flex-wrap items-center justify-between gap-3">
            {detail.recheck_at && <p className="text-small text-fg-3">SHADOW checks again on {formatDateTime(detail.recheck_at)}.</p>}
            {alertId && (
              <ButtonLink href={`/alerts?id=${alertId}`} size="sm">
                Open alert
              </ButtonLink>
            )}
          </div>
        </Section>
      )}

      <Section title="Sources">
        <ul className="flex flex-col gap-2">
          {detail.sources.map((source) => (
            <SourceLine key={source.url + source.citation} source={source} />
          ))}
        </ul>
      </Section>

      <Section title="Honest limits">
        <p className="text-body leading-relaxed text-fg-3">{detail.limits_text}</p>
      </Section>
    </div>
  );
}

export function ZonePanel({ crewId, pillar, asOfDay, summary, onClose }: {
  readonly crewId: string;
  /** `null` = panoul e închis. */
  readonly pillar: Pillar | null;
  /** Ziua din istoric afișată; lipsește pentru „acum”. În istoric planul nu se poate bifa. */
  readonly asOfDay?: number;
  readonly summary?: Schemas["PillarSummary"];
  readonly onClose: () => void;
}): ReactElement {
  const detail = usePillar(crewId, pillar, asOfDay);
  const meta = pillar ? PILLAR_META[pillar] : null;

  return (
    <Sheet
      open={Boolean(pillar)}
      onClose={onClose}
      wide
      title={pillar ? TOPIC_META[pillar].label : (summary?.name ?? "Zone")}
      description="The function, space hazard, values, chart, plan and sources for this zone."
      eyebrow={
        meta && (
          <>
            <meta.icon size={14} strokeWidth={1.8} />
            {meta.zone}
            {asOfDay !== undefined && <Tag>day {asOfDay}</Tag>}
          </>
        )
      }
    >
      {detail.isPending && (
        <div className="flex flex-col gap-4">
          {SKELETON_ROWS.map((row) => (
            <Skeleton key={row} className="h-24" />
          ))}
        </div>
      )}
      {detail.isError && <ProblemCard title="The panel could not be loaded" detail={errorMessage(detail.error)} onRetry={() => void detail.refetch()} />}
      {detail.data && <PanelBody detail={detail.data} crewId={crewId} readOnly={asOfDay !== undefined} />}
    </Sheet>
  );
}
