import { HttpAgent } from "@ag-ui/client";
import {
  CopilotRuntime,
  ExperimentalEmptyAdapter,
  copilotRuntimeNextJSAppRouterEndpoint,
} from "@copilotkit/runtime";
import { NextRequest } from "next/server";

const agentUrl = process.env.ACCOUNT_ASSISTANT_AGUI_URL ?? "http://127.0.0.1:8097/agui";

const copilotRuntime = new CopilotRuntime({
  agents: {
    account_assistant: new HttpAgent({ url: agentUrl }),
  },
});

export async function handleCopilotRequest(req: NextRequest) {
  const url = new URL(req.url);
  if (req.method === "GET" && url.pathname.endsWith("/threads")) {
    return Response.json({ threads: [], nextCursor: null });
  }

  const { handleRequest } = copilotRuntimeNextJSAppRouterEndpoint({
    runtime: copilotRuntime,
    serviceAdapter: new ExperimentalEmptyAdapter(),
    endpoint: "/api/copilotkit",
  });
  return handleRequest(req);
}
