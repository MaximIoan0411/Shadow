"use client";
/** Pilonul Tastatura: ritmul tastării și testul de reacție, cele două măsurători făcute chiar de astronaut. */
import { useState, type ReactElement } from "react";
import { TypingCard } from "@/components/keystrokes/TypingCard";
import { Page } from "@/components/layout/Shell";
import { PvtTest } from "@/components/pvt/PvtTest";
import { Tabs } from "@/components/ui/overlays";
import { useMission } from "@/lib/queries";
import { useSession } from "@/lib/session";

type View = "typing" | "pvt";

export default function RhythmPage(): ReactElement | null {
  const { crewId } = useSession();
  const mission = useMission();
  const [view, setView] = useState<View>("typing");
  if (!crewId) return null;
  return (
    <Page>
      <Tabs<View>
        label="Measurements"
        value={view}
        onChange={setView}
        items={[
          { value: "typing", label: "Typing", content: <TypingCard crewId={crewId} /> },
          { value: "pvt", label: "Reaction test", content: <PvtTest crewId={crewId} missionNow={mission.data?.sim_now} /> },
        ]}
      />
    </Page>
  );
}
