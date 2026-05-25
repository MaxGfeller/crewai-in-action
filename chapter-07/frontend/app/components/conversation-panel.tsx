"use client";

import { CopilotChat } from "@copilotkit/react-core/v2";
import { Loader2, MessageSquareText } from "lucide-react";

export function ConversationPanel({
  activeThreadId,
  running,
}: {
  activeThreadId: string;
  running: boolean;
}) {
  return (
    <section className="conversationColumn">
      <div className="panel chatPanel">
        <div className="chatHeader">
          <div className="panelHeader chatHeaderTitle">
            <MessageSquareText size={18} />
            <h2>Conversation</h2>
            {running ? (
              <div className="runStatus mono" role="status">
                <Loader2 className="spinIcon" size={14} />
                running
              </div>
            ) : null}
          </div>
        </div>
        <div className="embeddedChat">
          {activeThreadId ? (
            <CopilotChat
              key={activeThreadId}
              agentId="account_assistant"
              threadId={activeThreadId}
              labels={{
                welcomeMessageText: "Ask about a customer account.",
                chatInputPlaceholder: "Type a message for the account assistant...",
              }}
              input={{
                addMenuButton: EmptySlot,
                disclaimer: EmptySlot,
                showDisclaimer: false,
              }}
            />
          ) : (
            <div className="emptyCanvas">
              <Loader2 size={24} />
              <h2>Loading conversation</h2>
            </div>
          )}
        </div>
      </div>
    </section>
  );
}

function EmptySlot() {
  return null;
}
