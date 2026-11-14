"use client";
/**
 * „Cine ești?” — fiecare membru al echipajului are contul lui. Ecranul are două jumătăți: în stânga gaura neagră
 * (doar imagine), în dreapta intrarea, în doi pași: alegi contul din listă, apoi scrii parola lui.
 * Conturile de la bord și cel de pe Pământ sunt separate după stația de lucru.
 */
import { ArrowLeft, ChevronRight } from "lucide-react";
import { useRouter } from "next/navigation";
import { useEffect, useState, type FormEvent, type ReactElement } from "react";
import { BlackHole } from "@/components/login/BlackHole";
import { RoleIcon, hasRoleIcon } from "@/components/login/RoleIcon";
import { Button, Field, Input, Notice, Segmented, Skeleton, cx } from "@/components/ui";
import { ApiError, ERROR_CODE, errorMessage, type Schemas } from "@/lib/api";
import { getBackendStatus, type BackendStatus } from "@/lib/desktop";
import { formatDuration } from "@/lib/format";
import { useAccounts } from "@/lib/queries";
import { HOME_BY_ROLE, useSession } from "@/lib/session";
import { ROLE_LABEL } from "@/lib/status";

type Account = Schemas["LoginAccount"];
type Location = Account["location"];

const LOCATIONS = [
  { value: "ship", label: "On board" },
  { value: "earth", label: "On Earth" },
] as const satisfies readonly { readonly value: Location; readonly label: string }[];

const MS_PER_SECOND = 1000;
const PASSWORD_FIELD_ID = "login-password";
const SKELETON_ROWS = ["a", "b", "c", "d"] as const;
const RETRY_MS = 3000;
const BACKEND_COMMAND = "cd backend && uv run uvicorn app.main:app --port 8000";
const AVATAR_ICON_LARGE = 30;

const isRecord = (value: unknown): value is Record<string, unknown> => typeof value === "object" && value !== null;

/** Câte secunde cere serverul să aștepți după prea multe parole greșite (`details.retry_after_s`). */
function retryAfterSeconds(error: unknown): number | null {
  if (!(error instanceof ApiError) || error.code !== ERROR_CODE.tooManyAttempts || !isRecord(error.details)) return null;
  const seconds = error.details.retry_after_s;
  return typeof seconds === "number" ? seconds : null;
}

/** Numărătoarea inversă până când contul se deblochează; `0` = se poate încerca din nou. */
function useCountdown(): readonly [number, (seconds: number) => void] {
  const [until, setUntil] = useState(0);
  const [now, setNow] = useState(0);
  useEffect(() => {
    if (until <= now) return undefined;
    const timer = setTimeout(() => setNow(Date.now()), MS_PER_SECOND);
    return () => clearTimeout(timer);
  }, [until, now]);
  const start = (seconds: number): void => {
    setNow(Date.now());
    setUntil(Date.now() + seconds * MS_PER_SECOND);
  };
  return [Math.max(0, Math.ceil((until - now) / MS_PER_SECOND)), start] as const;
}

/** Cercul unui cont: icoana rolului, sau inițialele dacă rolul n-are icoană. */
function Avatar({ account, large }: { readonly account: Account; readonly large?: boolean }): ReactElement {
  const withIcon = hasRoleIcon(account.username);
  return (
    <span
      aria-hidden="true"
      className={cx(
        "grid shrink-0 place-items-center rounded-full border border-line-2 bg-surface-3 font-semibold",
        large ? "size-16 text-lead" : "size-11 text-body",
        withIcon ? "text-crew" : "text-fg",
      )}
    >
      {withIcon ? <RoleIcon username={account.username} size={large ? AVATAR_ICON_LARGE : undefined} /> : account.initials}
    </span>
  );
}

/** Un rând din lista conturilor: un clic duce la parola contului. */
function AccountRow({ account, onSelect }: { readonly account: Account; readonly onSelect: () => void }): ReactElement {
  return (
    <li>
      <button
        type="button"
        onClick={onSelect}
        className="group flex w-full items-center gap-4 rounded-2xl px-3 py-3 text-left transition-colors hover:bg-white/[0.05]"
      >
        <Avatar account={account} />
        <span className="min-w-0 flex-1">
          <span className="block truncate text-base font-medium text-fg">{account.display_name}</span>
          <span className="block truncate text-small text-fg-4">{ROLE_LABEL[account.role]}</span>
        </span>
        <ChevronRight size={17} strokeWidth={1.8} aria-hidden="true" className="shrink-0 text-fg-4 transition-transform duration-200 group-hover:translate-x-0.5 group-hover:text-fg-2" />
      </button>
    </li>
  );
}

/** Ce vede utilizatorul când backend-ul nu răspunde: ce s-a întâmplat și cum îl pornește. */
function BackendDown({ desktop, failure, retrying, onRetry }: {
  readonly desktop: BackendStatus | null;
  readonly failure: unknown;
  readonly retrying: boolean;
  readonly onRetry: () => void;
}): ReactElement {
  const starting = desktop?.state === "starting";
  // ce a răspuns de fapt serverul, ca problema să se poată găsi (ex. alt program ocupă portul 8000)
  const cause = failure instanceof ApiError ? `GET /api/v1/auth/accounts answered ${failure.status || "nothing"}${failure.code ? ` (${failure.code})` : ""}: ${failure.message}` : null;
  return (
    <Notice
      tone={starting ? "neutral" : "alert"}
      title={starting ? "Starting the SHADOW server…" : "The SHADOW server is not responding"}
      action={
        <Button size="sm" onClick={onRetry} busy={retrying}>
          Try again
        </Button>
      }
    >
      <p>{desktop?.detail ?? "The app needs the backend running on this computer."}</p>
      {cause && !starting && <p className="code mt-2 text-small text-fg-4">{cause}</p>}
      {!starting && (
        <p className="mt-2">
          Start it from the project folder: <code className="code rounded-md bg-white/[0.07] px-1.5 py-0.5 text-small text-fg">{BACKEND_COMMAND}</code>
        </p>
      )}
    </Notice>
  );
}

export default function LoginPage(): ReactElement {
  const { user, login } = useSession();
  const router = useRouter();
  const accounts = useAccounts();
  const [location, setLocation] = useState<Location>("ship");
  const [username, setUsername] = useState<string | null>(null);
  const [password, setPassword] = useState("");
  const [pending, setPending] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [desktop, setDesktop] = useState<BackendStatus | null>(null);
  const [waitSeconds, startWait] = useCountdown();

  useEffect(() => {
    if (user) router.replace(HOME_BY_ROLE[user.role]);
  }, [user, router]);

  // Ultima eroare rămâne pe ecran cât se reîncearcă: fără ea, mesajul ar clipi (la o nouă încercare, interogarea
  // fără date trece din nou prin „pending”).
  const [failure, setFailure] = useState<unknown>(null);
  useEffect(() => {
    if (accounts.error) setFailure(accounts.error);
    if (accounts.data) setFailure(null);
  }, [accounts.error, accounts.data]);

  const { refetch } = accounts;
  const down = Boolean(failure) && !accounts.data;
  useEffect(() => {
    if (!down) return undefined;
    const refresh = async (): Promise<void> => {
      const status = await getBackendStatus();
      setDesktop(status);
      // se reîncearcă singur doar cât aplicația pornește backend-ul; altfel, la „Try again”
      if (status?.state === "starting" || status?.state === "running") void refetch();
    };
    void refresh();
    const timer = setInterval(() => void refresh(), RETRY_MS);
    return () => clearInterval(timer);
  }, [down, refetch]);

  const visible = (accounts.data ?? []).filter((account) => account.location === location);
  const selected = (accounts.data ?? []).find((account) => account.username === username) ?? null;

  const choose = (next: string | null): void => {
    setUsername(next);
    setPassword("");
    setError(null);
  };

  const submit = async (event: FormEvent<HTMLFormElement>): Promise<void> => {
    event.preventDefault();
    if (!selected || !password || waitSeconds) return;
    setPending(true);
    setError(null);
    try {
      const signedIn = await login(selected.username, password);
      router.replace(HOME_BY_ROLE[signedIn.role]);
    } catch (caught) {
      const retryAfter = retryAfterSeconds(caught);
      if (retryAfter) startWait(retryAfter);
      setError(errorMessage(caught));
      setPassword("");
    } finally {
      setPending(false);
    }
  };

  return (
    <div className="relative flex min-h-full bg-bg">
      <div className="app-drag absolute inset-x-0 top-0 z-20 h-10" />

      {/* stânga: gaura neagră, ca imagine; pe ecrane înguste dispare */}
      <section aria-label="SHADOW" className="relative hidden min-w-0 flex-1 flex-col overflow-hidden bg-black lg:flex">
        <BlackHole className="absolute inset-0" />
        {/* un văl întunecat jos, ca textul să se citească peste stele */}
        <div aria-hidden="true" className="pointer-events-none absolute inset-x-0 bottom-0 h-1/3 bg-gradient-to-t from-black/70 to-transparent" />
        <div className="relative z-10 flex items-center gap-3 px-10 pt-12">
          {/* eslint-disable-next-line @next/next/no-img-element -- logo local; exportul static nu optimizează imagini */}
          <img src="/brand/mark-96.png" srcSet="/brand/mark-96.png 1x, /brand/mark-192.png 2x" alt="" width={55} height={32} className="h-8 w-auto" />
          {/* eslint-disable-next-line @next/next/no-img-element -- logo local */}
          <img src="/brand/wordmark-300.png" srcSet="/brand/wordmark-300.png 1x, /brand/wordmark-600.png 2x" alt="SHADOW" width={150} height={25} className="h-[22px] w-auto" />
        </div>
        <span className="flex-1" />
        <div className="relative z-10 max-w-[30rem] px-10 pb-10">
          <p className="text-display font-semibold leading-[1.15] tracking-[-0.02em] text-fg">Every astronaut, against their own baseline.</p>
          <p className="mt-3 text-lead leading-relaxed text-fg-2">How you say you feel, next to what your body shows in flight.</p>
        </div>
      </section>

      {/* dreapta: intrarea */}
      <main className="relative z-10 flex w-full flex-col border-line bg-surface lg:w-[480px] lg:shrink-0 lg:border-l">
        <div className="scroll-q flex flex-1 flex-col overflow-y-auto px-8 pb-8 pt-16 sm:px-12">
          {/* pe ecrane înguste logo-ul stă deasupra formularului */}
          <div className="mx-auto mb-10 flex w-full max-w-[400px] items-center gap-3 lg:hidden">
            {/* eslint-disable-next-line @next/next/no-img-element -- logo local */}
            <img src="/brand/mark-96.png" srcSet="/brand/mark-96.png 1x, /brand/mark-192.png 2x" alt="" width={55} height={32} className="h-8 w-auto" />
            {/* eslint-disable-next-line @next/next/no-img-element -- logo local */}
            <img src="/brand/wordmark-300.png" srcSet="/brand/wordmark-300.png 1x, /brand/wordmark-600.png 2x" alt="SHADOW" width={150} height={25} className="h-[22px] w-auto" />
          </div>

          <div className="mx-auto my-auto flex w-full max-w-[400px] flex-col">
            {selected ? (
              <form onSubmit={(event) => void submit(event)} className="flex flex-col">
                <button
                  type="button"
                  onClick={() => choose(null)}
                  className="-ml-2 mb-10 inline-flex w-fit items-center gap-2 rounded-full px-2 py-1 text-body text-fg-3 transition-colors hover:text-fg"
                >
                  <ArrowLeft size={15} strokeWidth={1.9} aria-hidden="true" />
                  All accounts
                </button>
                <Avatar account={selected} large />
                <h1 className="mt-5 text-title font-medium text-fg">{selected.display_name}</h1>
                <p className="mt-1 text-body text-fg-4">{ROLE_LABEL[selected.role]}</p>
                <div className="mt-8">
                  <Field id={PASSWORD_FIELD_ID} label="Password" error={error}>
                    <Input
                      id={PASSWORD_FIELD_ID}
                      type="password"
                      autoComplete="current-password"
                      autoFocus
                      value={password}
                      onChange={(event) => setPassword(event.target.value)}
                      aria-invalid={Boolean(error)}
                      aria-describedby={error ? `${PASSWORD_FIELD_ID}-error` : undefined}
                      disabled={Boolean(waitSeconds)}
                      className="h-11"
                    />
                  </Field>
                </div>
                <Button type="submit" variant="primary" size="lg" className="mt-4 h-11 w-full" busy={pending} disabled={!password || Boolean(waitSeconds)}>
                  Sign in
                </Button>
                {Boolean(waitSeconds) && <p className="mt-3 text-small text-fg-3">You can try again in {formatDuration(waitSeconds)}.</p>}
              </form>
            ) : (
              <div className="flex flex-col">
                <h1 className="text-display font-semibold tracking-[-0.02em] text-fg">Who are you?</h1>
                <p className="mt-2 text-base text-fg-3">Each crew member has their own account.</p>
                <div className="mt-8">
                  <Segmented<Location>
                    label="Workstation"
                    value={location}
                    options={LOCATIONS}
                    onChange={(next) => {
                      setLocation(next);
                      choose(null);
                    }}
                  />
                </div>

                <div className="mt-6">
                  {down && <BackendDown desktop={desktop} failure={failure} retrying={accounts.isFetching} onRetry={() => void refetch()} />}
                  {accounts.isPending && !down && (
                    <div className="flex flex-col gap-2">
                      {SKELETON_ROWS.map((row) => (
                        <Skeleton key={row} className="h-[68px] rounded-2xl" />
                      ))}
                    </div>
                  )}
                  {accounts.data && (
                    <ul aria-label="Accounts" className="-mx-3 flex flex-col gap-0.5">
                      {visible.map((account) => (
                        <AccountRow key={account.username} account={account} onSelect={() => choose(account.username)} />
                      ))}
                    </ul>
                  )}
                </div>
              </div>
            )}
          </div>

          <p className="mx-auto mt-12 w-full max-w-[400px] text-small text-fg-4">A decision-support prototype, not a medical device. NASA Space Apps 2026.</p>
        </div>
      </main>
    </div>
  );
}
