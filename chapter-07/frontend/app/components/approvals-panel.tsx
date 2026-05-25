"use client";

import { Check, Loader2 } from "lucide-react";

import { EmptyPanel } from "./metric";
import type { PendingAction } from "./types";

export function ApprovalsPanel({
  pendingActions,
  approving,
  approvedActions,
  onApprove,
}: {
  pendingActions: PendingAction[];
  approving: string | null;
  approvedActions: string[];
  onApprove: (action: PendingAction) => void;
}) {
  return (
    <div className="panel approvalsPanel">
      <div className="panelHeader">
        <Check size={18} />
        <h2>Approvals</h2>
      </div>
      {pendingActions.length === 0 ? (
        <EmptyPanel text="Staged tasks, drafts, and calendar holds appear here." />
      ) : (
        <div className="actionList">
          {pendingActions.map((action) => (
            <div className="actionItem" key={action.action_id}>
              <div>
                <p className="mono">{action.type}</p>
                <h3>{action.title}</h3>
              </div>
              <button
                className={approvedActions.includes(action.action_id) ? "approvedActionButton" : ""}
                onClick={() => onApprove(action)}
                disabled={
                  approving === action.action_id
                  || approvedActions.includes(action.action_id)
                }
              >
                {approving === action.action_id ? (
                  <Loader2 className="spinIcon" size={15} />
                ) : (
                  <Check size={15} />
                )}
                {approvedActions.includes(action.action_id) ? "Approved" : "Approve"}
              </button>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
