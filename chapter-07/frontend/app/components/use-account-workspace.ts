"use client";

import { useEffect, useMemo, useRef, useState } from "react";
import { useAgent, useCopilotKit } from "@copilotkit/react-core/v2";

import type {
  AccountSummary,
  AgentState,
  PendingAction,
  ThreadDetail,
  ThreadSummary,
} from "./types";
import { asState, latestMessagePreview, upsertThread } from "./workspace-utils";

export function useAccountWorkspace() {
  const { copilotkit } = useCopilotKit();
  const { agent } = useAgent({ agentId: "account_assistant" });
  const state = asState(agent?.state);
  const bootedThreads = useRef(false);
  const [threads, setThreads] = useState<ThreadSummary[]>([]);
  const [activeThreadId, setActiveThreadId] = useState("");
  const [threadLoading, setThreadLoading] = useState(true);
  const [approving, setApproving] = useState<string | null>(null);
  const [approvedActions, setApprovedActions] = useState<string[]>([]);
  const [shortcutRunning, setShortcutRunning] = useState(false);
  const [accounts, setAccounts] = useState<AccountSummary[]>([]);
  const [accountMenuOpen, setAccountMenuOpen] = useState(false);

  const surfaces = state.ui_surfaces ?? [];
  const pendingActions = state.pending_actions ?? [];
  const runtimeReady = copilotkit.runtimeConnectionStatus === "connected";
  const running = Boolean(agent?.isRunning || shortcutRunning);
  const statusLabel = running
    ? "running"
    : runtimeReady
      ? "connected"
      : "connecting";

  const sortedAccounts = useMemo(() => {
    const healthRank = { at_risk: 0, watch: 1, healthy: 2 };
    return [...accounts].sort((a, b) => {
      const rank = healthRank[a.health] - healthRank[b.health];
      return rank === 0 ? a.name.localeCompare(b.name) : rank;
    });
  }, [accounts]);

  const latestAccount = useMemo(
    () => surfaces.find((surface) => surface.type === "account_health_card")?.payload,
    [surfaces],
  );
  const selectedAccount = useMemo(() => {
    const surfaceAccount = latestAccount?.account as AccountSummary | undefined;
    return (
      surfaceAccount
      ?? sortedAccounts.find((account) => account.account_id === state.active_account_id)
    );
  }, [latestAccount, sortedAccounts, state.active_account_id]);
  const activeThread = threads.find((thread) => thread.thread_id === activeThreadId);
  const displayTitle = state.session_title ?? activeThread?.title ?? "New conversation";

  useEffect(() => {
    void loadAccounts();
  }, []);

  useEffect(() => {
    if (!agent || !runtimeReady || bootedThreads.current) {
      return;
    }
    bootedThreads.current = true;
    void bootstrapThreads();
  }, [agent, runtimeReady]);

  useEffect(() => {
    if (!activeThreadId || !state.thread_id || state.thread_id !== activeThreadId) {
      return;
    }
    setThreads((current) => upsertThread(current, {
      thread_id: activeThreadId,
      title: state.session_title ?? activeThread?.title ?? "New conversation",
      created_at: state.created_at ?? activeThread?.created_at ?? new Date().toISOString(),
      updated_at: state.updated_at ?? new Date().toISOString(),
      active_account_id: state.active_account_id ?? activeThread?.active_account_id ?? null,
      message_count: state.messages?.length ?? activeThread?.message_count ?? 0,
      last_message_preview: latestMessagePreview(state.messages) ?? activeThread?.last_message_preview ?? "",
    }));
  }, [
    activeThreadId,
    activeThread?.active_account_id,
    activeThread?.created_at,
    activeThread?.last_message_preview,
    activeThread?.message_count,
    activeThread?.title,
    state.active_account_id,
    state.created_at,
    state.messages,
    state.session_title,
    state.thread_id,
    state.updated_at,
  ]);

  async function bootstrapThreads() {
    setThreadLoading(true);
    try {
      const response = await fetch("/api/account-assistant/threads", { cache: "no-store" });
      if (!response.ok) {
        throw new Error(`Thread list failed with ${response.status}`);
      }
      const data = await response.json() as { threads: ThreadSummary[] };
      const loadedThreads = data.threads ?? [];
      setThreads(loadedThreads);
      if (loadedThreads.length > 0) {
        await selectThread(loadedThreads[0].thread_id);
      } else {
        await startNewThread();
      }
    } finally {
      setThreadLoading(false);
    }
  }

  async function loadAccounts() {
    try {
      const response = await fetch("/api/account-assistant/accounts", { cache: "no-store" });
      if (!response.ok) {
        throw new Error(`Account list failed with ${response.status}`);
      }
      const data = await response.json() as { accounts: AccountSummary[] };
      setAccounts(data.accounts ?? []);
    } catch {
      setAccounts([]);
    }
  }

  async function startNewThread() {
    if (!agent || running) {
      return;
    }
    const response = await fetch("/api/account-assistant/threads", { method: "POST" });
    if (!response.ok) {
      throw new Error(`Thread create failed with ${response.status}`);
    }
    const thread = await response.json() as ThreadSummary;
    setThreads((current) => upsertThread(current, thread));
    setActiveThreadId(thread.thread_id);
    setApprovedActions([]);
    setAccountMenuOpen(false);
    agent.threadId = thread.thread_id;
    agent.setMessages([]);
    agent.setState({
      thread_id: thread.thread_id,
      session_title: thread.title,
      created_at: thread.created_at,
      updated_at: thread.updated_at,
    });
  }

  async function selectThread(threadId: string) {
    if (!agent || running) {
      return;
    }
    setThreadLoading(true);
    setActiveThreadId(threadId);
    setApprovedActions([]);
    setAccountMenuOpen(false);
    agent.threadId = threadId;
    try {
      const response = await fetch(`/api/account-assistant/threads/${threadId}`, {
        cache: "no-store",
      });
      if (response.status === 404) {
        agent.setMessages([]);
        agent.setState({ thread_id: threadId, session_title: "New conversation" });
        return;
      }
      if (!response.ok) {
        throw new Error(`Thread load failed with ${response.status}`);
      }
      const detail = await response.json() as ThreadDetail;
      agent.setMessages(detail.messages);
      agent.setState(detail.snapshot as AgentState);
      setThreads((current) => upsertThread(current, detail.summary));
    } finally {
      setThreadLoading(false);
    }
  }

  async function runStarterPrompt(prompt: string) {
    if (!agent || !runtimeReady || !activeThreadId || agent.isRunning || shortcutRunning) {
      return;
    }
    setShortcutRunning(true);
    try {
      agent.threadId = activeThreadId;
      agent.addMessage({
        id: crypto.randomUUID(),
        role: "user",
        content: prompt,
      });
      await copilotkit.runAgent({ agent });
    } finally {
      setShortcutRunning(false);
    }
  }

  async function approve(action: PendingAction) {
    setApproving(action.action_id);
    try {
      const response = await fetch("/api/account-assistant/actions/approve", {
        method: "POST",
        headers: { "content-type": "application/json" },
        body: JSON.stringify({ action }),
      });
      if (!response.ok) {
        throw new Error(`Approval failed with ${response.status}`);
      }
      setApprovedActions((current) => [...new Set([...current, action.action_id])]);
    } finally {
      setApproving(null);
    }
  }

  return {
    accountMenuOpen,
    activeThreadId,
    approving,
    approvedActions,
    displayTitle,
    pendingActions,
    running,
    runtimeReady,
    selectedAccount,
    setAccountMenuOpen,
    sortedAccounts,
    startNewThread,
    selectThread,
    runStarterPrompt,
    approve,
    state,
    statusLabel,
    surfaces,
    threadLoading,
    threads,
    canCreateThread: Boolean(agent),
  };
}
