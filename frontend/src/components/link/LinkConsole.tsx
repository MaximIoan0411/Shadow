"use client";
/**
 * Legătura navă ↔ Pământ: starea legăturii, pachetul care călătorește, coada de pachete și conținutul celui ales.
 * Folosită de ofițerul medical (la bord) și de medicul de zbor (pe Pământ, care poate și răspunde).
 *
 * Regula care face întârzierea vizibilă: conținutul unui pachet apare ABIA după sosire. Bara se animă local, pe
 * durata `eta_real_s`; lista se reîncarcă doar la evenimentele `packet.*`.
 */
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { useEffect, useState, type ReactElement } from "react";
import { Button, Card, EmptyState, Field, Notice, ProblemCard, SectionTitle, Skeleton, StatusBadge, Tag, Textarea, cx } from "@/components/ui";
import { errorMessage, type Schemas } from "@/lib/api";
import { replyFromEarth } from "@/lib/endpoints";
import { formatDateTime, formatDuration, formatNumber, formatPercent, formatTime, toPercent } from "@/lib/format";
import { keys, useLinkStatus, useMission, usePacket, usePackets } from "@/lib/queries";
import { useToast } from "@/lib/toast";

type Packet = Schemas["Packet"];
type PacketDetail = Schemas["PacketDetail"];
type Role = Schemas["Role"];

const KIND_LABEL = {
  alert_l3: "Level 3 alert",
  weekly_summary: "Weekly summary",
  earth_reply: "Reply from the Earth doctor",
  donki_alert: "Solar storm warning",
} as const satisfies Record<Packet["kind"], string>;

const DIRECTION_LABEL = { down: "ship → Earth", up: "Earth → ship" } as const satisfies Record<Packet["direction"], string>;

const REJECT_LABEL = {
  bad_signature: "invalid signature",
  implausible: "impossible value",
  frozen_sensor: "frozen sensor",
  replay: "replayed packet",
} as const satisfies Record<NonNullable<Packet["reject_reason"]>, string>;

const IN_TRANSIT = "in_transit";
const DELIVERED = "delivered";
const REJECTED = "rejected";
const EARTH: Role = "earth";
const REPLY_MAX = 2000;
const FULL = 100;

const isRecord = (value: unknown): value is Record<string, unknown> => typeof value === "object" && value !== null;
const textOf = (value: unknown): string | null => (typeof value === "string" && value ? value : null);

/** Starea unui pachet, cu cuvintele din contract: în coadă, pe drum, sosit, respins. */
function PacketState({ packet }: { readonly packet: Packet }): ReactElement {
  if (packet.status === DELIVERED) return <StatusBadge status="ok" label="Arrived" compact />;
  if (packet.status === REJECTED) return <StatusBadge status="alert" label={`Rejected: ${packet.reject_reason ? REJECT_LABEL[packet.reject_reason] : "invalid signature"}`} compact />;
  return <Tag>{packet.status === IN_TRANSIT ? "In transit" : "Queued"}</Tag>;
}

/**
 * Drumul pachetului, din puncte: cele aprinse arată cât a parcurs. Pornește de la `progress` și ajunge la capăt
 * în `eta_real_s` secunde reale, fără alte cereri către server.
 */
export function PacketTrack({ packet }: { readonly packet: Packet }): ReactElement {
  const moving = packet.status === IN_TRANSIT;
  const [arrived, setArrived] = useState(false);
  useEffect(() => {
    setArrived(false);
    if (!moving) return undefined;
    const frame = requestAnimationFrame(() => setArrived(true));
    return () => cancelAnimationFrame(frame);
  }, [moving, packet.id, packet.progress]);

  const done = packet.status === DELIVERED || packet.status === REJECTED;
  const start = done ? FULL : toPercent(packet.progress, 0, 1);
  const width = moving && arrived ? FULL : start;
  const toShip = packet.direction === "up";

  return (
    <div className="flex items-center gap-3">
      <span className="w-16 shrink-0 text-small font-medium text-fg-2">Ship</span>
      <div
        role="progressbar"
        aria-label={`Path of packet ${packet.id}, ${DIRECTION_LABEL[packet.direction]}`}
        aria-valuemin={0}
        aria-valuemax={FULL}
        aria-valuenow={Math.round(start)}
        className="dot-track relative flex-1 text-fg-5"
      >
        <div
          className={cx("dot-track absolute inset-y-0", toShip ? "right-0" : "left-0", packet.status === REJECTED ? "text-alert" : "text-solid")}
          style={{
            width: `${width}%`,
            transitionProperty: "width",
            transitionTimingFunction: "linear",
            transitionDuration: moving && arrived ? `${packet.eta_real_s ?? 0}s` : "0s",
            backgroundPositionX: toShip ? "right" : "left",
          }}
        />
      </div>
      <span className="w-16 shrink-0 text-right text-small font-medium text-fg-2">Earth</span>
    </div>
  );
}

function LinkSummary({ activePacket }: { readonly activePacket: Packet | undefined }): ReactElement {
  const link = useLinkStatus();
  const mission = useMission();
  return (
    <Card as="section" aria-labelledby="link-title">
      <SectionTitle
        id="link-title"
        right={
          link.data && (
            <span className="flex flex-wrap justify-end gap-2">
              {mission.data && <Tag>{mission.data.environment.name}</Tag>}
              <Tag>{link.data.window_open ? "window open" : "window closed"}</Tag>
            </span>
          )
        }
      >
        The link between ship and Earth
      </SectionTitle>
      {link.isError && <ProblemCard title="The link status could not be loaded" detail={errorMessage(link.error)} onRetry={() => void link.refetch()} />}
      {link.data && (
        <>
          <div className="flex flex-wrap items-end gap-x-8 gap-y-4">
            <p className="flex items-baseline gap-3">
              <span className="text-hero font-medium tracking-[-0.03em] text-fg">{formatDuration(link.data.one_way_delay_s)}</span>
              <span className="text-body leading-snug text-fg-3">
                one way
                <br />
                ({formatNumber(link.data.one_way_delay_real_s)} s in the demo, clock ×{formatNumber(mission.data?.time_scale, 0)})
              </span>
            </p>
            <dl className="flex gap-6 text-small text-fg-3">
              <div>
                <dt>Queued for Earth</dt>
                <dd className="num text-title font-medium text-fg">{link.data.queued_down}</dd>
              </div>
              <div>
                <dt>Queued for the ship</dt>
                <dd className="num text-title font-medium text-fg">{link.data.queued_up}</dd>
              </div>
              <div>
                <dt>{link.data.window_open ? "Window closes" : "Window opens"}</dt>
                <dd className="num text-title font-medium text-fg">{formatTime(link.data.window_open ? link.data.window_closes_at : link.data.next_window_at)}</dd>
              </div>
            </dl>
          </div>
          <div className="mt-6 rounded-2xl border border-line bg-white/[0.02] p-4">
            {activePacket ? (
              <>
                <p className="mb-3 flex flex-wrap items-center justify-between gap-2 text-body">
                  <span className="shimmer-text font-medium">{`${KIND_LABEL[activePacket.kind]} in transit, ${DIRECTION_LABEL[activePacket.direction]}`}</span>
                  <span className="num text-small text-fg-3">arrives at {formatTime(activePacket.arrives_at)}</span>
                </p>
                <PacketTrack packet={activePacket} />
              </>
            ) : (
              <p className="text-body text-fg-3">No packet in transit right now.</p>
            )}
          </div>
        </>
      )}
    </Card>
  );
}

/** Conținutul decriptat, citit defensiv: forma lui depinde de `kind` și nu e descrisă în tipurile generate. */
function Payload({ detail }: { readonly detail: PacketDetail }): ReactElement {
  const payload = detail.payload;
  if (!payload) {
    return (
      <Notice title={detail.status === REJECTED ? "The packet was rejected: its content is not opened" : "The content appears only after arrival"}>
        {detail.status === REJECTED
          ? "The signature did not verify, so the packet was not decrypted."
          : "Until it arrives, Earth only sees the envelope. That is what the link delay looks like."}
      </Notice>
    );
  }
  const alert = isRecord(payload.alert) ? payload.alert : null;
  const event = isRecord(payload.event) ? payload.event : null;
  const body = textOf(payload.body) ?? textOf(payload.summary) ?? textOf(payload.note);
  const evidence = Array.isArray(alert?.evidence) ? alert.evidence.filter(isRecord) : [];
  return (
    <div className="flex flex-col gap-3">
      {alert && (
        <div>
          <p className="text-base font-medium text-fg">{textOf(alert.title)}</p>
          <p className="mt-1 text-body leading-relaxed text-fg-2">{textOf(alert.explanation)}</p>
          {Boolean(evidence.length) && (
            <ul className="mt-2 flex flex-col gap-1 text-body text-fg-3">
              {evidence.map((item) => (
                <li key={textOf(item.metric_key) ?? textOf(item.label)}>
                  {textOf(item.label)}: <span className="text-fg-2">{textOf(item.deviation_text)}</span>
                </li>
              ))}
            </ul>
          )}
        </div>
      )}
      {event && (
        <p className="text-body text-fg-2">
          {textOf(event.note)} ({textOf(event.flare_class)}, {textOf(event.instrument)})
        </p>
      )}
      {body && <p className="whitespace-pre-line text-base leading-relaxed text-fg">{body}</p>}
      {!alert && !event && !body && <p className="text-body text-fg-3">The packet has no content to show.</p>}
    </div>
  );
}

function ReplyForm({ packet, delay }: { readonly packet: PacketDetail; readonly delay: string }): ReactElement | null {
  const queryClient = useQueryClient();
  const notify = useToast();
  const [body, setBody] = useState("");
  const reply = useMutation({
    mutationFn: () => replyFromEarth({ in_reply_to: packet.id, crew_id: packet.crew_id ?? "", alert_id: packet.alert_id ?? null, body: body.trim() }),
    onSuccess: () => {
      setBody("");
      void queryClient.invalidateQueries({ queryKey: keys.link });
      notify({ title: "The reply is in the queue", detail: `It reaches the ship after ${delay}.` });
    },
  });
  if (!packet.crew_id) return null;
  return (
    <form
      className="mt-5 flex flex-col gap-3 border-t border-line pt-5"
      onSubmit={(event) => {
        event.preventDefault();
        if (body.trim()) reply.mutate();
      }}
    >
      <Field id="earth-reply" label="Your reply to the crew" hint={`The reply reaches the ship after ${delay}.`}>
        <Textarea id="earth-reply" maxLength={REPLY_MAX} value={body} onChange={(event) => setBody(event.target.value)} aria-describedby="earth-reply-hint" />
      </Field>
      {reply.isError && <ProblemCard title="The reply did not leave" detail={errorMessage(reply.error)} />}
      <Button type="submit" variant="primary" className="self-start" busy={reply.isPending} disabled={!body.trim()}>
        Send reply
      </Button>
    </form>
  );
}

function PacketPanel({ packetId, role, delay }: { readonly packetId: string; readonly role: Role; readonly delay: string }): ReactElement {
  const packet = usePacket(packetId);
  const detail = packet.data;
  return (
    <Card as="section" aria-labelledby="packet-title">
      <SectionTitle id="packet-title" right={detail && <PacketState packet={detail} />}>
        Packet {packetId}
      </SectionTitle>
      {packet.isPending && <Skeleton className="h-40 rounded-2xl" />}
      {packet.isError && <ProblemCard title="The packet could not be loaded" detail={errorMessage(packet.error)} onRetry={() => void packet.refetch()} />}
      {detail && (
        <>
          <p className="text-base font-medium text-fg">{detail.title}</p>
          <p className="mt-1 text-small text-fg-3">
            {KIND_LABEL[detail.kind]}, {DIRECTION_LABEL[detail.direction]}, from {detail.sender}
          </p>
          <div className="mt-4">
            <PacketTrack packet={detail} />
          </div>
          <dl className="mt-4 grid grid-cols-2 gap-x-6 gap-y-1.5 text-small sm:grid-cols-4">
            <div>
              <dt className="text-fg-4">Sent</dt>
              <dd className="num text-fg-2">{formatDateTime(detail.sent_at)}</dd>
            </div>
            <div>
              <dt className="text-fg-4">{detail.delivered_at ? "Arrived" : "Arrives"}</dt>
              <dd className="num text-fg-2">{formatDateTime(detail.delivered_at ?? detail.arrives_at)}</dd>
            </div>
            <div>
              <dt className="text-fg-4">Sequence number</dt>
              <dd className="num text-fg-2">{detail.seq}</dd>
            </div>
            <div>
              <dt className="text-fg-4">Size</dt>
              <dd className="num text-fg-2">{detail.size_bytes} B</dd>
            </div>
          </dl>
          <p className="mt-3 flex flex-wrap items-center gap-2 text-small text-fg-3">
            <Tag>{detail.crypto.cipher}</Tag>
            <Tag>{detail.crypto.signature_alg}</Tag>
            <span>
              key <span className="code text-fg-2">{detail.crypto.key_id}</span>
            </span>
          </p>
          <div className="mt-5 border-t border-line pt-5">
            <Payload detail={detail} />
          </div>
          {role === EARTH && detail.status === DELIVERED && detail.direction === "down" && <ReplyForm packet={detail} delay={delay} />}
        </>
      )}
    </Card>
  );
}

function signatureText(packet: Packet): string {
  if (packet.signature_valid === null || packet.signature_valid === undefined) return "checked on arrival";
  return packet.signature_valid ? "valid" : "invalid";
}

export function LinkConsole({ role }: { readonly role: Role }): ReactElement {
  const packets = usePackets(true);
  const link = useLinkStatus();
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const list = packets.data ?? [];
  const active = list.find((packet) => packet.status === IN_TRANSIT);
  const chosenId = selectedId ?? active?.id ?? list[0]?.id ?? null;
  const delay = formatDuration(link.data?.one_way_delay_s);

  return (
    <div className="flex flex-col gap-5">
      <LinkSummary activePacket={active} />
      <div className="grid items-start gap-5 xl:grid-cols-[minmax(0,1fr)_minmax(0,1fr)]">
        <Card as="section" aria-labelledby="queue-title">
          <SectionTitle id="queue-title">Packet queue</SectionTitle>
          {packets.isPending && <Skeleton className="h-40 rounded-2xl" />}
          {packets.isError && <ProblemCard title="The queue could not be loaded" detail={errorMessage(packets.error)} onRetry={() => void packets.refetch()} />}
          {packets.isSuccess && !list.length && <EmptyState title="The queue is empty">Packets appear here when an alert reaches level 3 or an astronaut sends a summary.</EmptyState>}
          <ul className="flex flex-col gap-2">
            {list.map((packet) => (
              <li key={packet.id}>
                <button
                  type="button"
                  onClick={() => setSelectedId(packet.id)}
                  aria-pressed={packet.id === chosenId}
                  className={cx(
                    "w-full rounded-2xl border p-3.5 text-left transition-colors",
                    packet.id === chosenId ? "border-line-4 bg-white/[0.07]" : "border-line-2 bg-white/[0.02] hover:border-line-3 hover:bg-white/[0.05]",
                  )}
                >
                  <span className="flex items-center justify-between gap-2">
                    <span className="text-small text-fg-3">
                      {DIRECTION_LABEL[packet.direction]}, from {packet.sender}
                    </span>
                    <PacketState packet={packet} />
                  </span>
                  <span className="mt-1.5 block text-base font-medium leading-snug text-fg">{packet.title}</span>
                  <span className="mt-2 flex flex-wrap items-center gap-x-3 gap-y-1 text-caption text-fg-4">
                    <span className="code">{packet.id}</span>
                    <span>signature: {signatureText(packet)}</span>
                    {packet.status === IN_TRANSIT && <span className="num">travelled {formatPercent(packet.progress)}</span>}
                    <span className="num">{formatDateTime(packet.created_at)}</span>
                  </span>
                </button>
              </li>
            ))}
          </ul>
        </Card>
        {chosenId && <PacketPanel key={chosenId} packetId={chosenId} role={role} delay={delay} />}
      </div>
    </div>
  );
}
