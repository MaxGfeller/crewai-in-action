import type { AgentState, ThreadSummary } from "./types";

export function asState(raw: unknown): AgentState {
  return (raw ?? {}) as AgentState;
}

export function upsertThread(threads: ThreadSummary[], thread: ThreadSummary) {
  const next = [
    thread,
    ...threads.filter((current) => current.thread_id !== thread.thread_id),
  ];
  return next.sort((a, b) => (b.updated_at || "").localeCompare(a.updated_at || ""));
}

export function latestMessagePreview(messages?: AgentState["messages"]) {
  const latest = messages?.at(-1)?.content;
  if (!latest) {
    return undefined;
  }
  return latest.length > 140 ? `${latest.slice(0, 137)}...` : latest;
}

export function formatThreadTime(value: string) {
  if (!value) {
    return "new";
  }
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) {
    return "new";
  }
  return new Intl.DateTimeFormat(undefined, {
    month: "short",
    day: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  }).format(date);
}
