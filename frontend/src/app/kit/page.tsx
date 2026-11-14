"use client";
/**
 * /kit — catalogul componentelor SHADOW (stilul Quaternion), compuse ca un ecran real.
 * Date statice, luate din scenariul mock (ziua 96). Nu apelează backend-ul: e referința vizuală a echipei.
 */
import { motion } from "motion/react";
import { ArrowUpRight, Brain, HeartPulse, Bone, ShieldPlus, Sparkles, Siren } from "lucide-react";
import type { CSSProperties, ReactElement } from "react";
import { useState } from "react";
import { Button, Card, Dot, Input, Kbd, Metric, Orb, PillarTag, ProblemCard, SectionTitle, Segmented, Slider, StatusBadge, Switch, Tip, cx, easeOut, rise } from "@/components/ui";
import { Select } from "@/components/ui/Select";
import { Header, SHIP_NAV, Screen, Sidebar, type NavItem } from "@/components/layout/Shell";
import { PILLAR_HUE } from "@/lib/hues";
import type { components } from "@/lib/shadow-api";

type Status = components["schemas"]["Status"];
type Pillar = components["schemas"]["Pillar"];

// Scorurile din scenariul mock (ziua 96), ca în GET /crew/cm-2/dashboard.
const SCORE_BEHAVIORAL = 71;
const SCORE_CARDIO = 88;
const SCORE_IMMUNE = 58;
const SCORE_MUSCULOSKELETAL = 82;

const PILLARS: readonly { pillar: Pillar; name: string; status: Status; score: number; headline: string; icon: typeof Brain }[] = [
  { pillar: "behavioral", name: "Tastatura", status: "watch", score: SCORE_BEHAVIORAL, headline: "Tastezi cu 18% mai lent decât de obicei", icon: Brain },
  { pillar: "cardio", name: "Inima", status: "ok", score: SCORE_CARDIO, headline: "În limitele tale din zbor", icon: HeartPulse },
  { pillar: "immune", name: "Santinela", status: "alert", score: SCORE_IMMUNE, headline: "Puls de noapte crescut 3 nopți la rând", icon: ShieldPlus },
  { pillar: "musculoskeletal", name: "Încărcarea", status: "ok", score: SCORE_MUSCULOSKELETAL, headline: "1 din 2 sesiuni făcute azi", icon: Bone },
];

const MOODS = ["1", "2", "3", "4", "5"] as const;
const ENVIRONMENTS = [
  { value: "iss", label: "Stația spațială", detail: "întârziere sub 1 s" },
  { value: "mars_transit", label: "Tranzit spre Marte", detail: "întârziere 3–22 min" },
] as const;
const PACKET_PROGRESS = 0.64;
const BAR_SECONDS = 0.9;
const DEFAULT_TIME_SCALE = 60;
const PERCENT = 100;

function PerceptionGap(): ReactElement {
  const self = 80;
  const objective = 52;
  return (
    <Card as="section" aria-labelledby="gap-h" className="relative overflow-hidden">
      <SectionTitle id="gap-h" right={<StatusBadge status="alert" />}>
        Decalajul de percepție
      </SectionTitle>
      <p className="max-w-[46ch] text-[15px] leading-relaxed text-fg-2">
        Spui că ești bine <span className="num text-fg">(4/5)</span>, dar tastezi cu <span className="num text-fg">18%</span> mai lent și pulsul
        de noapte a crescut.
      </p>
      <div className="mt-5 grid gap-3">
        {[
          { label: "Cum spui că te simți", value: self, hue: "var(--color-steel)" },
          { label: "Ce arată datele", value: objective, hue: "var(--color-status-alert)" },
        ].map((b) => (
          <div key={b.label}>
            <div className="mb-1.5 flex justify-between text-[12.5px] text-fg-3">
              <span>{b.label}</span>
              <span className="num text-fg-2">{b.value}</span>
            </div>
            <div className="h-2 overflow-hidden rounded-full bg-white/[0.06]">
              <motion.div
                className="h-full rounded-full"
                style={{ background: b.hue }}
                initial={{ width: 0 }}
                animate={{ width: `${b.value}%` }}
                transition={{ duration: BAR_SECONDS, ease: easeOut }}
              />
            </div>
          </div>
        ))}
      </div>
      <p className="num mt-4 text-[12.5px] text-fg-4">diferență {self - objective} puncte</p>
    </Card>
  );
}

function PillarList(): ReactElement {
  return (
    <Card as="section" aria-labelledby="pillars-h">
      <SectionTitle id="pillars-h">Cei patru piloni</SectionTitle>
      <ul className="grid gap-1">
        {PILLARS.map((p) => (
          <li key={p.pillar}>
            <button
              type="button"
              className="group flex w-full items-center gap-3.5 rounded-2xl px-3 py-3 text-left transition-colors hover:bg-white/[0.04]"
              style={{ "--p": PILLAR_HUE[p.pillar] } as CSSProperties}
            >
              <span className="grid size-9 shrink-0 place-items-center rounded-xl border border-line-2 bg-[color-mix(in_oklab,var(--p)_10%,transparent)] text-[var(--p)]">
                <p.icon size={17} strokeWidth={1.8} />
              </span>
              <span className="min-w-0 flex-1">
                <PillarTag pillar={p.pillar} name={p.name} className="text-fg" />
                <span className="mt-0.5 block truncate text-[12.5px] text-fg-3">{p.headline}</span>
              </span>
              <span className="w-8 text-right text-[15px] text-fg-2 tabular-nums">{p.score}</span>
              <StatusBadge status={p.status} />
              <ArrowUpRight size={15} className="text-fg-5 transition-colors group-hover:text-fg-3" />
            </button>
          </li>
        ))}
      </ul>
    </Card>
  );
}

function Controls(): ReactElement {
  const [mood, setMood] = useState<(typeof MOODS)[number]>("4");
  const [env, setEnv] = useState<string>("mars_transit");
  const [on, setOn] = useState(true);
  const [speed, setSpeed] = useState(DEFAULT_TIME_SCALE);
  return (
    <Card as="section" aria-labelledby="controls-h">
      <SectionTitle id="controls-h">Controale</SectionTitle>
      <div className="grid gap-5">
        <div className="flex flex-wrap items-center gap-2">
          <Button variant="primary">Trimite check-in-ul</Button>
          <Button>Anunță ofițerul medical</Button>
          <Button variant="ghost">Mai târziu</Button>
          <Button variant="danger">Închide alerta</Button>
        </div>
        <div className="grid gap-1.5">
          <span className="text-[12.5px] text-fg-3">Starea de spirit</span>
          <Segmented label="Starea de spirit" value={mood} onChange={setMood} options={MOODS.map((m) => ({ value: m, label: m }))} dense />
        </div>
        <div className="grid gap-1.5">
          <label htmlFor="temp" className="text-[12.5px] text-fg-3">
            Temperatura <span className="text-fg-5">°C</span>
          </label>
          <Input id="temp" inputMode="decimal" defaultValue="41.9" aria-invalid="true" className="num max-w-[160px]" />
          <span className="text-[12px] text-danger">41,9 °C e în afara intervalului posibil. Măsoară din nou.</span>
        </div>
        <div className="flex flex-wrap items-center gap-4">
          <Select label="Mediul misiunii" value={env} onChange={setEnv} options={ENVIRONMENTS} />
          <label className="flex items-center gap-2.5 text-[13px] text-fg-2">
            <Switch checked={on} onChange={setOn} label="Reamintiri" /> Reamintiri
          </label>
        </div>
        <div className="grid gap-1.5">
          <span className="flex justify-between text-[12.5px] text-fg-3">
            Viteza ceasului <span className="num text-fg-2">×{speed}</span>
          </span>
          <Slider label="Viteza ceasului" value={speed} min={1} max={240} step={1} onChange={setSpeed} hue="var(--hue-a)" />
        </div>
        <p className="flex items-center gap-2 text-[12.5px] text-fg-4">
          Panoul de demo: <Kbd>Ctrl</Kbd>
          <Kbd>Shift</Kbd>
          <Kbd>D</Kbd>
        </p>
      </div>
    </Card>
  );
}

function Metrics(): ReactElement {
  return (
    <Card as="section" aria-labelledby="metrics-h">
      <SectionTitle id="metrics-h" right={<PillarTag pillar="immune" name="Santinela" />}>
        Valori față de normalul tău
      </SectionTitle>
      <div className="grid gap-3 sm:grid-cols-2">
        <Metric label="Puls de noapte" value={61} unit="bpm" baseline={54} deviation="+7" status="alert" simulated />
        <Metric label="Temperatura" value={37.3} unit="°C" baseline={36.9} deviation="+0,4" status="watch" />
        <Metric label="Somn" value={5.5} unit="h" baseline={6.6} deviation="−1,1" status="watch" />
        <Metric label="Indice de stres" value={null} unit="/100" status="unknown" />
      </div>
    </Card>
  );
}

function Link(): ReactElement {
  return (
    <Card as="section" aria-labelledby="link-h" className="relative overflow-hidden">
      <SectionTitle id="link-h" right={<span className="num text-[12px] text-fg-4">Ed25519 ✓</span>}>
        Pachet spre Pământ
      </SectionTitle>
      <p className="text-[14px] text-fg-2">Imunitar · puls de noapte +7 bpm, 3 nopți</p>
      <p className="shimmer-text mt-1 text-[12.5px]">Pe drum · ajunge în 4 s</p>
      <div className="relative mt-5 h-7" role="img" aria-label={`Pachetul e la ${PACKET_PROGRESS * PERCENT}% din drum`}>
        <span className="num absolute -top-1 left-0 text-[11px] text-fg-4">NAVA</span>
        <span className="num absolute -top-1 right-0 text-[11px] text-fg-4">PĂMÂNT</span>
        <div className="absolute inset-x-0 top-[18px] h-0.5 bg-[radial-gradient(rgb(var(--tint)/0.18)_1px,transparent_1.2px)] bg-[length:8px_2px]" />
        <div className="absolute left-0 top-[18px] h-0.5 rounded-full bg-amber" style={{ width: `${PACKET_PROGRESS * PERCENT}%` }} />
        <span className="absolute top-[13px] size-3 rotate-45 rounded-[2px] bg-amber shadow-[0_0_12px_var(--color-amber)]" style={{ left: `calc(${PACKET_PROGRESS * PERCENT}% - 6px)` }} />
      </div>
    </Card>
  );
}

function AiCard(): ReactElement {
  const [busy, setBusy] = useState(true);
  return (
    <Card as="section" aria-labelledby="ai-h" className="relative">
      <span className="glow-ring" data-on={busy ? "true" : "false"} />
      <SectionTitle id="ai-h" right={<StatusBadge status="unknown" label="model: mock" />}>
        Medicul AI de bord
      </SectionTitle>
      {busy ? (
        <p className="shimmer-text text-[14px]">Caută în documentele NASA…</p>
      ) : (
        <div className="prose-q">
          <p>
            Pulsul tău de noapte e cu <strong>7 bpm</strong> peste normalul tău de trei nopți. Anunță ofițerul medical și protejează-ți somnul.
          </p>
        </div>
      )}
      <div className="mt-4 flex items-center justify-between gap-3">
        <a className="text-[12.5px] text-periwinkle underline decoration-periwinkle/35 underline-offset-[3px]" href="https://www.nature.com/articles/s41591-021-01593-2">
          Alavi et al. (2022), Nature Medicine
        </a>
        <Button size="sm" variant="ghost" onClick={() => setBusy((b) => !b)}>
          <Sparkles size={13} /> {busy ? "Arată răspunsul" : "Din nou"}
        </Button>
      </div>
      <p className="mt-3 text-[11.5px] text-fg-4">Prototip de sprijin, nu dispozitiv medical.</p>
    </Card>
  );
}

function StormBanner(): ReactElement {
  return (
    <div role="alert" className="float-q flex flex-wrap items-center gap-4 rounded-[var(--radius-card)] border-danger/30 p-4" style={{ borderColor: "color-mix(in oklab, var(--color-danger) 35%, transparent)" }}>
      <span className="grid size-10 place-items-center rounded-2xl bg-danger/15 text-danger">
        <Siren size={19} strokeWidth={1.9} />
      </span>
      <div className="min-w-0 flex-1">
        <p className="text-[15px] font-medium text-fg">Mergi în adăpost</p>
        <p className="text-[13px] text-fg-3">
          Rata dozei e de <span className="num text-fg">6,2×</span> media pe 24 h. Furtună solară reală, NASA DONKI, 11 mai 2024 · curbă sintetică.
        </p>
      </div>
      <Button variant="primary">Sunt în adăpost</Button>
    </div>
  );
}

function EmptyState(): ReactElement {
  return (
    <Card className="grid place-items-center py-10 text-center">
      <Orb size={52} />
      <p className="mt-5 text-[15px] font-medium text-fg">Nicio alertă</p>
      <p className="mt-1 max-w-[34ch] text-[13px] text-fg-3">Toți cei patru piloni sunt în limitele normalului tău.</p>
    </Card>
  );
}

export default function KitPage(): ReactElement {
  const [collapsed, setCollapsed] = useState(false);
  const [active, setActive] = useState<NavItem["screen"]>("dashboard");
  return (
    <div className="flex h-screen overflow-hidden">
      <Sidebar
        active={active}
        items={SHIP_NAV}
        account={{ displayName: "Specialist de misiune 2", initials: "S2", roleLabel: "astronaut · cm-2" }}
        collapsed={collapsed}
        onToggle={() => setCollapsed((c) => !c)}
        onNavigate={(n) => setActive(n.screen)}
        onSwitchAccount={() => undefined}
      />
      <main className="min-w-0 flex-1">
        <Screen screen={active} live>
          <Header
            title="Catalogul componentelor"
            mission={{ clock: "Ziua 96 · 07:42", environment: "Tranzit spre Marte", delay: "11 min 40 s", linkOpen: true }}
            right={
              <Tip label="Legătura cu Pământul">
                <span className="inline-flex items-center gap-2 rounded-full border border-line-2 px-3 py-1 text-[12px] text-fg-3">
                  <Dot hue="var(--hue-a)" /> ecran: {active}
                </span>
              </Tip>
            }
          />
          <div className="scroll-q min-h-0 flex-1 overflow-y-auto">
            <motion.div {...rise} className="mx-auto grid max-w-[1180px] gap-5 px-6 pb-16 pt-6">
              <div>
                <p className="text-[12.5px] text-fg-4">Bună dimineața, Specialist de misiune 2.</p>
                <h2 className="mt-1 text-[34px] font-light tracking-[-0.02em] text-fg">Spui că ești bine. Datele spun altceva.</h2>
              </div>
              <StormBanner />
              <div className={cx("grid items-start gap-5 lg:grid-cols-[1.1fr_1fr]")}>
                <PerceptionGap />
                <PillarList />
              </div>
              <div className="grid items-start gap-5 lg:grid-cols-2">
                <Metrics />
                <Controls />
              </div>
              <div className="grid gap-5 lg:grid-cols-3">
                <Link />
                <AiCard />
                <EmptyState />
              </div>
              <ProblemCard title="Nu am putut salva check-in-ul." detail="Serverul nu răspunde. Datele tale sunt păstrate pe ecran." onRetry={() => undefined} />
            </motion.div>
          </div>
        </Screen>
      </main>
    </div>
  );
}
