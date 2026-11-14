"use client";
/**
 * Radiațiile: dozimetrul de la bord, curba dozei și, în timpul unei furtuni solare, cu câte minute a dat SHADOW
 * alerta înaintea avertizării venite de pe Pământ. Evenimentul e real (NASA DONKI, 11 mai 2024); forma curbei
 * e sintetică și e etichetată așa.
 */
import { useMutation, useQueryClient } from "@tanstack/react-query";
import type { ReactElement } from "react";
import { LineChart, type ChartSeries } from "@/components/charts/LineChart";
import { Page } from "@/components/layout/Shell";
import { Button, Card, Notice, ProblemCard, SectionTitle, Skeleton, StatusBadge, Tag } from "@/components/ui";
import { errorMessage, type Schemas } from "@/lib/api";
import { ackShelter } from "@/lib/endpoints";
import { formatDateTime, formatFullDateTime, formatNumber, formatTime } from "@/lib/format";
import { keys, useRadiationSeries, useRadiationStatus } from "@/lib/queries";
import { useToast } from "@/lib/toast";

type RadiationStatus = Schemas["RadiationStatus"];
type RadiationSeries = Schemas["RadiationSeries"];

const UNIT = "µSv/h";
const TWO_DECIMALS = 2;

function toSeries(series: RadiationSeries): readonly ChartSeries[] {
  const at = (iso: string): number => new Date(iso).getTime();
  return [
    { key: "dose", label: "Dose rate", points: series.points.map((point) => ({ x: at(point.t), xLabel: formatDateTime(point.t), value: point.dose_rate_usv_h })) },
    { key: "mean", label: "24 h mean", quiet: true, points: series.points.map((point) => ({ x: at(point.t), xLabel: formatDateTime(point.t), value: point.mean_24h_usv_h })) },
  ];
}

function Reading({ status }: { readonly status: RadiationStatus }): ReactElement {
  const queryClient = useQueryClient();
  const notify = useToast();
  const shelter = useMutation({
    mutationFn: ackShelter,
    onSuccess: (next) => queryClient.setQueryData(keys.radiationStatus, next),
    onError: (error) => notify({ title: "Could not save", detail: errorMessage(error), status: "alert" }),
  });

  return (
    <Card as="section" aria-labelledby="dose-title">
      <SectionTitle id="dose-title" right={<StatusBadge status={status.alert_active ? "alert" : "ok"} label={status.alert_active ? "Above threshold" : "Below threshold"} />}>
        On-board dosimeter
      </SectionTitle>
      <p className="flex items-baseline gap-2">
        <span className="text-hero font-medium tracking-[-0.03em] text-fg">{formatNumber(status.dose_rate_usv_h)}</span>
        <span className="text-body text-fg-3">{UNIT}</span>
      </p>
      <dl className="mt-4 grid grid-cols-2 gap-2.5">
        <div className="rounded-2xl border border-line bg-white/[0.02] p-3.5">
          <dt className="text-small text-fg-3">Against the 24 h mean</dt>
          <dd className="mt-1.5 text-display font-medium tracking-[-0.02em] text-fg">×{formatNumber(status.ratio, TWO_DECIMALS)}</dd>
          <dd className="mt-2 text-small text-fg-4">alert from ×{formatNumber(status.threshold_ratio)}</dd>
        </div>
        <div className="rounded-2xl border border-line bg-white/[0.02] p-3.5">
          <dt className="text-small text-fg-3">Dose from the event</dt>
          <dd className="mt-1.5 flex items-baseline gap-1.5">
            <span className="text-display font-medium tracking-[-0.02em] text-fg">{formatNumber(status.event_dose_msv, TWO_DECIMALS)}</span>
            <span className="text-small text-fg-4">mSv</span>
          </dd>
          <dd className="mt-2 text-small text-fg-4">24 h mean: {formatNumber(status.mean_24h_usv_h)} {UNIT}</dd>
        </div>
      </dl>
      <div className="mt-4 flex flex-wrap items-center gap-3">
        <Button variant={status.alert_active && !status.sheltered ? "primary" : "secondary"} busy={shelter.isPending} onClick={() => shelter.mutate(!status.sheltered)}>
          {status.sheltered ? "I have left the shelter" : "I am in the shelter"}
        </Button>
        <p className="text-small text-fg-3">
          {status.sheltered && status.sheltered_since ? `Sheltered since ${formatTime(status.sheltered_since)}; shielding lowers the dose.` : "The shelter is the most shielded part of the ship."}
        </p>
      </div>
    </Card>
  );
}

function LeadTime({ status }: { readonly status: RadiationStatus }): ReactElement | null {
  if (!status.onboard_alert_at) return null;
  const lead = status.lead_minutes;
  return (
    <Card as="section" aria-labelledby="lead-title">
      <SectionTitle id="lead-title">SHADOW versus Earth</SectionTitle>
      {lead !== null && lead !== undefined ? (
        <p className="flex items-baseline gap-3">
          <span className="text-hero font-medium tracking-[-0.03em] text-fg">{formatNumber(lead, 0)}</span>
          <span className="text-body leading-snug text-fg-3">
            minutes: sheltered before
            <br />
            the warning from Earth
          </span>
        </p>
      ) : (
        <p className="shimmer-text text-base">The warning from Earth is still on its way…</p>
      )}
      <ol className="mt-4 flex flex-col gap-2 text-body">
        <li className="flex justify-between gap-3">
          <span className="text-fg-2">On-board dosimeter alert</span>
          <span className="num text-fg">{formatTime(status.onboard_alert_at)}</span>
        </li>
        <li className="flex justify-between gap-3">
          <span className="text-fg-2">NASA DONKI warning, arrived over the link</span>
          <span className="num text-fg">{formatTime(status.earth_warning_arrived_at)}</span>
        </li>
      </ol>
    </Card>
  );
}

function EventCard({ event }: { readonly event: NonNullable<RadiationStatus["event"]> }): ReactElement {
  return (
    <Card as="section" aria-labelledby="event-title">
      <SectionTitle id="event-title" right={<Tag>real event</Tag>}>
        The storm replayed by the simulator
      </SectionTitle>
      <p className="text-base font-medium text-fg">{event.note}</p>
      <dl className="mt-3 grid grid-cols-[auto_minmax(0,1fr)] gap-x-4 gap-y-1.5 text-body">
        <dt className="text-fg-3">Flare</dt>
        <dd className="num text-fg">{event.flare_class}</dd>
        <dt className="text-fg-3">Instrument</dt>
        <dd className="text-fg">{event.instrument}</dd>
        <dt className="text-fg-3">When it happened</dt>
        <dd className="num text-fg">{formatFullDateTime(event.event_time)}</dd>
        <dt className="text-fg-3">In the mission</dt>
        <dd className="num text-fg">{formatDateTime(event.sim_onset_at)}</dd>
      </dl>
      <p className="mt-3 text-small">
        <a href={event.donki_url} target="_blank" rel="noreferrer">
          {event.donki_id} in NASA DONKI
        </a>
      </p>
    </Card>
  );
}

export default function RadiationPage(): ReactElement {
  const status = useRadiationStatus(true);
  const series = useRadiationSeries(true);
  const failure = status.error ?? series.error;
  const latestMean = series.data?.points.at(-1)?.mean_24h_usv_h;
  const threshold = latestMean !== undefined && series.data ? latestMean * series.data.threshold_ratio : null;

  return (
    <Page>
      {(status.isPending || series.isPending) && <Skeleton className="h-[420px] rounded-[var(--radius-card)]" />}
      {failure && (
        <ProblemCard
          title="Radiation data could not be loaded"
          detail={errorMessage(failure)}
          onRetry={() => {
            void status.refetch();
            void series.refetch();
          }}
        />
      )}
      {status.data && series.data && (
        <div className="grid items-start gap-5 xl:grid-cols-[minmax(0,1fr)_400px]">
          <div className="flex min-w-0 flex-col gap-5">
            <Card as="section" aria-labelledby="curve-title">
              <SectionTitle id="curve-title" right={status.data.profile_is_synthetic ? <Tag>synthetic curve</Tag> : undefined}>
                Dose rate, last 24 hours
              </SectionTitle>
              <LineChart
                title="Dose rate at the on-board dosimeter and the 24-hour mean"
                series={toSeries(series.data)}
                unit={UNIT}
                threshold={threshold}
                thresholdLabel={`${formatNumber(series.data.threshold_ratio)} × the 24 h mean`}
                height={300}
              />
              <p className="mt-3 text-small leading-relaxed text-fg-3">
                The alert fires after 3 consecutive readings above the threshold. The time and class of the event are real; the shape of the curve is synthetic, because the dose measured in 2024 is not published.
              </p>
            </Card>
            {!status.data.event && (
              <Notice title="No solar storm in progress">For the demo, start the event from the demo panel (the icon in the header, or Ctrl+Shift+D).</Notice>
            )}
          </div>
          <div className="flex flex-col gap-5">
            <Reading status={status.data} />
            <LeadTime status={status.data} />
            {status.data.event && <EventCard event={status.data.event} />}
          </div>
        </div>
      )}
    </Page>
  );
}
