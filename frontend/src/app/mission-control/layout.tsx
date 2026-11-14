import type { ReactElement, ReactNode } from "react";
import { AppShell } from "@/components/layout/AppShell";

export default function MissionControlLayout({ children }: { readonly children: ReactNode }): ReactElement {
  return <AppShell area="earth">{children}</AppShell>;
}
