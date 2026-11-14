"use client";
/**
 * Rezumatul trimis de astronaut pe Pământ. Pleacă doar ce aprobă el: Pământul nu vede nimic în timp real,
 * ci numai pachetele puse în coadă de la bord (`POST /link/outbox`).
 */
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { useState, type ReactElement } from "react";
import { Button, Card, Field, Notice, ProblemCard, SectionTitle, Textarea } from "@/components/ui";
import { errorMessage } from "@/lib/api";
import { sendToEarth } from "@/lib/endpoints";
import { formatDuration } from "@/lib/format";
import { keys, useMission } from "@/lib/queries";

const BODY_MAX = 2000;
const FIELD_ID = "summary-body";

export function SummaryOutbox({ crewId }: { readonly crewId: string }): ReactElement {
  const queryClient = useQueryClient();
  const mission = useMission();
  const [body, setBody] = useState("");
  const send = useMutation({
    mutationFn: () => sendToEarth({ kind: "weekly_summary", crew_id: crewId, alert_id: null, body: body.trim() || null }),
    onSuccess: () => {
      setBody("");
      void queryClient.invalidateQueries({ queryKey: keys.link });
    },
  });
  const delay = formatDuration(mission.data?.link.one_way_delay_s);

  return (
    <Card as="section" aria-labelledby="summary-title">
      <SectionTitle id="summary-title">Your summary for Earth</SectionTitle>
      <form
        className="flex flex-col gap-3"
        onSubmit={(event) => {
          event.preventDefault();
          send.mutate();
        }}
      >
        <Field id={FIELD_ID} label="Anything to add (optional)" hint={`It leaves signed and encrypted; arrives after ${delay}.`}>
          <Textarea id={FIELD_ID} maxLength={BODY_MAX} value={body} onChange={(event) => setBody(event.target.value)} aria-describedby={`${FIELD_ID}-hint`} className="min-h-20" />
        </Field>
        {send.isError && <ProblemCard title="The summary did not leave" detail={errorMessage(send.error)} />}
        {send.isSuccess && (
          <Notice tone="ok" title={`The summary is in the queue (${send.data.id})`}>
            The flight surgeon sees it once it has made the trip to Earth.
          </Notice>
        )}
        <Button type="submit" className="self-start" busy={send.isPending}>
          Send the weekly summary
        </Button>
      </form>
    </Card>
  );
}
