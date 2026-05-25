"use client";

import { Clock3, Loader2, MessageSquareText, Plus } from "lucide-react";

import type { ThreadSummary } from "./types";
import { formatThreadTime } from "./workspace-utils";

export function ThreadList({
  threads,
  activeThreadId,
  loading,
  running,
  canCreate,
  onCreate,
  onSelect,
}: {
  threads: ThreadSummary[];
  activeThreadId: string;
  loading: boolean;
  running: boolean;
  canCreate: boolean;
  onCreate: () => void;
  onSelect: (threadId: string) => void;
}) {
  return (
    <aside className="threadColumn">
      <div className="panel threadPanel">
        <div className="threadPanelHeader">
          <div className="panelHeader">
            <MessageSquareText size={18} />
            <h2>Threads</h2>
          </div>
          <button
            className="iconButton"
            onClick={onCreate}
            disabled={!canCreate || running}
            aria-label="Start a new conversation"
            title="Start a new conversation"
          >
            <Plus size={16} />
          </button>
        </div>
        <div className="threadList">
          {loading && threads.length === 0 ? (
            <div className="threadLoading mono">
              <Loader2 size={14} />
              loading
            </div>
          ) : (
            threads.map((thread) => (
              <button
                className={`threadItem ${thread.thread_id === activeThreadId ? "threadItemActive" : ""}`}
                key={thread.thread_id}
                onClick={() => onSelect(thread.thread_id)}
                disabled={running || thread.thread_id === activeThreadId}
              >
                <strong>{thread.title}</strong>
                <span>{thread.last_message_preview || "No messages yet"}</span>
                <small>
                  <Clock3 size={12} />
                  {formatThreadTime(thread.updated_at)}
                </small>
              </button>
            ))
          )}
        </div>
      </div>
    </aside>
  );
}
