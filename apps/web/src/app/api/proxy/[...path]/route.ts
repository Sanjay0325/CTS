import { NextRequest, NextResponse } from "next/server";

const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

/** Allow long-running streams (chat can take 10+ min with tools) */
export const maxDuration = 600;

/** Paths that stream indefinitely - no timeout (chat can take 5+ min with tools) */
const STREAMING_PATHS = ["chat/stream"];

/** Default timeout for non-streaming requests (seconds) */
const DEFAULT_TIMEOUT_MS = 90_000;

type Params = { path: string[] };

function isStreamingPath(pathStr: string): boolean {
  return STREAMING_PATHS.some((p) => pathStr === p || pathStr.startsWith(p + "/"));
}

export async function GET(
  request: NextRequest,
  ctx: { params: Params | Promise<Params> }
) {
  const params = await Promise.resolve(ctx.params);
  return proxyRequest(request, params);
}

export async function POST(
  request: NextRequest,
  ctx: { params: Params | Promise<Params> }
) {
  const params = await Promise.resolve(ctx.params);
  return proxyRequest(request, params);
}

export async function PUT(
  request: NextRequest,
  ctx: { params: Params | Promise<Params> }
) {
  const params = await Promise.resolve(ctx.params);
  return proxyRequest(request, params);
}

export async function DELETE(
  request: NextRequest,
  ctx: { params: Params | Promise<Params> }
) {
  const params = await Promise.resolve(ctx.params);
  return proxyRequest(request, params);
}

export async function PATCH(
  request: NextRequest,
  ctx: { params: Params | Promise<Params> }
) {
  const params = await Promise.resolve(ctx.params);
  return proxyRequest(request, params);
}

async function proxyRequest(request: NextRequest, { path }: Params) {
  const pathStr = path?.join("/") || "";
  const url = `${API_BASE.replace(/\/$/, "")}/${pathStr}`;
  const search = request.nextUrl.searchParams.toString();
  const fullUrl = search ? `${url}?${search}` : url;

  const headers = new Headers(request.headers);
  headers.delete("host");
  headers.delete("connection");

  const isStreaming = isStreamingPath(pathStr);
  const timeoutMs = isStreaming ? 0 : DEFAULT_TIMEOUT_MS;

  const fetchOpts: RequestInit = {
    method: request.method,
    headers,
  };
  if (timeoutMs > 0) {
    fetchOpts.signal = AbortSignal.timeout(timeoutMs);
  }

  if (request.method !== "GET" && request.body) {
    const contentType = request.headers.get("content-type") || "";
    if (contentType.includes("application/json")) {
      try {
        fetchOpts.body = await request.text();
      } catch {
        fetchOpts.body = request.body;
      }
    } else {
      fetchOpts.body = request.body;
    }
  }

  try {
    const res = await fetch(fullUrl, fetchOpts);

    const contentType = res.headers.get("content-type") || "";
    const isJson = contentType.includes("application/json");
    const isStream =
      contentType.includes("text/event-stream") ||
      res.headers.get("transfer-encoding") === "chunked";

    if (isStream) {
      return new NextResponse(res.body, {
        status: res.status,
        headers: {
          "content-type": contentType,
          "cache-control": "no-cache",
          connection: "keep-alive",
        },
      });
    }

    const text = await res.text();
    if (isJson && text) {
      try {
        return NextResponse.json(JSON.parse(text), { status: res.status });
      } catch {
        return new NextResponse(text, { status: res.status });
      }
    }
    return new NextResponse(text, {
      status: res.status,
      headers: { "content-type": contentType },
    });
  } catch (err) {
    const msg = err instanceof Error ? err.message : String(err);
    const isTimeout = /timeout|aborted|TIMEOUT/i.test(msg);
    const isConnectionError =
      /ECONNRESET|ECONNREFUSED|socket hang up|fetch failed/i.test(msg);
    const detail = isTimeout
      ? "Request timed out. Try a shorter message or check backend."
      : isConnectionError
      ? "API server unavailable. Start: cd services/api && uvicorn src.main:app --reload --port 8000"
      : msg;
    return NextResponse.json({ detail }, { status: 503 });
  }
}
