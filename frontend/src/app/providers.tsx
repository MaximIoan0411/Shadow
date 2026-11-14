"use client";
import { QueryClientProvider } from "@tanstack/react-query";
import { useEffect, useState, type ReactElement, type ReactNode } from "react";
import { TooltipProvider } from "@/components/ui";
import { createQueryClient } from "@/lib/queries";
import { SessionProvider } from "@/lib/session";
import { ToastProvider } from "@/lib/toast";

/** Tot ce trebuie să existe o singură dată pe fereastră: datele, sesiunea, notificările, tooltip-urile. */
export function Providers({ children }: { readonly children: ReactNode }): ReactElement {
  const [queryClient] = useState(createQueryClient);

  // În aplicația de desktop, CSS-ul trebuie să știe platforma (unde stau butoanele ferestrei).
  useEffect(() => {
    const platform = window.shadowDesktop?.platform;
    if (platform) document.documentElement.dataset.desktop = platform;
  }, []);
  return (
    <QueryClientProvider client={queryClient}>
      <TooltipProvider>
        <ToastProvider>
          <SessionProvider>{children}</SessionProvider>
        </ToastProvider>
      </TooltipProvider>
    </QueryClientProvider>
  );
}
