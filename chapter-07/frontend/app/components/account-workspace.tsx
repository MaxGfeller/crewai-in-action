"use client";

import { AccountPicker } from "./account-picker";
import { ApprovalsPanel } from "./approvals-panel";
import { ConversationPanel } from "./conversation-panel";
import { RichWorkspace } from "./rich-workspace";
import { ThreadList } from "./thread-list";
import { useAccountWorkspace } from "./use-account-workspace";
import { WorkflowPanel } from "./workflow-panel";

export function AccountWorkspace() {
  const workspace = useAccountWorkspace();

  return (
    <main className="workspace" aria-busy={workspace.running}>
      <section className="topbar">
        <div>
          <h1>Customer Account Assistant</h1>
        </div>
        <div className="topbarControls">
          <AccountPicker
            accounts={workspace.sortedAccounts}
            selectedAccount={workspace.selectedAccount}
            open={workspace.accountMenuOpen}
            disabled={
              workspace.running
              || workspace.threadLoading
              || !workspace.activeThreadId
            }
            onOpenChange={workspace.setAccountMenuOpen}
            onSelect={(account) => {
              workspace.setAccountMenuOpen(false);
              void workspace.runStarterPrompt(`Load ${account.name} and summarize the account.`);
            }}
          />
          <div className="runtime mono">
            <span>{workspace.statusLabel}</span>
            <strong>{workspace.displayTitle}</strong>
          </div>
        </div>
      </section>

      <section className="appGrid">
        <ThreadList
          threads={workspace.threads}
          activeThreadId={workspace.activeThreadId}
          loading={workspace.threadLoading}
          running={workspace.running}
          canCreate={workspace.canCreateThread}
          onCreate={() => void workspace.startNewThread()}
          onSelect={(threadId) => void workspace.selectThread(threadId)}
        />

        <ConversationPanel
          activeThreadId={workspace.activeThreadId}
          running={workspace.running}
        />

        <aside className="workspaceColumn">
          <WorkflowPanel state={workspace.state} />
          <RichWorkspace surfaces={workspace.surfaces} />
          <ApprovalsPanel
            pendingActions={workspace.pendingActions}
            approving={workspace.approving}
            approvedActions={workspace.approvedActions}
            onApprove={(action) => void workspace.approve(action)}
          />
        </aside>
      </section>
    </main>
  );
}
