import { ListChecks } from "lucide-react";

import { Metric } from "./metric";
import type { AgentState } from "./types";

export function WorkflowPanel({ state }: { state: AgentState }) {
  return (
    <div className="contextGrid">
      <div className="panel workflowPanel">
        <div className="panelHeader">
          <ListChecks size={18} />
          <h2>Workflow</h2>
        </div>
        <div className="metricGrid">
          <Metric label="Prompt budget" value={`${state.estimated_prompt_tokens ?? 0} tok`} />
          <Metric label="Compacted" value={state.compacted_this_turn ? "yes" : "no"} />
          <Metric label="Tools" value={`${state.tool_traces?.length ?? 0}`} />
        </div>
      </div>
    </div>
  );
}
