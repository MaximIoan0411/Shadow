"use client";
import type { ReactElement } from "react";
import { AiChat } from "@/components/ai/AiChat";
import { useSession } from "@/lib/session";

/** Medicul AI, pentru întrebări care nu țin de o alertă anume: conversația ocupă tot ecranul, caseta stă jos. */
export default function AiPage(): ReactElement | null {
  const { crewId } = useSession();
  if (!crewId) return null;
  return <AiChat crewId={crewId} />;
}
