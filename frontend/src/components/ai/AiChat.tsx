"use client";
/**
 * Medicul AI, ca o conversație din aplicațiile de chat: firul de mesaje la mijloc, caseta de scris jos.
 * Frontend-ul vorbește doar cu `/ai/chat` din backend; dacă modelul nu răspunde, backend-ul trimite textul din
 * catalog (`fallback`), iar aici se spune asta deschis. Fiecare răspuns își arată sursele NASA.
 *
 * Două forme: `page` (ecranul „AI doctor”, pe toată înălțimea) și `embedded` (în detaliul unei alerte, într-un card).
 */
import { useMutation } from "@tanstack/react-query";
import { ArrowUp, Check, ChevronDown, Copy, Stethoscope, X } from "lucide-react";
import { motion } from "motion/react";
import { useEffect, useLayoutEffect, useRef, useState, type KeyboardEvent, type ReactElement, type ReactNode } from "react";
import { Card, IconButton, Notice, SectionTitle, Spinner, Tag, Tip, cx, rise } from "@/components/ui";
import { errorMessage, type Schemas } from "@/lib/api";
import { askAi } from "@/lib/endpoints";
import { formatDuration } from "@/lib/format";
import { useAiStatus } from "@/lib/queries";
import { useToast } from "@/lib/toast";
import { useKeystrokes } from "@/lib/useKeystrokes";

type AiStatus = Schemas["AiStatus"];
type ChatMessage = Schemas["ChatMessage"];
type AiAnswer = Schemas["AiChatResponse"];
type KeystrokeBindings = ReturnType<typeof useKeystrokes>;

interface Exchange {
  readonly id: number;
  readonly question: string;
  readonly answer: AiAnswer;
}

/** Unde rulează modelul, spus scurt (în casetă) și pe larg (în indiciu). */
const MODE_META = {
  local: { short: "Local model", long: "The model runs on this computer, with no internet." },
  colab_simulation: { short: "Colab simulation", long: "The model runs in Google Colab, shown openly as a simulation of the ship's computer." },
  fallback: { short: "Catalog only", long: "The model is not responding. Answers come straight from the catalog text." },
  mock: { short: "No model yet", long: "The AI service is running without a model. Answers come from the catalog text." },
} as const satisfies Record<AiStatus["mode"], { readonly short: string; readonly long: string }>;

const HISTORY_LIMIT = 6;
const QUESTION_MAX = 1000;
const MS_PER_SECOND = 1000;
const MAX_TEXTAREA_PX = 220;
const COPIED_MS = 1600;
const MARK_ICON = 14;
const MARK_ICON_LARGE = 24;
const DEFAULT_DISCLAIMER = "Decision support from NASA sources, not a diagnosis.";
const SUGGESTIONS = ["Why has my night pulse gone up?", "What can I do today to sleep better?", "Why does splitting my workout in two matter?"] as const;

// ---------------------------------------------------------------- conversația

/** Întrebările și răspunsurile, plus trimiterea: istoricul trimis la backend e limitat la ultimele 6 mesaje. */
function useConversation(crewId: string, alertId: string | undefined, onFailed: (question: string) => void) {
  const [exchanges, setExchanges] = useState<readonly Exchange[]>([]);
  const ask = useMutation({
    mutationFn: async (message: string) => {
      const history: ChatMessage[] = exchanges
        .flatMap((exchange): ChatMessage[] => [
          { role: "user", content: exchange.question },
          { role: "assistant", content: exchange.answer.answer },
        ])
        .slice(-HISTORY_LIMIT);
      return askAi({ crew_id: crewId, message, alert_id: alertId ?? null, history });
    },
    onSuccess: (answer, question) => setExchanges((current) => [...current, { id: (current.at(-1)?.id ?? 0) + 1, question, answer }]),
    onError: (_error, question) => onFailed(question),
  });
  const send = (message: string): boolean => {
    const trimmed = message.trim();
    if (!trimmed || ask.isPending) return false;
    ask.mutate(trimmed);
    return true;
  };
  return { exchanges, ask, send } as const;
}

// ---------------------------------------------------------------- mesajele

function DoctorMark({ large }: { readonly large?: boolean }): ReactElement {
  return (
    <span aria-hidden="true" className={cx("grid shrink-0 place-items-center rounded-full border border-line-2 bg-surface-3 text-fg-2", large ? "size-14" : "size-7")}>
      <Stethoscope size={large ? MARK_ICON_LARGE : MARK_ICON} strokeWidth={1.8} />
    </span>
  );
}

function UserBubble({ children }: { readonly children: ReactNode }): ReactElement {
  return (
    <div className="flex justify-end">
      <p className="max-w-[82%] whitespace-pre-line rounded-3xl rounded-br-lg bg-white/[0.08] px-4 py-2.5 text-base leading-relaxed text-fg">{children}</p>
    </div>
  );
}

function CopyButton({ text }: { readonly text: string }): ReactElement {
  const notify = useToast();
  const [copied, setCopied] = useState(false);
  useEffect(() => {
    if (!copied) return undefined;
    const timer = setTimeout(() => setCopied(false), COPIED_MS);
    return () => clearTimeout(timer);
  }, [copied]);
  const copy = async (): Promise<void> => {
    try {
      await navigator.clipboard.writeText(text);
      setCopied(true);
    } catch (error) {
      notify({ title: "Could not copy the answer", detail: errorMessage(error), status: "alert" });
    }
  };
  return (
    <Tip label={copied ? "Copied" : "Copy"}>
      <IconButton label={copied ? "Copied" : "Copy the answer"} size="sm" onClick={() => void copy()} className="text-fg-4">
        {copied ? <Check size={15} strokeWidth={2} /> : <Copy size={14} strokeWidth={1.8} />}
      </IconButton>
    </Tip>
  );
}

function Sources({ citations }: { readonly citations: AiAnswer["citations"] }): ReactElement {
  return (
    <ul className="mt-1 flex flex-col gap-2 rounded-2xl border border-line p-3">
      {citations.map((citation, index) => (
        <li key={citation.url + citation.title} className="flex gap-3 text-small">
          <span className="num mt-px grid size-5 shrink-0 place-items-center rounded-full bg-surface-4 text-caption text-fg-2">{index + 1}</span>
          <span className="min-w-0">
            <a href={citation.url} target="_blank" rel="noreferrer" className="font-medium">
              {citation.title}
            </a>
            <span className="mt-0.5 block leading-relaxed text-fg-3">“{citation.snippet}”</span>
          </span>
        </li>
      ))}
    </ul>
  );
}

function AssistantAnswer({ answer }: { readonly answer: AiAnswer }): ReactElement {
  const [showSources, setShowSources] = useState(false);
  const count = answer.citations.length;
  return (
    <div className="flex gap-3.5">
      <DoctorMark />
      <div className="flex min-w-0 flex-1 flex-col gap-2 pt-0.5">
        <div className="prose-q whitespace-pre-line">{answer.answer}</div>
        <div className="-ml-1.5 flex flex-wrap items-center gap-1.5">
          <CopyButton text={answer.answer} />
          {count ? (
            <button
              type="button"
              aria-expanded={showSources}
              onClick={() => setShowSources((open) => !open)}
              className="inline-flex h-8 items-center gap-1.5 rounded-full px-2.5 text-small text-fg-3 transition-colors hover:bg-white/[0.07] hover:text-fg"
            >
              {count === 1 ? "1 source" : `${count} sources`}
              <ChevronDown size={14} strokeWidth={1.9} className={cx("transition-transform duration-200", showSources && "rotate-180")} />
            </button>
          ) : (
            <Tag>no source</Tag>
          )}
          {answer.fallback && <Tag>catalog text, the model did not respond</Tag>}
          <span className="num ml-1 text-caption text-fg-4">
            {answer.model}, {formatDuration(answer.latency_ms / MS_PER_SECOND)}
          </span>
        </div>
        {showSources && <Sources citations={answer.citations} />}
      </div>
    </div>
  );
}

function PendingAnswer(): ReactElement {
  return (
    <div className="flex items-center gap-3.5">
      <DoctorMark />
      <p className="shimmer-text text-base">Searching the NASA sources… this can take 5–15 seconds.</p>
    </div>
  );
}

function Thread({ exchanges, pendingQuestion }: { readonly exchanges: readonly Exchange[]; readonly pendingQuestion: string | null }): ReactElement {
  return (
    <ol aria-live="polite" aria-label="Conversation" className="flex flex-col gap-7">
      {exchanges.map((exchange) => (
        <li key={exchange.id} className="flex flex-col gap-5">
          <UserBubble>{exchange.question}</UserBubble>
          <AssistantAnswer answer={exchange.answer} />
        </li>
      ))}
      {pendingQuestion && (
        <li className="flex flex-col gap-5">
          <UserBubble>{pendingQuestion}</UserBubble>
          <PendingAnswer />
        </li>
      )}
    </ol>
  );
}

// ---------------------------------------------------------------- caseta de scris

/** Câmpul care crește cu textul, până la 220 px; Enter trimite, Shift+Enter face rând nou. */
function AutoTextarea({ value, onChange, onSubmit, keystrokes, autoFocus }: {
  readonly value: string;
  readonly onChange: (value: string) => void;
  readonly onSubmit: () => void;
  readonly keystrokes: KeystrokeBindings;
  readonly autoFocus?: boolean;
}): ReactElement {
  const ref = useRef<HTMLTextAreaElement>(null);
  useLayoutEffect(() => {
    const field = ref.current;
    if (!field) return;
    field.style.height = "auto";
    field.style.height = `${Math.min(field.scrollHeight, MAX_TEXTAREA_PX)}px`;
  }, [value]);
  const onKeyDown = (event: KeyboardEvent<HTMLTextAreaElement>): void => {
    keystrokes.onKeyDown(event);
    if (event.key === "Enter" && !event.shiftKey && !event.nativeEvent.isComposing) {
      event.preventDefault();
      onSubmit();
    }
  };
  return (
    <textarea
      ref={ref}
      rows={1}
      value={value}
      maxLength={QUESTION_MAX}
      autoFocus={autoFocus}
      aria-label="Your question for the AI doctor"
      placeholder="Ask the AI doctor"
      onChange={(event) => onChange(event.target.value)}
      onKeyDown={onKeyDown}
      onKeyUp={keystrokes.onKeyUp}
      className="scroll-q block w-full resize-none bg-transparent px-5 pb-2 pt-4 text-lead leading-[1.55] text-fg outline-none placeholder:text-fg-4 focus-visible:outline-none"
    />
  );
}

function SendButton({ busy, disabled, onSend }: { readonly busy: boolean; readonly disabled: boolean; readonly onSend: () => void }): ReactElement {
  return (
    <button
      type="button"
      aria-label={busy ? "Waiting for the answer" : "Send"}
      disabled={disabled || busy}
      onClick={onSend}
      className={cx(
        "grid size-9 shrink-0 place-items-center rounded-full transition-colors duration-150",
        disabled && !busy ? "bg-white/[0.09] text-fg-4" : "bg-solid text-on-solid hover:bg-fg",
        busy && "cursor-progress",
      )}
    >
      {busy ? <Spinner /> : <ArrowUp size={18} strokeWidth={2.2} />}
    </button>
  );
}

function ModeLabel({ status }: { readonly status: AiStatus | undefined }): ReactElement | null {
  if (!status) return null;
  const meta = MODE_META[status.mode];
  return (
    <Tip label={status.model ? `${meta.long} Model: ${status.model}.` : meta.long}>
      <span tabIndex={0} className="inline-flex h-8 items-center gap-2 rounded-full px-3 text-small text-fg-3">
        <span aria-hidden="true" className={cx("size-1.5 rounded-full", status.ready ? "bg-fg-2" : "bg-fg-5")} />
        {meta.short}
      </span>
    </Tip>
  );
}

function Composer({ value, onChange, onSend, busy, status, keystrokes, autoFocus }: {
  readonly value: string;
  readonly onChange: (value: string) => void;
  readonly onSend: () => void;
  readonly busy: boolean;
  readonly status: AiStatus | undefined;
  readonly keystrokes: KeystrokeBindings;
  readonly autoFocus?: boolean;
}): ReactElement {
  return (
    <div className="float-q relative rounded-[26px] transition-colors duration-150 focus-within:border-fg-4">
      <span aria-hidden="true" className="busy-ring" data-on={busy ? "true" : "false"} />
      <AutoTextarea value={value} onChange={onChange} onSubmit={onSend} keystrokes={keystrokes} autoFocus={autoFocus} />
      <div className="flex items-center gap-1 px-2.5 pb-2.5">
        <ModeLabel status={status} />
        <span className="flex-1" />
        <SendButton busy={busy} disabled={!value.trim()} onSend={onSend} />
      </div>
    </div>
  );
}

function Suggestions({ onPick, centered }: { readonly onPick: (text: string) => void; readonly centered?: boolean }): ReactElement {
  return (
    <div className={cx("flex flex-wrap gap-2", centered && "justify-center")}>
      {SUGGESTIONS.map((suggestion) => (
        <button
          key={suggestion}
          type="button"
          onClick={() => onPick(suggestion)}
          className="inline-flex h-9 items-center rounded-full border border-line-2 bg-white/[0.02] px-3.5 text-body text-fg-2 transition-colors hover:border-line-3 hover:bg-white/[0.05] hover:text-fg"
        >
          {suggestion}
        </button>
      ))}
    </div>
  );
}

function ErrorLine({ error, onDismiss }: { readonly error: unknown; readonly onDismiss: () => void }): ReactElement {
  return (
    <Notice
      tone="alert"
      title="The question did not get through"
      className="mb-3"
      action={
        <IconButton label="Dismiss" size="sm" onClick={onDismiss}>
          <X size={14} strokeWidth={2} />
        </IconButton>
      }
    >
      {errorMessage(error)}
    </Notice>
  );
}

// ---------------------------------------------------------------- cele două forme

export function AiChat({
  crewId,
  alertId,
  title = "Ask the AI doctor",
  variant = "page",
}: {
  readonly crewId: string;
  readonly alertId?: string;
  readonly title?: string;
  readonly variant?: "page" | "embedded";
}): ReactElement {
  const status = useAiStatus(true);
  const [question, setQuestion] = useState("");
  const keystrokes = useKeystrokes(crewId, "ai_chat");
  // dacă întrebarea nu ajunge, se întoarce în casetă, ca să nu trebuiască scrisă din nou
  const { exchanges, ask, send } = useConversation(crewId, alertId, (failed) => setQuestion((current) => current || failed));
  const scroller = useRef<HTMLDivElement>(null);

  const pendingQuestion = ask.isPending ? (ask.variables ?? null) : null;
  const empty = !exchanges.length && !pendingQuestion;
  const submit = (text: string): void => {
    if (send(text)) setQuestion("");
  };

  useEffect(() => {
    const element = scroller.current;
    if (element) element.scrollTo({ top: element.scrollHeight, behavior: "smooth" });
  }, [exchanges.length, pendingQuestion]);

  const composer = (
    <Composer
      value={question}
      onChange={setQuestion}
      onSend={() => submit(question)}
      busy={ask.isPending}
      status={status.data}
      keystrokes={keystrokes}
      autoFocus={variant === "page"}
    />
  );
  const errorLine = ask.isError && <ErrorLine error={ask.error} onDismiss={() => ask.reset()} />;

  if (variant === "embedded") {
    return (
      <Card as="section" aria-labelledby="ai-title">
        <SectionTitle id="ai-title">{title}</SectionTitle>
        {empty ? (
          <div className="mb-4">
            <Suggestions onPick={submit} />
          </div>
        ) : (
          <div className="mb-5">
            <Thread exchanges={exchanges} pendingQuestion={pendingQuestion} />
          </div>
        )}
        {errorLine}
        {composer}
      </Card>
    );
  }

  const disclaimer = exchanges.at(-1)?.answer.disclaimer ?? DEFAULT_DISCLAIMER;

  if (empty) {
    return (
      <div className="scroll-q flex min-h-0 flex-1 flex-col items-center justify-center overflow-y-auto px-6 pb-[12vh]">
        <motion.div {...rise} className="flex w-full max-w-[760px] flex-col items-center">
          <DoctorMark large />
          <h2 className="mt-6 text-center text-display font-semibold tracking-[-0.03em] text-fg">What would you like to ask?</h2>
          <p className="mt-2 max-w-[56ch] text-center text-lead text-fg-3">
            Answers come from the catalog the team wrote from NASA documents, with the source of every answer.
          </p>
          <div className="mt-8 w-full">
            {errorLine}
            {composer}
          </div>
          <div className="mt-5">
            <Suggestions onPick={submit} centered />
          </div>
        </motion.div>
      </div>
    );
  }

  return (
    <div className="flex min-h-0 flex-1 flex-col">
      <div ref={scroller} className="scroll-q min-h-0 flex-1 overflow-y-auto">
        <div className="mx-auto w-full max-w-[760px] px-6 pb-8 pt-6">
          <Thread exchanges={exchanges} pendingQuestion={pendingQuestion} />
        </div>
      </div>
      <div className="mx-auto w-full max-w-[760px] px-6 pb-4">
        {errorLine}
        {composer}
        <p className="mt-2.5 text-center text-caption text-fg-4">{disclaimer}</p>
      </div>
    </div>
  );
}
