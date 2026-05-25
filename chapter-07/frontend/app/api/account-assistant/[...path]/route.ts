import { NextRequest } from "next/server";

export const runtime = "nodejs";
export const dynamic = "force-dynamic";

const backendUrl = process.env.ACCOUNT_ASSISTANT_API_URL ?? "http://127.0.0.1:8097";

type RouteContext = {
  params: Promise<{ path: string[] }>;
};

async function proxyAccountAssistant(req: NextRequest, context: RouteContext) {
  const { path } = await context.params;
  const url = new URL(path.join("/"), `${backendUrl.replace(/\/$/, "")}/`);
  req.nextUrl.searchParams.forEach((value, key) => {
    url.searchParams.set(key, value);
  });

  const headers = new Headers();
  const contentType = req.headers.get("content-type");
  if (contentType) {
    headers.set("content-type", contentType);
  }

  const response = await fetch(url, {
    method: req.method,
    headers,
    body: req.method === "GET" || req.method === "HEAD" ? undefined : await req.text(),
    cache: "no-store",
  });

  return new Response(response.body, {
    status: response.status,
    headers: {
      "content-type": response.headers.get("content-type") ?? "application/json",
    },
  });
}

export const GET = proxyAccountAssistant;
export const POST = proxyAccountAssistant;
export const PATCH = proxyAccountAssistant;
export const DELETE = proxyAccountAssistant;
