"use client";
/**
 * Panoul de demo (Ctrl+Shift+D): butoanele cu care prezentatorul provoacă evenimentele din scenariu.
 * Tot ce face trece prin endpoint-urile `/sim/*` și `/demo/*`; efectele apar singure, prin evenimentele live.
 */
import { useMutation, useQueryClient } from "@tanstack/react-query";
import type { ReactElement, ReactNode } from "react";
import { Button, Segmented } from "@/components/ui";
import { Sheet } from "@/components/ui/overlays";
import { errorMessage, type Schemas } from "@/lib/api";
import * as api from "@/lib/endpoints";
import { keys } from "@/lib/queries";
import { useToast } from "@/lib/toast";

const TIME_SCALES = [
  { value: "1", label: "×1" },
  { value: "60", label: "×60" },
  { value: "600", label: "×600" },
  { value: "3600", label: "×3600" },
] as const;

type TimeScale = (typeof TIME_SCALES)[number]["value"];

function Row({ title, detail, children }: { readonly title: string; readonly detail: string; readonly children: ReactNode }): ReactElement {
  return (
    <div className="flex flex-wrap items-center gap-x-4 gap-y-3 border-b border-line py-4 last:border-b-0">
      <div className="min-w-[220px] flex-1">
        <p className="text-base font-medium text-fg">{title}</p>
        <p className="mt-0.5 text-small text-fg-3">{detail}</p>
      </div>
      <div className="flex flex-wrap gap-2">{children}</div>
    </div>
  );
}

export function DemoPanel({
  open,
  onClose,
  mission,
}: {
  readonly open: boolean;
  readonly onClose: () => void;
  readonly mission: Schemas["MissionState"] | undefined;
}): ReactElement {
  const queryClient = useQueryClient();
  const notify = useToast();
  const onError = (error: unknown): void => notify({ title: "The action failed", detail: errorMessage(error), status: "alert" });
  const onMission = (next: Schemas["MissionState"]): void => {
    queryClient.setQueryData(keys.mission, next);
    void queryClient.invalidateQueries({ queryKey: keys.link });
  };

  const stormStart = useMutation({
    mutationFn: api.startStorm,
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: keys.radiation });
      notify({ title: "The solar storm has started", detail: "The NASA DONKI event of 11 May 2024, replayed by the simulator." });
    },
    onError,
  });
  const stormStop = useMutation({
    mutationFn: api.stopStorm,
    onSuccess: () => void queryClient.invalidateQueries({ queryKey: keys.radiation }),
    onError,
  });
  const spoof = useMutation({
    mutationFn: api.injectSpoofedPacket,
    onSuccess: () => void queryClient.invalidateQueries({ queryKey: keys.link }),
    onError,
  });
  const frozen = useMutation({
    mutationFn: api.triggerFrozenSensor,
    onSuccess: () => void queryClient.invalidateQueries({ queryKey: keys.security }),
    onError,
  });
  const clock = useMutation({ mutationFn: api.setClock, onSuccess: onMission, onError });
  const reset = useMutation({
    mutationFn: api.resetSimulation,
    onSuccess: () => {
      void queryClient.invalidateQueries();
      notify({ title: "The simulation has been reset", detail: "The mission is back at day 96, 07:00." });
    },
    onError,
  });

  const scale = TIME_SCALES.find((option) => Number(option.value) === mission?.time_scale)?.value;

  return (
    <Sheet open={open} onClose={onClose} title="Demo panel" description="The buttons that trigger the scenario's events.">
      <p className="text-body text-fg-3">Each button calls the simulator in the backend. The effects appear on their own on the screens, as in a real mission.</p>
      <div className="mt-2">
        <Row title="Solar storm" detail="The dose rate climbs; after 3 readings above the threshold, the shelter alert appears.">
          <Button busy={stormStart.isPending} onClick={() => stormStart.mutate()}>
            Start
          </Button>
          <Button variant="ghost" busy={stormStop.isPending} onClick={() => stormStop.mutate()}>
            Stop
          </Button>
        </Row>
        <Row title="Spoofed packet" detail="A packet with a wrong signature enters the queue and is rejected on arrival.">
          <Button busy={spoof.isPending} onClick={() => spoof.mutate()}>
            Send
          </Button>
        </Row>
        <Row title="Frozen sensor" detail="A device keeps sending the same value; validation rejects it.">
          <Button busy={frozen.isPending} onClick={() => frozen.mutate()}>
            Trigger
          </Button>
        </Row>
        <Row title="Clock speed" detail="How many times faster mission time runs than real time.">
          <Segmented<TimeScale>
            size="sm"
            label="Clock speed"
            value={scale}
            options={TIME_SCALES}
            onChange={(value) => clock.mutate({ time_scale: Number(value) })}
          />
        </Row>
        <Row title="Skip a day" detail="The clock jumps to the start of the next day; the backend generates that day's data.">
          <Button busy={clock.isPending} disabled={!mission} onClick={() => mission && clock.mutate({ mission_day: mission.mission_day + 1 })}>
            {mission ? `Skip to day ${mission.mission_day + 1}` : "Skip"}
          </Button>
        </Row>
        <Row title="Reset" detail="Clears everything and puts the mission back at day 96, 07:00.">
          <Button busy={reset.isPending} onClick={() => reset.mutate()}>
            Reset the simulation
          </Button>
        </Row>
      </div>
    </Sheet>
  );
}
