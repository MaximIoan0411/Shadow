"use client";
/**
 * Dovezile: de unde vine orice cifră din aplicație și cine a atins datele. Testele automate ale motorului,
 * pragurile cu sursa fiecăruia, catalogul de recomandări, jurnalul de acces și valorile respinse.
 */
import { useState, type ReactElement, type ReactNode } from "react";
import { SourceLine } from "@/components/body/ZonePanel";
import { Card, EmptyState, Input, LevelTag, ProblemCard, Skeleton, StatusBadge, Switch, Tag } from "@/components/ui";
import { Tabs, type TabItem } from "@/components/ui/overlays";
import { errorMessage, type ApiError, type Schemas } from "@/lib/api";
import { formatDateTime, formatNumber } from "@/lib/format";
import { useAccessLog, useCatalog, useParameters, useRejections, useTestReport } from "@/lib/queries";
import { ROLE_LABEL, TOPIC_META } from "@/lib/status";

type Role = Schemas["Role"];
type View = "tests" | "parameters" | "catalog" | "access" | "rejections";

const SHIP_ROLES: readonly Role[] = ["astronaut", "cmo"];
const TWO_DECIMALS = 2;
const SEARCH_FIELD_ID = "parameter-search";

const ACTION_LABEL: Readonly<Record<string, string>> = {
  login: "Sign-in",
  login_failed: "Wrong password",
  logout: "Sign-out",
  read_dashboard: "Read the dashboard",
  read_pillar: "Read a zone panel",
  read_alert: "Read an alert",
  read_packet: "Read a packet",
  escalate: "Escalated an alert",
  access_denied: "Access denied",
};

const REJECTION_LABEL = {
  bad_signature: "Invalid signature",
  implausible: "Impossible value",
  frozen_sensor: "Frozen sensor",
  replay: "Replayed packet",
} as const satisfies Record<Schemas["RejectionKind"], string>;

/** Starea unei liste încărcate: schelet, eroare cu „încearcă din nou”, sau conținutul. */
function Loaded<TData>({ query, title, children }: {
  readonly query: { readonly data: TData | undefined; readonly isPending: boolean; readonly error: ApiError | null; readonly refetch: () => unknown };
  readonly title: string;
  readonly children: (data: TData) => ReactNode;
}): ReactElement {
  if (query.error) return <ProblemCard title={title} detail={errorMessage(query.error)} onRetry={() => void query.refetch()} />;
  if (query.isPending || query.data === undefined) return <Skeleton className="h-48 rounded-2xl" />;
  return <>{children(query.data)}</>;
}

function Tests(): ReactElement {
  const report = useTestReport();
  return (
    <Loaded query={report} title="The test report could not be loaded">
      {(data) => (
        <Card>
          <p className="mb-4 flex flex-wrap items-center gap-x-4 gap-y-2 text-body text-fg-3">
            <StatusBadge status={data.failed ? "alert" : "ok"} label={data.failed ? `${data.failed} tests failed` : "All tests pass"} />
            <span>
              <span className="num text-fg">{data.passed}</span> passed, <span className="num text-fg">{data.failed}</span> failed, <span className="num text-fg">{data.skipped}</span> skipped
            </span>
            <span>
              run {formatDateTime(data.ran_at)}, in <span className="num">{formatNumber(data.duration_s, TWO_DECIMALS)} s</span>
            </span>
          </p>
          <table className="w-full text-small">
            <thead>
              <tr className="text-left text-caption text-fg-4">
                <th scope="col" className="pb-2 font-medium">Test</th>
                <th scope="col" className="pb-2 font-medium">File</th>
                <th scope="col" className="pb-2 text-right font-medium">Duration</th>
                <th scope="col" className="pb-2 text-right font-medium">Result</th>
              </tr>
            </thead>
            <tbody>
              {data.tests.map((test) => (
                <tr key={test.module + test.name} className="border-t border-line">
                  <td className="code py-2.5 text-fg">{test.name}</td>
                  <td className="code py-2.5 text-fg-3">{test.module}</td>
                  <td className="num py-2.5 text-right text-fg-3">{formatNumber(test.duration_ms)} ms</td>
                  <td className="py-2.5 text-right">
                    {test.outcome === "skipped" ? <Tag>skipped</Tag> : <StatusBadge status={test.outcome === "passed" ? "ok" : "alert"} label={test.outcome === "passed" ? "Passed" : "Failed"} compact />}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </Card>
      )}
    </Loaded>
  );
}

/** Valoarea unui prag e de orice tip în `parameters.json`: număr, text, listă sau obiect. */
function valueText(value: unknown): string {
  if (typeof value === "number") return formatNumber(value, TWO_DECIMALS);
  return typeof value === "string" ? value : JSON.stringify(value);
}

function Parameters(): ReactElement {
  const parameters = useParameters();
  const [search, setSearch] = useState("");
  const [keyOnly, setKeyOnly] = useState(true);
  const needle = search.trim().toLowerCase();

  return (
    <Loaded query={parameters} title="The thresholds could not be loaded">
      {(data) => {
        const shown = data.filter((parameter) => (!keyOnly || parameter.is_key_threshold) && (!needle || `${parameter.name} ${parameter.id} ${parameter.topic}`.toLowerCase().includes(needle)));
        return (
          <Card>
            <div className="mb-4 flex flex-wrap items-center gap-4">
              <label htmlFor={SEARCH_FIELD_ID} className="sr-only">
                Search for a threshold
              </label>
              <Input id={SEARCH_FIELD_ID} value={search} onChange={(event) => setSearch(event.target.value)} placeholder="Search by name or topic" className="max-w-[320px]" />
              <span className="flex items-center gap-2.5 text-body text-fg-2">
                <Switch checked={keyOnly} onChange={setKeyOnly} label="Only thresholds used directly by triage" />
                Only thresholds used directly by triage
              </span>
              <span className="num ml-auto text-small text-fg-4">
                {shown.length} of {data.length}
              </span>
            </div>
            {!shown.length && <EmptyState title="No threshold matches">Change the search or turn off the filter.</EmptyState>}
            <ul className="flex flex-col">
              {shown.map((parameter) => (
                <li key={parameter.id} className="border-t border-line py-4 first:border-t-0 first:pt-0">
                  <div className="flex flex-wrap items-baseline justify-between gap-x-4 gap-y-1">
                    <p className="text-base font-medium text-fg">{parameter.name}</p>
                    <p className="num text-base text-fg">
                      {valueText(parameter.value)} <span className="text-small text-fg-4">{parameter.unit}</span>
                    </p>
                  </div>
                  <p className="mt-1.5 max-w-[86ch] text-body leading-relaxed text-fg-3">{parameter.explanation}</p>
                  <ul className="mt-2 flex flex-wrap items-center gap-x-3 gap-y-1.5">
                    <li>
                      <Tag>{parameter.topic}</Tag>
                    </li>
                    {parameter.is_key_threshold && (
                      <li>
                        <Tag>used by triage</Tag>
                      </li>
                    )}
                    <SourceLine source={parameter.source} />
                  </ul>
                </li>
              ))}
            </ul>
          </Card>
        );
      }}
    </Loaded>
  );
}

function Catalog(): ReactElement {
  const catalog = useCatalog(true);
  return (
    <Loaded query={catalog} title="The catalog could not be loaded">
      {(data) => (
        <Card>
          <p className="mb-4 max-w-[80ch] text-body leading-relaxed text-fg-3">
            The recommendations are written by the team from NASA documents. The AI doctor only rephrases them; it does not invent advice.
          </p>
          <ul className="flex flex-col">
            {data.map((recommendation) => {
              const topic = TOPIC_META[recommendation.topic];
              return (
                <li key={recommendation.id} className="border-t border-line py-4 first:border-t-0 first:pt-0">
                  <p className="flex flex-wrap items-center gap-2 text-small text-fg-3">
                    <topic.icon size={14} strokeWidth={1.8} />
                    {topic.label}
                    <LevelTag level={recommendation.level} />
                    <span className="code text-fg-4">{recommendation.id}</span>
                  </p>
                  <p className="mt-1.5 max-w-[86ch] text-base leading-relaxed text-fg">{recommendation.action}</p>
                  <p className="mt-1 max-w-[86ch] text-small leading-relaxed text-fg-3">When: {recommendation.trigger}</p>
                  <ul className="mt-2">
                    <SourceLine source={recommendation.source} />
                  </ul>
                </li>
              );
            })}
          </ul>
        </Card>
      )}
    </Loaded>
  );
}

function AccessLog(): ReactElement {
  const log = useAccessLog(true);
  return (
    <Loaded query={log} title="The access log could not be loaded">
      {(data) => (
        <Card>
          <p className="mb-4 max-w-[80ch] text-body leading-relaxed text-fg-3">
            Who read your data and which attempts were refused. The log only grows: every row carries the fingerprint of the one before it, so it cannot be rewritten in secret.
          </p>
          {!data.length && <EmptyState title="Nobody has read your data" />}
          <ul className="flex flex-col">
            {data.map((entry) => (
              <li key={entry.id} className="flex flex-wrap items-baseline gap-x-3 gap-y-1 border-t border-line py-3 first:border-t-0 first:pt-0">
                <span className="num w-28 shrink-0 text-small text-fg-4">{formatDateTime(entry.at)}</span>
                <span className="text-body text-fg">
                  {entry.actor} <span className="text-fg-4">({ROLE_LABEL[entry.actor_role]})</span>
                </span>
                <span className="text-body text-fg-2">{ACTION_LABEL[entry.action] ?? entry.action}</span>
                <span className="code text-small text-fg-3">{entry.resource}</span>
                <span className="ml-auto">{entry.outcome === "denied" ? <StatusBadge status="alert" label="Refused" compact /> : <Tag>allowed</Tag>}</span>
                <span className="code w-full pl-[124px] text-caption text-fg-4">
                  fingerprint {entry.prev_hash} → {entry.hash}
                </span>
              </li>
            ))}
          </ul>
        </Card>
      )}
    </Loaded>
  );
}

function Rejections(): ReactElement {
  const rejections = useRejections(true);
  return (
    <Loaded query={rejections} title="The rejections could not be loaded">
      {(data) => (
        <Card>
          <p className="mb-4 max-w-[80ch] text-body leading-relaxed text-fg-3">
            Values and packets stopped at the door: wrong signature, impossible value, a sensor repeating the same reading, a replayed packet.
          </p>
          {!data.length && <EmptyState title="Nothing rejected" />}
          <ul className="flex flex-col">
            {data.map((rejection) => (
              <li key={rejection.id} className="flex flex-wrap items-baseline gap-x-3 gap-y-1 border-t border-line py-3 first:border-t-0 first:pt-0">
                <span className="num w-28 shrink-0 text-small text-fg-4">{formatDateTime(rejection.at)}</span>
                <StatusBadge status="alert" label={REJECTION_LABEL[rejection.kind]} compact />
                <span className="code text-small text-fg-3">{rejection.source}</span>
                <span className="w-full pl-[124px] text-body text-fg">{rejection.message}</span>
              </li>
            ))}
          </ul>
        </Card>
      )}
    </Loaded>
  );
}

export function Evidence({ role }: { readonly role: Role }): ReactElement {
  const [view, setView] = useState<View>("parameters");
  const onShip = SHIP_ROLES.includes(role);
  const shipOnly: readonly TabItem<View>[] = [
    { value: "access", label: "Access log", content: <AccessLog /> },
    { value: "rejections", label: "Rejections", content: <Rejections /> },
  ];
  const items: readonly TabItem<View>[] = [
    { value: "parameters", label: "Thresholds and sources", content: <Parameters /> },
    { value: "tests", label: "Automated tests", content: <Tests /> },
    { value: "catalog", label: "Recommendation catalog", content: <Catalog /> },
    ...(onShip ? shipOnly : []),
  ];
  return <Tabs<View> label="Evidence" value={view} onChange={setView} items={items} />;
}
