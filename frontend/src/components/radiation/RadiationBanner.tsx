"use client";
/**
 * Banner-ul furtunii solare: apare pe orice ecran de la bord cât timp alerta de radiații e activă.
 * E singurul loc unde SHADOW cere o acțiune imediată, de aceea ocupă toată lățimea.
 */
import { useMutation, useQueryClient } from "@tanstack/react-query";
import Link from "next/link";
import type { ReactElement } from "react";
import { Button, StatusMark } from "@/components/ui";
import { errorMessage, type Schemas } from "@/lib/api";
import { ackShelter } from "@/lib/endpoints";
import { formatNumber, formatTime } from "@/lib/format";
import { keys } from "@/lib/queries";
import { useToast } from "@/lib/toast";

export function RadiationBanner({ status }: { readonly status: Schemas["RadiationStatus"] }): ReactElement | null {
  const queryClient = useQueryClient();
  const notify = useToast();
  const shelter = useMutation({
    mutationFn: ackShelter,
    onSuccess: (next) => queryClient.setQueryData(keys.radiationStatus, next),
    onError: (error) => notify({ title: "Could not save", detail: errorMessage(error), status: "alert" }),
  });

  if (!status.alert_active) return null;

  return (
    <section aria-label="Radiation alert" role="alert" className="mx-6 mb-1 flex flex-wrap items-center gap-x-5 gap-y-3 rounded-2xl border border-alert/40 bg-alert/[0.09] px-5 py-4">
      <StatusMark status="alert" className="text-title" />
      <div className="min-w-0 flex-1">
        <p className="text-title font-medium text-fg">{status.sheltered ? "You are in the shelter" : "Solar storm: go to the shelter"}</p>
        <p className="mt-0.5 text-body text-fg-2">
          The dosimeter reads <span className="num text-fg">{formatNumber(status.dose_rate_usv_h)} µSv/h</span>,{" "}
          <span className="num text-fg">{formatNumber(status.ratio)}</span> times the mean of the last 24 hours.
          {status.sheltered && status.sheltered_since ? ` Sheltered since ${formatTime(status.sheltered_since)}.` : ""}
        </p>
      </div>
      <Link href="/radiation" className="text-body">
        See the dose curve
      </Link>
      <Button variant={status.sheltered ? "secondary" : "primary"} size="lg" busy={shelter.isPending} onClick={() => shelter.mutate(!status.sheltered)}>
        {status.sheltered ? "I have left the shelter" : "I am in the shelter"}
      </Button>
    </section>
  );
}
