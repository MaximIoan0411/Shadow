"use client";
import type { ReactElement } from "react";
import { Evidence } from "@/components/evidence/Evidence";
import { Page } from "@/components/layout/Shell";
import { useSession } from "@/lib/session";

export default function EvidencePage(): ReactElement | null {
  const { user } = useSession();
  if (!user) return null;
  return (
    <Page>
      <Evidence role={user.role} />
    </Page>
  );
}
