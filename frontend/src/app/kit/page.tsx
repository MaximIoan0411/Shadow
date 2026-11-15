"use client";
/**
 * Catalogul viu al sistemului de design („Semnal pe negru”): tokenii și fiecare componentă, cu stările ei.
 * Datele de aici sunt exemple scrise de mână, doar pentru catalog; ecranele reale iau totul din API.
 * Documentația: frontend/DESIGN.md.
 */
import { Search } from "lucide-react";
import { useState, type ReactElement, type ReactNode } from "react";
import { BodyFigure } from "@/components/body/BodyFigure";
import { PerceptionGapCard } from "@/components/body/PerceptionGap";
import { LineChart } from "@/components/charts/LineChart";
import { MissionTimeline } from "@/components/layout/MissionTimeline";
import { Backdrop, Brand } from "@/components/layout/Shell";
import { PacketTrack } from "@/components/link/LinkConsole";
import {
  Button,
  ButtonLink,
  Card,
  Checkbox,
  EmptyState,
  Field,
  IconButton,
  Input,
  Kbd,
  LevelTag,
  Meter,
  Metric,
  Notice,
  SectionTitle,
  Segmented,
  Skeleton,
  Slider,
  StatusBadge,
  Switch,
  Tag,
  Textarea,
  Tip,
} from "@/components/ui";
import { Select } from "@/components/ui/Select";
import type { Pillar, Status } from "@/lib/status";
import { ALERT_FROM, FIRST_DAY, NIGHT_PULSE, SAMPLE_DAYS, SAMPLE_GAP, SAMPLE_PACKET, SAMPLE_PILLARS, SAMPLE_TIMELINE, SAMPLE_TODAY } from "./samples";

const NEUTRALS = [
  { token: "bg", value: "#0b0a0f", note: "background (the logo's black)", swatch: "bg-bg" },
  { token: "surface", value: "#111016", note: "sidebar", swatch: "bg-surface" },
  { token: "surface-2", value: "#17161d", note: "fields", swatch: "bg-surface-2" },
  { token: "surface-3", value: "#1e1d25", note: "buttons, menus", swatch: "bg-surface-3" },
  { token: "surface-4", value: "#27262f", note: "hover, tooltip", swatch: "bg-surface-4" },
] as const;

const TEXTS = [
  { token: "fg", note: "primary text", ratio: "12,8 – 16,9 : 1", swatch: "text-fg" },
  { token: "fg-2", note: "body text", ratio: "9,1 – 11,4 : 1", swatch: "text-fg-2" },
  { token: "fg-3", note: "secondary text", ratio: "6,4 – 7,6 : 1", swatch: "text-fg-3" },
  { token: "fg-4", note: "quiet text (AA limit)", ratio: "5,0 – 5,7 : 1", swatch: "text-fg-4" },
  { token: "fg-5", note: "decoration only, never text", ratio: "2,6 : 1", swatch: "text-fg-5" },
] as const;

const SIGNALS = [
  { token: "ok", value: "#75dbb6", status: "ok", ratio: "9,0 – 11,8 : 1" },
  { token: "watch", value: "#f5c25f", status: "watch", ratio: "9,1 – 12,0 : 1" },
  { token: "alert", value: "#fa6863", status: "alert", ratio: "5,1 – 6,8 : 1" },
] as const satisfies readonly { readonly token: string; readonly value: string; readonly status: Status; readonly ratio: string }[];

const TYPE_SCALE = [
  { cls: "text-hero", name: "hero, 44", sample: "28" },
  { cls: "text-display", name: "display, 28", sample: "61 bpm" },
  { cls: "text-title", name: "title, 18", sample: "Night pulse +7 bpm, 3 nights in a row" },
  { cls: "text-lead", name: "lead, 15", sample: "Your night pulse has been 7 bpm above your baseline for three nights." },
  { cls: "text-base", name: "base, 14", sample: "Go to bed an hour earlier for the next 3 nights." },
  { cls: "text-body", name: "body, 13.5", sample: "Morning check-in" },
  { cls: "text-small", name: "small, 12.5", sample: "your baseline 54" },
  { cls: "text-caption", name: "caption, 11.5", sample: "simulated data" },
] as const;

const STATUSES: readonly Status[] = ["ok", "watch", "alert", "unknown"];
const ENVIRONMENTS = [
  { value: "iss", label: "Space station" },
  { value: "mars_transit", label: "Mars transit" },
] as const;
type EnvironmentValue = (typeof ENVIRONMENTS)[number]["value"];
const MOODS = ["1", "2", "3", "4", "5"] as const;

function Group({ title, lead, children }: { readonly title: string; readonly lead?: string; readonly children: ReactNode }): ReactElement {
  return (
    <Card as="section" aria-label={title}>
      <SectionTitle>{title}</SectionTitle>
      {lead && <p className="mb-4 max-w-[76ch] text-body leading-relaxed text-fg-3">{lead}</p>}
      {children}
    </Card>
  );
}

export default function KitPage(): ReactElement {
  const [pillar, setPillar] = useState<Pillar | null>(null);
  const [on, setOn] = useState(true);
  const [done, setDone] = useState(false);
  const [mood, setMood] = useState<(typeof MOODS)[number]>("4");
  const [environment, setEnvironment] = useState<EnvironmentValue>("mars_transit");
  const [scale, setScale] = useState(SAMPLE_TODAY);
  const [day, setDay] = useState<number | null>(null);

  return (
    <div className="relative min-h-full bg-bg">
      <Backdrop />
      <main className="relative z-10 mx-auto flex max-w-[1180px] flex-col gap-5 px-6 pb-20 pt-10">
        <header className="mb-2">
          <Brand />
          <h1 className="mt-5 text-display font-medium tracking-[-0.02em] text-fg">The design system</h1>
          <p className="mt-2 max-w-[72ch] text-lead text-fg-3">
            Signal on black: ivory tones on the logo's black, and colour appears only when the body has something to say. Three status colours, each always with its icon and its word.
          </p>
        </header>

        <Group title="Colour: neutrals" lead="The background and four surface steps. Depth comes from tone, not from shadow.">
          <div className="grid gap-2.5 sm:grid-cols-5">
            {NEUTRALS.map((item) => (
              <div key={item.token} className="rounded-2xl border border-line-2 p-2.5">
                <div className={`h-14 rounded-xl border border-line ${item.swatch}`} />
                <p className="mt-2 text-body font-medium text-fg">{item.token}</p>
                <p className="code text-small text-fg-3">{item.value}</p>
                <p className="text-caption text-fg-4">{item.note}</p>
              </div>
            ))}
          </div>
          <div className="mt-4 grid gap-2.5 sm:grid-cols-5">
            {TEXTS.map((item) => (
              <div key={item.token} className="rounded-2xl border border-line-2 p-3">
                <p className={`text-title font-medium ${item.swatch}`}>Aa 61</p>
                <p className="mt-1 text-body font-medium text-fg">{item.token}</p>
                <p className="text-caption text-fg-4">{item.note}</p>
                <p className="num text-caption text-fg-3">{item.ratio}</p>
              </div>
            ))}
          </div>
        </Group>

        <Group title="Colour: signal" lead="The only colours in the interface. They are never used for pillars, screens, levels or decoration. Orange belongs to the logo.">
          <div className="grid gap-2.5 sm:grid-cols-3">
            {SIGNALS.map((item) => (
              <div key={item.token} className="flex items-center gap-3 rounded-2xl border border-line-2 p-3">
                <span className="size-12 shrink-0 rounded-xl" style={{ background: item.value }} />
                <span className="min-w-0 flex-1">
                  <span className="flex items-center justify-between gap-2">
                    <span className="text-body font-medium text-fg">{item.token}</span>
                    <StatusBadge status={item.status} />
                  </span>
                  <span className="code block text-small text-fg-3">{item.value}</span>
                  <span className="num block text-caption text-fg-4">contrast as text: {item.ratio}</span>
                </span>
              </div>
            ))}
          </div>
        </Group>

        <Group title="Typography" lead="Geist for everything; Geist Mono only for identifiers. Every step has a role.">
          <ul className="flex flex-col">
            {TYPE_SCALE.map((item) => (
              <li key={item.cls} className="flex items-baseline gap-5 border-t border-line py-2.5 first:border-t-0">
                <span className="w-28 shrink-0 text-small text-fg-4">{item.name}</span>
                <span className={`${item.cls} min-w-0 truncate font-medium text-fg`}>{item.sample}</span>
              </li>
            ))}
          </ul>
        </Group>

        <Group title="Status" lead="Colour, icon and word, always together. The compact variant is for dense rows; the neutral tag never carries colour.">
          <div className="flex flex-wrap items-center gap-3">
            {STATUSES.map((status) => (
              <StatusBadge key={status} status={status} />
            ))}
          </div>
          <div className="mt-3 flex flex-wrap items-center gap-4">
            {STATUSES.map((status) => (
              <StatusBadge key={status} status={status} compact />
            ))}
            <Tag>simulated data</Tag>
            <Tag>hypothesis</Tag>
            <LevelTag level={1} full />
            <LevelTag level={2} full />
            <LevelTag level={3} full />
          </div>
        </Group>

        <Group title="Buttons" lead="Pills. At most one primary button per screen.">
          <div className="flex flex-wrap items-center gap-3">
            <Button variant="primary">Save check-in</Button>
            <Button>Notify the medical officer</Button>
            <Button variant="ghost">Close alert</Button>
            <Button variant="primary" busy>
              Sending
            </Button>
            <Button disabled>Unavailable</Button>
            <ButtonLink href="/kit">Open alert</ButtonLink>
            <Tip label="Search">
              <IconButton label="Search">
                <Search size={16} strokeWidth={1.8} />
              </IconButton>
            </Tip>
            <span className="flex items-center gap-1.5 text-small text-fg-3">
              <Kbd>Ctrl</Kbd>
              <Kbd>Shift</Kbd>
              <Kbd>D</Kbd>
            </span>
          </div>
        </Group>

        <Group title="Fields" lead="Field borders have a contrast of at least 3:1 against the background. The error appears under the field, with the status icon.">
          <div className="grid gap-5 sm:grid-cols-2">
            <Field id="kit-temp" label="Temperature" hint="With the thermometer, at the same time every day.">
              <Input id="kit-temp" defaultValue="36,9" aria-describedby="kit-temp-hint" />
            </Field>
            <Field id="kit-temp-bad" label="Temperature" error="41.9 °C is outside the possible range. Measure again.">
              <Input id="kit-temp-bad" defaultValue="41,9" aria-invalid aria-describedby="kit-temp-bad-error" />
            </Field>
            <Field id="kit-note" label="Free note">
              <Textarea id="kit-note" placeholder="Write a sentence or two." />
            </Field>
            <div className="flex flex-col gap-4">
              <Segmented label="Mood" value={mood} options={MOODS.map((value) => ({ value, label: value }))} onChange={setMood} dense />
              <Select<EnvironmentValue> label="Mission environment" value={environment} options={ENVIRONMENTS} onChange={setEnvironment} />
              <span className="flex items-center gap-2.5 text-body text-fg-2">
                <Switch checked={on} onChange={setOn} label="Only thresholds used by triage" />
                Only thresholds used by triage
              </span>
              <Slider label="Day" value={scale} min={1} max={SAMPLE_DAYS} step={1} onChange={setScale} />
              <Checkbox checked={done} onChange={setDone}>
                Take your temperature morning and evening.
              </Checkbox>
            </div>
          </div>
        </Group>

        <Group title="Messages" lead="The neutral tone informs; coloured tones also carry the status icon.">
          <div className="flex flex-col gap-2.5">
            <Notice title="Today's check-in is saved (07:02)">You can send another one at any time: it replaces the previous one.</Notice>
            <Notice tone="ok" title="Reply from the Earth doctor">Agreed on rest. Temperature twice a day.</Notice>
            <Notice tone="watch" title="You are typing 18% slower than usual" action={<Button size="sm">See the plan</Button>} />
            <Notice tone="alert" title="Solar storm: go to the shelter">The dosimeter reads 6.2 times the mean of the last 24 hours.</Notice>
            <EmptyState title="No open alerts">All your values are within your in-flight baseline.</EmptyState>
            <Skeleton className="h-16 rounded-2xl" />
          </div>
        </Group>

        <Group title="Values" lead="The large value in proportional figures; your personal baseline and the deviation underneath.">
          <div className="grid gap-2.5 sm:grid-cols-3">
            <Metric label="Night pulse" value={61} unit="bpm" baseline={54} deviation={7} status="alert" simulated />
            <Metric label="Temperature" value={37.3} unit="°C" baseline={36.9} deviation={0.4} status="watch" />
            <Metric label="Sleep" value={6.6} unit="h" baseline={6.6} deviation={0} status="ok" />
          </div>
          <div className="mt-4 max-w-[420px]">
            <Meter value={68} max={100} label="Fatigue index" status="watch" />
          </div>
        </Group>

        <Group title="Chart" lead="The line is cream; only points outside your normal range take the status colour. Exact values appear on hover or with the arrow keys.">
          <LineChart
            title="Night pulse, example"
            unit="bpm"
            baseline={54}
            bandLow={52}
            bandHigh={57}
            threshold={58}
            thresholdLabel="+4 bpm, 2 nights (NightSignal)"
            series={[
              {
                key: "night_pulse_bpm",
                label: "Night pulse",
                points: NIGHT_PULSE.map((value, index) => ({ x: FIRST_DAY + index, xLabel: `Day ${FIRST_DAY + index}`, value, status: value >= ALERT_FROM ? "alert" : "ok" })),
              },
            ]}
          />
        </Group>

        <Group title="The dot language" lead="Taken from the logo: the body, the mission timeline and the packet's path are drawn from small squares. Those within limits stay neutral; deviations light up.">
          <BodyFigure pillars={SAMPLE_PILLARS} selected={pillar} onSelect={(next) => setPillar((current) => (current === next ? null : next))} />
          <div className="mt-6 grid gap-5 lg:grid-cols-[minmax(0,1fr)_380px]">
            <MissionTimeline days={SAMPLE_TIMELINE} totalDays={SAMPLE_DAYS} currentDay={SAMPLE_TODAY} selectedDay={day} onSelect={setDay} />
            <PerceptionGapCard gap={SAMPLE_GAP} canCheckIn={false} />
          </div>
          <div className="mt-5 rounded-2xl border border-line bg-white/[0.02] p-4">
            <PacketTrack packet={SAMPLE_PACKET} />
          </div>
        </Group>
      </main>
    </div>
  );
}
