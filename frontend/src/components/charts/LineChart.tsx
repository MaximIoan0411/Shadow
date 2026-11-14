"use client";
/**
 * Graficul cu linie al aplicației: o valoare în timp, față de normalul personal.
 *
 * Reguli (aceleași peste tot): linia e crem, 2px; banda normală e o tentă neutră; pragul e o linie fină în
 * culoarea alertei, cu eticheta lui; doar punctele ieșite din normal primesc culoarea stării lor; textul nu
 * poartă niciodată culoare. Valorile exacte apar la hover / cu săgețile, iar un tabel ascuns vizual le dă
 * cititoarelor de ecran.
 */
import { useMemo, useState, type KeyboardEvent, type PointerEvent, type ReactElement } from "react";
import { clamp, formatNumber } from "@/lib/format";
import { useElementWidth } from "@/lib/hooks";
import { STATUS_META, type Status } from "@/lib/status";

export interface ChartPoint {
  /** Poziția pe axa orizontală (ziua misiunii sau momentul, în ms). */
  readonly x: number;
  /** Cum se citește poziția: „Ziua 94”, „02:14”. */
  readonly xLabel: string;
  readonly value: number | null;
  readonly status?: Status | null;
}

export interface ChartSeries {
  readonly key: string;
  readonly label: string;
  readonly points: readonly ChartPoint[];
  /** Serie de referință (ex. media pe 24 h): linie mai subțire și mai stinsă. */
  readonly quiet?: boolean;
}

interface LineChartProps {
  /** Numele graficului, pentru cititoarele de ecran. */
  readonly title: string;
  readonly series: readonly ChartSeries[];
  readonly unit: string;
  readonly baseline?: number | null;
  readonly bandLow?: number | null;
  readonly bandHigh?: number | null;
  readonly threshold?: number | null;
  readonly thresholdLabel?: string | null;
  readonly height?: number;
}

interface Scales {
  readonly x: (value: number) => number;
  readonly y: (value: number) => number;
  readonly ticks: readonly number[];
  readonly left: number;
  readonly right: number;
  readonly top: number;
  readonly bottom: number;
}

const DEFAULT_HEIGHT = 220;
const PAD_LEFT = 44;
const PAD_RIGHT = 52;
const PAD_TOP = 14;
const PAD_BOTTOM = 26;
const TARGET_TICKS = 3;
const DOMAIN_PADDING = 0.12;
const DECIMAL_BASE = 10;
const TWO = 2;
const FIVE = 5;
const NICE_MULTIPLIERS: readonly number[] = [1, TWO, FIVE, DECIMAL_BASE];
const POINT_RADIUS = 4.5;
const LABEL_GAP = 8;
const TICK_LABEL_OFFSET = 4;
const X_LABEL_OFFSET = 18;
const TOOLTIP_HALF_WIDTH = 90;
const TOOLTIP_TOP = 4;
const OFF_NORMAL: readonly Status[] = ["watch", "alert"];
const KEY_STEP: Readonly<Record<string, number>> = { ArrowLeft: -1, ArrowRight: 1 };

const isNumber = (value: number | null | undefined): value is number => typeof value === "number" && Number.isFinite(value);

/** Pas „rotund” pentru axa verticală: 1, 2 sau 5 înmulțit cu o putere a lui 10. */
function niceStep(rough: number): number {
  if (!(rough > 0)) return 1;
  const magnitude = DECIMAL_BASE ** Math.floor(Math.log10(rough));
  const multiplier = NICE_MULTIPLIERS.find((candidate) => candidate * magnitude >= rough) ?? DECIMAL_BASE;
  return multiplier * magnitude;
}

function buildScales(props: LineChartProps, width: number, height: number): Scales | null {
  const points = props.series.flatMap((series) => series.points);
  const values = [...points.map((point) => point.value), props.baseline, props.bandLow, props.bandHigh, props.threshold].filter(isNumber);
  const xs = points.map((point) => point.x);
  if (!values.length || !xs.length || width <= PAD_LEFT + PAD_RIGHT) return null;

  const rawMin = Math.min(...values);
  const rawMax = Math.max(...values);
  const span = rawMax - rawMin || Math.abs(rawMax) || 1;
  const step = niceStep((span * (1 + DOMAIN_PADDING * TWO)) / TARGET_TICKS);
  const yMin = Math.floor((rawMin - span * DOMAIN_PADDING) / step) * step;
  const yMax = Math.ceil((rawMax + span * DOMAIN_PADDING) / step) * step;
  const tickCount = Math.round((yMax - yMin) / step) + 1;
  const ticks = Array.from({ length: tickCount }, (_, index) => yMin + index * step);

  const xMin = Math.min(...xs);
  const xMax = Math.max(...xs);
  const left = PAD_LEFT;
  const right = width - PAD_RIGHT;
  const top = PAD_TOP;
  const bottom = height - PAD_BOTTOM;
  return {
    x: (value) => (xMax === xMin ? (left + right) / TWO : left + ((value - xMin) / (xMax - xMin)) * (right - left)),
    y: (value) => bottom - ((value - yMin) / (yMax - yMin || 1)) * (bottom - top),
    ticks,
    left,
    right,
    top,
    bottom,
  };
}

/** Linia unei serii ca drum SVG; o valoare lipsă întrerupe linia în loc s-o unească peste gol. */
function linePath(points: readonly ChartPoint[], scales: Scales): string {
  return points
    .reduce<{ readonly d: string; readonly pen: boolean }>(
      (path, point) => {
        if (!isNumber(point.value)) return { d: path.d, pen: false };
        const command = path.pen ? "L" : "M";
        return { d: `${path.d}${command}${scales.x(point.x).toFixed(1)} ${scales.y(point.value).toFixed(1)}`, pen: true };
      },
      { d: "", pen: false },
    )
    .d;
}

export function LineChart(props: LineChartProps): ReactElement {
  const { title, series, unit, baseline, bandLow, bandHigh, threshold, thresholdLabel, height = DEFAULT_HEIGHT } = props;
  const [ref, width] = useElementWidth<HTMLDivElement>();
  const [active, setActive] = useState<number | null>(null);
  const scales = useMemo(() => buildScales(props, width, height), [props, width, height]);
  const primary = series[0];
  const primaryPoints = primary?.points ?? [];
  const lastIndex = primaryPoints.length - 1;

  const nearestIndex = (clientX: number, bounds: DOMRect): number => {
    if (!scales) return 0;
    const pointerX = clientX - bounds.left;
    return primaryPoints.reduce((best, point, index) => {
      const bestPoint = primaryPoints[best];
      const bestDistance = bestPoint ? Math.abs(scales.x(bestPoint.x) - pointerX) : Infinity;
      return Math.abs(scales.x(point.x) - pointerX) < bestDistance ? index : best;
    }, 0);
  };

  const onPointerMove = (event: PointerEvent<HTMLDivElement>): void => {
    setActive(nearestIndex(event.clientX, event.currentTarget.getBoundingClientRect()));
  };

  const onKeyDown = (event: KeyboardEvent<HTMLDivElement>): void => {
    const step = KEY_STEP[event.key];
    if (step === undefined) return;
    event.preventDefault();
    setActive((current) => clamp((current ?? lastIndex) + step, 0, lastIndex));
  };

  const activePoint = active === null ? undefined : primaryPoints[active];
  const lastPoint = primaryPoints.findLast((point) => isNumber(point.value));
  const xLabels = [primaryPoints[0], primaryPoints[Math.floor(lastIndex / TWO)], primaryPoints[lastIndex]].filter(
    (point, index, all): point is ChartPoint => Boolean(point) && all.indexOf(point) === index,
  );

  return (
    <figure className="m-0">
      {series.length > 1 && (
        <ul className="mb-2 flex flex-wrap gap-x-4 gap-y-1 text-small text-fg-3">
          {series.map((item) => (
            <li key={item.key} className="flex items-center gap-2">
              <span aria-hidden="true" className={item.quiet ? "h-px w-4 bg-fg-4" : "h-0.5 w-4 rounded-full bg-fg"} />
              {item.label}
            </li>
          ))}
        </ul>
      )}
      <div
        ref={ref}
        role="img"
        aria-label={`${title}. Use the left and right arrow keys for values.`}
        tabIndex={0}
        onPointerMove={onPointerMove}
        onPointerLeave={() => setActive(null)}
        onBlur={() => setActive(null)}
        onKeyDown={onKeyDown}
        className="relative w-full touch-none select-none rounded-xl"
        style={{ height }}
      >
        {scales && (
          <svg width={width} height={height} aria-hidden="true" className="block overflow-visible">
            {scales.ticks.map((tick) => (
              <g key={tick}>
                <line x1={scales.left} x2={scales.right} y1={scales.y(tick)} y2={scales.y(tick)} stroke="rgb(var(--tint) / 0.07)" strokeWidth={1} />
                <text x={scales.left - LABEL_GAP} y={scales.y(tick) + TICK_LABEL_OFFSET} textAnchor="end" className="num fill-fg-4 text-[11px]">
                  {formatNumber(tick)}
                </text>
              </g>
            ))}
            {isNumber(bandLow) && isNumber(bandHigh) && (
              <rect x={scales.left} width={scales.right - scales.left} y={scales.y(bandHigh)} height={Math.max(0, scales.y(bandLow) - scales.y(bandHigh))} fill="rgb(var(--tint) / 0.06)" />
            )}
            {isNumber(baseline) && <line x1={scales.left} x2={scales.right} y1={scales.y(baseline)} y2={scales.y(baseline)} stroke="var(--color-fg-4)" strokeWidth={1} />}
            {isNumber(threshold) && <line x1={scales.left} x2={scales.right} y1={scales.y(threshold)} y2={scales.y(threshold)} stroke="var(--color-alert)" strokeWidth={1} />}
            {series.map((item) => (
              <path
                key={item.key}
                d={linePath(item.points, scales)}
                fill="none"
                stroke={item.quiet ? "var(--color-fg-4)" : "var(--color-fg)"}
                strokeWidth={item.quiet ? 1 : TWO}
                strokeLinejoin="round"
                strokeLinecap="round"
              />
            ))}
            {primaryPoints.map((point) =>
              isNumber(point.value) && point.status && OFF_NORMAL.includes(point.status) ? (
                <circle key={point.x} cx={scales.x(point.x)} cy={scales.y(point.value)} r={POINT_RADIUS} fill={STATUS_META[point.status].color} stroke="var(--color-surface)" strokeWidth={2} />
              ) : null,
            )}
            {lastPoint && isNumber(lastPoint.value) && (
              <>
                {!(lastPoint.status && OFF_NORMAL.includes(lastPoint.status)) && (
                  <circle cx={scales.x(lastPoint.x)} cy={scales.y(lastPoint.value)} r={POINT_RADIUS} fill="var(--color-fg)" stroke="var(--color-surface)" strokeWidth={2} />
                )}
                <text x={scales.x(lastPoint.x) + LABEL_GAP} y={scales.y(lastPoint.value) + TICK_LABEL_OFFSET} className="num fill-fg text-[12px] font-medium">
                  {formatNumber(lastPoint.value)}
                </text>
              </>
            )}
            {xLabels.map((point) => (
              <text key={point.x} x={scales.x(point.x)} y={scales.bottom + X_LABEL_OFFSET} textAnchor="middle" className="fill-fg-4 text-[11px]">
                {point.xLabel}
              </text>
            ))}
            {activePoint && (
              <line x1={scales.x(activePoint.x)} x2={scales.x(activePoint.x)} y1={scales.top} y2={scales.bottom} stroke="rgb(var(--tint) / 0.3)" strokeWidth={1} />
            )}
          </svg>
        )}
        {scales && activePoint && active !== null && (
          <div
            className="pointer-events-none absolute z-10 min-w-[120px] rounded-lg border border-line-2 bg-surface-4 px-2.5 py-1.5 text-small shadow-[0_8px_24px_rgb(0_0_0/0.5)]"
            style={{ left: clamp(scales.x(activePoint.x) - TOOLTIP_HALF_WIDTH, 0, Math.max(0, width - TOOLTIP_HALF_WIDTH * TWO)), top: TOOLTIP_TOP }}
          >
            <p className="text-fg-3">{activePoint.xLabel}</p>
            {series.map((item) => {
              const point = item.points[active];
              return (
                <p key={item.key} className="flex items-center justify-between gap-3 text-fg">
                  <span className="text-fg-3">{series.length > 1 ? item.label : unit}</span>
                  <span className="num font-medium">
                    {formatNumber(point?.value)}
                    {series.length > 1 ? ` ${unit}` : ""}
                  </span>
                </p>
              );
            })}
            {activePoint.status && <p style={{ color: STATUS_META[activePoint.status].color }}>{`${STATUS_META[activePoint.status].shape} ${STATUS_META[activePoint.status].label}`}</p>}
          </div>
        )}
      </div>
      {(isNumber(baseline) || isNumber(threshold) || (isNumber(bandLow) && isNumber(bandHigh))) && (
        <ul className="mt-1 flex flex-wrap gap-x-4 gap-y-1 text-caption text-fg-3">
          {isNumber(baseline) && (
            <li className="flex items-center gap-2">
              <span aria-hidden="true" className="h-px w-4 bg-fg-4" />
              your baseline: {formatNumber(baseline)} {unit}
            </li>
          )}
          {isNumber(bandLow) && isNumber(bandHigh) && (
            <li className="flex items-center gap-2">
              <span aria-hidden="true" className="h-2.5 w-4 rounded-[2px] bg-white/[0.1]" />
              your normal band
            </li>
          )}
          {isNumber(threshold) && (
            <li className="flex items-center gap-2">
              <span aria-hidden="true" className="h-px w-4 bg-alert" />
              {thresholdLabel ? `alert threshold: ${thresholdLabel}` : "alert threshold"}
            </li>
          )}
        </ul>
      )}
      <table className="sr-only">
        <caption>{title}</caption>
        <thead>
          <tr>
            <th scope="col">Time</th>
            {series.map((item) => (
              <th key={item.key} scope="col">{`${item.label} (${unit})`}</th>
            ))}
          </tr>
        </thead>
        <tbody>
          {primaryPoints.map((point, index) => (
            <tr key={point.x}>
              <th scope="row">{point.xLabel}</th>
              {series.map((item) => (
                <td key={item.key}>{formatNumber(item.points[index]?.value)}</td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
    </figure>
  );
}
