"use client";
import type { ReactElement } from "react";
import { Page } from "@/components/layout/Shell";
import { LinkConsole } from "@/components/link/LinkConsole";
import { Notice } from "@/components/ui";
import { useSession } from "@/lib/session";

/**
 * Controlul misiunii: ce vede medicul de zbor de pe Pământ. Nimic în timp real despre echipaj, doar pachetele
 * care au ajuns prin coadă, după întârzierea legăturii.
 */
export default function MissionControlPage(): ReactElement | null {
  const { user } = useSession();
  if (!user) return null;
  return (
    <Page>
      <Notice title="Earth only sees what has arrived over the link">
        The data belongs to the astronaut. Packets sent from the ship appear here once they have made the trip and their signature has been verified.
      </Notice>
      <LinkConsole role={user.role} />
    </Page>
  );
}
