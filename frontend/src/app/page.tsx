"use client";
import { useRouter } from "next/navigation";
import { useEffect } from "react";
import { HOME_BY_ROLE, LOGIN_PATH, useSession } from "@/lib/session";

/** Rădăcina doar trimite mai departe: la ecranul rolului, sau la autentificare dacă nu e nimeni conectat. */
export default function Home(): null {
  const { user } = useSession();
  const router = useRouter();
  useEffect(() => {
    router.replace(user ? HOME_BY_ROLE[user.role] : LOGIN_PATH);
  }, [user, router]);
  return null;
}
