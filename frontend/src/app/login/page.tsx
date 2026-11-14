"use client";
/**
 * „Cine ești?” — fiecare astronaut are contul lui. Ecranul arată câte o casetă pe cont; la alegere cere parola
 * acelui cont. Conturile de la bord și cel de pe Pământ sunt separate după stația de lucru.
 */
import { useRouter } from "next/navigation";
import { useEffect, useState, type FormEvent, type ReactElement } from "react";
import { Backdrop } from "@/components/layout/Shell";
import { RoleIcon, hasRoleIcon } from "@/components/login/RoleIcon";
import { Button, Card, Field, Input, Notice, Segmented, Skeleton, cx } from "@/components/ui";
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
const SKELETON_TILES = ["a", "b", "c", "d"] as const;
const RETRY_MS = 3000;
const BACKEND_COMMAND = "cd backend && uv run uvicorn app.main:app --port 8000";

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

function AccountTile({ account, selected, onSelect }: { readonly account: Account; readonly selected: boolean; readonly onSelect: () => void }): ReactElement {
  const withIcon = hasRoleIcon(account.username);
  const idleTone = withIcon ? "bg-surface-4 text-crew" : "bg-surface-4 text-fg";
  return (
    <button
      type="button"
      role="radio"
      aria-checked={selected}
      onClick={onSelect}
      className={cx(
        "flex items-center gap-3 rounded-2xl border p-3 text-left transition-colors",
        selected ? "border-solid bg-white/[0.07]" : "border-line-2 bg-white/[0.02] hover:border-line-3 hover:bg-white/[0.05]",
      )}
    >
      {/* icoana de rol a contului; un cont fără icoană își arată inițialele */}
      <span
        aria-hidden="true"
        className={cx("grid size-10 shrink-0 place-items-center rounded-full text-body font-semibold", selected ? "bg-solid text-on-solid" : idleTone)}
      >
        {withIcon ? <RoleIcon username={account.username} /> : account.initials}
      </span>
      <span className="min-w-0">
        <span className="block truncate text-base font-medium text-fg">{account.display_name}</span>
        <span className="block truncate text-small text-fg-4">{ROLE_LABEL[account.role]}</span>
      </span>
    </button>
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
  const selected = visible.find((account) => account.username === username) ?? null;

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
    <div className="relative flex min-h-full flex-col bg-bg">
      <Backdrop />
      <div className="app-drag absolute inset-x-0 top-0 z-10 h-10" />
      <main className="scroll-q relative z-10 flex flex-1 flex-col items-center overflow-y-auto px-6 pb-10 pt-[7vh]">
        {/* eslint-disable-next-line @next/next/no-img-element -- logo local; exportul static nu optimizează imagini */}
        <img src="/brand/mark-420.png" srcSet="/brand/mark-420.png 1x, /brand/mark-840.png 2x" alt="" width={420} height={246} className="h-auto w-[min(420px,70vw)]" />
        {/* eslint-disable-next-line @next/next/no-img-element -- logo local */}
        <img src="/brand/wordmark-300.png" srcSet="/brand/wordmark-300.png 1x, /brand/wordmark-600.png 2x" alt="SHADOW" width={300} height={49} className="mt-2 h-auto w-[min(300px,56vw)]" />
        <p className="mt-5 max-w-[52ch] text-center text-lead text-fg-3">
          Compare how you say you feel with what your data shows, against your own in-flight baseline.
        </p>

        <Card as="section" aria-labelledby="who" className="mt-9 w-full max-w-[640px] p-6">
          <div className="mb-4 flex flex-wrap items-center justify-between gap-3">
            <h1 id="who" className="text-title font-medium text-fg">
              Who are you?
            </h1>
            <Segmented<Location>
              size="sm"
              label="Workstation"
              value={location}
              options={LOCATIONS}
              onChange={(next) => {
                setLocation(next);
                setUsername(null);
                setError(null);
              }}
            />
          </div>

          {down && <BackendDown desktop={desktop} failure={failure} retrying={accounts.isFetching} onRetry={() => void refetch()} />}

          {accounts.isPending && !down && (
            <div className="grid gap-2.5 sm:grid-cols-2">
              {SKELETON_TILES.map((tile) => (
                <Skeleton key={tile} className="h-[66px] rounded-2xl" />
              ))}
            </div>
          )}

          {accounts.data && (
            <div role="radiogroup" aria-label="Accounts" className="grid gap-2.5 sm:grid-cols-2">
              {visible.map((account) => (
                <AccountTile
                  key={account.username}
                  account={account}
                  selected={account.username === username}
                  onSelect={() => {
                    setUsername(account.username);
                    setError(null);
                    setPassword("");
                  }}
                />
              ))}
            </div>
          )}

          {selected && (
            <form onSubmit={(event) => void submit(event)} className="mt-5 flex flex-col gap-3">
              <Field id={PASSWORD_FIELD_ID} label={`Password for “${selected.display_name}”`} error={error}>
                <div className="flex gap-2">
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
                  />
                  <Button type="submit" variant="primary" size="lg" className="h-10 shrink-0" busy={pending} disabled={!password || Boolean(waitSeconds)}>
                    Sign in
                  </Button>
                </div>
              </Field>
              {Boolean(waitSeconds) && <p className="text-small text-fg-3">You can try again in {formatDuration(waitSeconds)}.</p>}
            </form>
          )}
        </Card>

        <p className="mt-6 text-small text-fg-4">A decision-support prototype, not a medical device. NASA Space Apps 2026.</p>
      </main>
    </div>
  );
}
