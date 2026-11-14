import type { Metadata } from "next";
import type { ReactElement, ReactNode } from "react";
import { Providers } from "./providers";
import "./globals.css";

export const metadata: Metadata = {
  title: "SHADOW",
  description: "Astronaut health monitoring. NASA Space Apps 2026. A decision-support prototype, not a medical device.",
};

export default function RootLayout({ children }: { readonly children: ReactNode }): ReactElement {
  return (
    <html lang="en">
      <body>
        <Providers>{children}</Providers>
      </body>
    </html>
  );
}
