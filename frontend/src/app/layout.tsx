import type { Metadata } from "next";
import type { ReactElement, ReactNode } from "react";
import { TooltipProvider } from "@/components/ui";
import "./globals.css";

export const metadata: Metadata = {
  title: "SHADOW",
  description: "Monitorizarea sănătății astronauților — NASA Space Apps 2026. Prototip de sprijin, nu dispozitiv medical.",
};

export default function RootLayout({ children }: { readonly children: ReactNode }): ReactElement {
  return (
    <html lang="ro">
      <body>
        <TooltipProvider>{children}</TooltipProvider>
      </body>
    </html>
  );
}
