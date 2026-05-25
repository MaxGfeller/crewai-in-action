import { handleCopilotRequest } from "../handler";

export const runtime = "nodejs";
export const dynamic = "force-dynamic";

export const GET = handleCopilotRequest;
export const POST = handleCopilotRequest;
