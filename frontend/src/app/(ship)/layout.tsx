import type { ReactElement, ReactNode } from "react";
import { AppShell } from "@/components/layout/AppShell";

export default function ShipLayout({ children }: { readonly children: ReactNode }): ReactElement {
  return <AppShell area="ship">{children}</AppShell>;
}
