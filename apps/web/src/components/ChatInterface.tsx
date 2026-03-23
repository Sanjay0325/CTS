"use client";

import { useState, useRef, useEffect } from "react";
import ReactMarkdown from "react-markdown";
import { apiPost, apiFetch, apiDelete, getAuthHeaders, getApiUrl } from "@/lib/api";
import { MermaidDiagram } from "./MermaidDiagram";

interface Message {
  id: string;
  role: "user" | "assistant";
  content: string;
}

interface MemoryDebug {
  in_context_messages?: number;
  external_memory_items?: number;
  memory_cache_hit?: boolean;
  tool_cache_hits?: number;
  tools_available?: number;
  tools_used?: string[];
  external_dbs_used?: string[];
  rag_chunks_retrieved?: number;
  ollama_tools_disabled?: string;
}

interface Conversation {
  id: string;
  title: string;
  created_at: string;
  updated_at?: string;
}

interface OllamaModels {
  available: boolean;
  models: { name: string; size?: number; family?: string }[];
  default_model: string | null;
}

interface GraphStep {
  type: string;
  round?: number;
  label?: string;
  name?: string;
  args_preview?: string;
  args_label?: string;
  result_preview?: string;
}

interface MessageTrace {
  prompt_trace?: {
    system_prompt_preview?: string;
    rag_chunks?: number;
    memory_items?: number;
    tools_available?: number;
    memory_cache_hit?: boolean;
    graph_steps?: GraphStep[];
    mermaid?: string;
  };
  model_used?: string;
  tools_used?: string[];
  external_dbs_used?: string[];
  in_context_count?: number;
}

export function ChatInterface({ onOpenSettings }: { onOpenSettings?: () => void }) {
  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const [conversationId, setConversationId] = useState<string | null>(null);
  const [profileId, setProfileId] = useState<string | null>(null);
  const [profiles, setProfiles] = useState<{ id: string; display_name: string }[]>([]);
  const [conversations, setConversations] = useState<Conversation[]>([]);
  const [memoryDebug, setMemoryDebug] = useState<MemoryDebug | null>(null);
  const [showDebug, setShowDebug] = useState(true);
  const [saveToMemory, setSaveToMemory] = useState(false);
  const [selectedCollections, setSelectedCollections] = useState<string[]>([]);
  const [collections, setCollections] = useState<{ id: string; name: string }[]>([]);
  const [rateLimitError, setRateLimitError] = useState<{ message: string; retryAfter: number } | null>(null);
  const [ollama, setOllama] = useState<OllamaModels | null>(null);
  const [traceForMessage, setTraceForMessage] = useState<string | null>(null);
  const [traceData, setTraceData] = useState<MessageTrace | null>(null);
  const [toolStatus, setToolStatus] = useState<string | null>(null);
  const [loadingProfiles, setLoadingProfiles] = useState(true);
  const [loadingConversations, setLoadingConversations] = useState(true);
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLTextAreaElement>(null);

  useEffect(() => {
    if (!rateLimitError?.retryAfter || rateLimitError.retryAfter <= 0) return;
    const t = setInterval(() => {
      setRateLimitError((prev) => {
        if (!prev || prev.retryAfter <= 0) return null;
        const next = prev.retryAfter - 1;
        return next <= 0 ? null : { ...prev, retryAfter: next };
      });
    }, 1000);
    return () => clearInterval(t);
  }, [rateLimitError?.retryAfter]);

  useEffect(() => {
    loadProfiles();
    loadOllama();
    loadConversations();
    loadCollections();
  }, []);

  useEffect(() => {
    if (conversationId) {
      loadMessages(conversationId);
    } else {
      setMessages([]);
    }
  }, [conversationId]);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  async function loadProfiles() {
    setLoadingProfiles(true);
    try {
      const data = await apiFetch<{ id: string; display_name: string }[]>("/profiles");
      setProfiles(data);
    } catch {
      setProfiles([]);
    } finally {
      setLoadingProfiles(false);
    }
  }

  async function loadOllama() {
    try {
      const data = await apiFetch<OllamaModels>("/ollama/models");
      setOllama(data);
    } catch {
      setOllama(null);
    }
  }

  // Set default model only when none selected; never overwrite user's choice
  useEffect(() => {
    if (profileId) return; // User has a selection - respect it
    if (ollama?.available && ollama.default_model) {
      setProfileId(`ollama:${ollama.default_model}`);
    } else if (profiles.length > 0) {
      setProfileId(profiles[0].id);
    }
  }, [ollama?.available, ollama?.default_model, profiles, profileId]);

  async function loadConversations() {
    setLoadingConversations(true);
    try {
      const data = await apiFetch<Conversation[]>("/conversations");
      setConversations(data);
    } catch {
      setConversations([]);
    } finally {
      setLoadingConversations(false);
    }
  }

  async function loadCollections() {
    try {
      const data = await apiFetch<{ id: string; name: string }[]>("/documents/collections");
      setCollections(data);
    } catch {
      setCollections([]);
    }
  }

  async function fetchTrace(msgId: string) {
    if (traceForMessage === msgId) {
      setTraceForMessage(null);
      setTraceData(null);
      return;
    }
    if (!conversationId) return;
    try {
      const t = await apiFetch<MessageTrace>(
        `/conversations/${conversationId}/messages/${msgId}/trace`
      );
      setTraceData(t);
      setTraceForMessage(msgId);
    } catch {
      setTraceData(null);
      setTraceForMessage(null);
    }
  }

  async function loadMessages(convId: string) {
    try {
      const data = await apiFetch<{ id: string; role: string; content: string }[]>(
        `/conversations/${convId}/messages`
      );
      setMessages(
        data.map((m) => ({
          id: m.id,
          role: m.role as "user" | "assistant",
          content: m.content,
        }))
      );
    } catch {
      setMessages([]);
    }
  }

  function startNewChat() {
    setConversationId(null);
    setMessages([]);
    setMemoryDebug(null);
  }

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    const trimmed = input.trim();
    if (!trimmed || loading) return;

    const userMessage: Message = {
      id: crypto.randomUUID(),
      role: "user",
      content: trimmed,
    };
    setMessages((prev) => [...prev, userMessage]);
    setInput("");
    setLoading(true);
    setMemoryDebug(null);
    setToolStatus(null);

    const assistantId = crypto.randomUUID();
    setMessages((prev) => [...prev, { id: assistantId, role: "assistant", content: "" }]);

    try {
      const headers = await getAuthHeaders();
      const body: Record<string, unknown> = {
        message: trimmed,
        conversation_id: conversationId,
        save_to_memory: saveToMemory,
        memory_kind: "fact",
        collection_ids: selectedCollections.length > 0 ? selectedCollections : undefined,
      };
      if (profileId?.startsWith("ollama:")) {
        body.ollama_model = profileId.slice(7);
        body.profile_id = null;
      } else {
        body.profile_id = profileId;
      }
      const apiBase = getApiUrl();
      let res = await fetch(`${apiBase}/chat/stream`, {
        method: "POST",
        headers: { ...headers, "Content-Type": "application/json" },
        body: JSON.stringify(body),
      });

      // Fallback: if proxy returns 503, retry with direct API (CORS permitted)
      if (!res.ok && res.status === 503 && apiBase === "/api/proxy") {
        const directUrl = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";
        if (directUrl && directUrl.startsWith("http")) {
          res = await fetch(`${directUrl}/chat/stream`, {
            method: "POST",
            headers: { ...headers, "Content-Type": "application/json" } as HeadersInit,
            body: JSON.stringify(body),
          });
        }
      }

      if (!res.ok) {
        let msg: string;
        try {
          const raw = await res.text();
          const parsed = raw ? JSON.parse(raw) : {};
          msg = parsed.detail || raw || `HTTP ${res.status}`;
        } catch {
          msg = `HTTP ${res.status}`;
        }
        if (res.status === 503) {
          throw new Error(
            msg.includes("unavailable") || msg.includes("timed out")
              ? msg
              : "API server unavailable. Start: cd services/api && uvicorn src.main:app --reload --port 8000"
          );
        }
        throw new Error(msg);
      }

      const reader = res.body?.getReader();
      const decoder = new TextDecoder();
      let buffer = "";
      let fullContent = "";
      let streamError: Error | null = null;

      if (reader) {
        try {
          while (true) {
            const { done, value } = await reader.read();
            if (done) break;
            if (value) {
              buffer += decoder.decode(value, { stream: true });
              const lines = buffer.split("\n");
              buffer = lines.pop() || "";

              for (const line of lines) {
                if (line.startsWith("data: ")) {
                  const data = line.slice(6);
                  if (data === "[DONE]") continue;
                  try {
                    const parsed = JSON.parse(data);
                    if (parsed.type === "text") {
                      setToolStatus(null);
                      fullContent += parsed.content;
                      setMessages((prev) =>
                        prev.map((m) =>
                          m.id === assistantId ? { ...m, content: fullContent } : m
                        )
                      );
                    } else if (parsed.type === "tool_start") {
                      setToolStatus(parsed.tool ? `Calling ${parsed.tool}...` : "Calling tool...");
                    } else if (parsed.type === "tool_done") {
                      setToolStatus(null);
                    } else if (parsed.type === "debug") {
                      setMemoryDebug(parsed.memory);
                    } else if (parsed.type === "done") {
                      setToolStatus(null);
                      setConversationId(parsed.conversation_id);
                      loadConversations();
                      loadMessages(parsed.conversation_id);
                    } else if (parsed.type === "error") {
                      setToolStatus(null);
                      setMessages((prev) =>
                        prev.filter((m) => m.id !== userMessage.id && m.id !== assistantId)
                      );
                      setInput(userMessage.content);
                      setRateLimitError({
                        message: parsed.content || "An error occurred.",
                        retryAfter: 0,  // Never block - user can switch model and retry immediately
                      });
                      return;
                    }
                  } catch {
                    // Skip invalid JSON
                  }
                }
              }
            }
          }
        } catch (e) {
          streamError = e instanceof Error ? e : new Error(String(e));
        } finally {
          try {
            reader.releaseLock();
          } catch {
            // Ignore
          }
        }
      }

      if (streamError) {
        const msg = streamError.message;
        const isTimeout = /timeout|aborted|TimeoutError/i.test(msg);
        throw new Error(
          isTimeout
            ? "Stream timed out. Try a shorter message or ensure the backend is running."
            : `Stream error: ${msg}`
        );
      }
    } catch (err) {
      setToolStatus(null);
      setMessages((prev) =>
        prev.filter((m) => m.id !== userMessage.id && m.id !== assistantId)
      );
      setInput(userMessage.content);
      const msg = err instanceof Error ? err.message : String(err);
      if (msg.includes("429") || /rate limit|quota/i.test(msg)) {
        setRateLimitError({ message: msg, retryAfter: 0 });  // Show error but don't block
      } else if (
        msg.includes("unavailable") ||
        msg.includes("503") ||
        msg.includes("timed out") ||
        msg.includes("Stream error")
      ) {
        setRateLimitError({
          message: msg,
          retryAfter: 0,
        });
      } else {
        setRateLimitError({ message: msg, retryAfter: 0 });
      }
    } finally {
      setLoading(false);
      setToolStatus(null);
    }
  }

  return (
    <div className="flex flex-1 min-h-0">
      {/* Sidebar - Chat History */}
      <aside className="w-56 border-r border-[var(--border)] flex flex-col bg-[var(--bg-secondary)]">
        <button
          onClick={startNewChat}
          className="m-3 px-3 py-2 rounded-lg bg-[var(--accent)] hover:bg-[var(--accent-hover)] text-sm font-medium"
        >
          + New Chat
        </button>
        <div className="flex-1 overflow-y-auto p-2">
          {loadingConversations ? (
            <div className="px-3 py-2 text-xs text-[var(--text-secondary)] animate-pulse">Loading chats...</div>
          ) : (
            conversations.map((c) => (
              <div
                key={c.id}
                className={`group flex items-center gap-1 mb-1 rounded-lg ${
                  conversationId === c.id ? "bg-[var(--accent)]" : "hover:bg-[var(--bg-tertiary)]"
                }`}
              >
                <button
                  onClick={() => setConversationId(c.id)}
                  className={`flex-1 min-w-0 text-left px-3 py-2 truncate text-sm transition-colors ${
                    conversationId === c.id ? "text-white" : ""
                  }`}
                  title={c.title}
                >
                  {c.title || "New conversation"}
                </button>
                <button
                  onClick={async (e) => {
                    e.stopPropagation();
                    if (!confirm("Delete this chat and all messages?")) return;
                    try {
                      await apiDelete(`/conversations/${c.id}`);
                      if (conversationId === c.id) {
                        setConversationId(null);
                        setMessages([]);
                      }
                      loadConversations();
                    } catch {
                      alert("Failed to delete");
                    }
                  }}
                  className={`opacity-0 group-hover:opacity-100 p-1.5 rounded text-xs transition-opacity ${
                    conversationId === c.id ? "text-white/80 hover:bg-white/20" : "text-[var(--text-secondary)] hover:bg-red-500/20 hover:text-red-400"
                  }`}
                  title="Delete chat"
                >
                  ✕
                </button>
              </div>
            ))
          )}
        </div>
      </aside>

      {/* Main Chat */}
      <div className="flex flex-col flex-1 min-w-0">
        <div className="flex-1 overflow-y-auto p-4 space-y-4">
          {messages.length === 0 && profiles.length === 0 && !ollama?.available && onOpenSettings && (
            <div className="text-center py-12 px-6 mx-auto max-w-md rounded-xl border-2 border-dashed border-[var(--accent)] bg-[var(--bg-tertiary)]/50">
              <p className="text-lg font-medium mb-2">Add your first API key</p>
              <p className="text-sm text-[var(--text-secondary)] mb-4">
                CTS works with OpenAI, Groq, Gemini, OpenRouter, Qwen, Kimi & more. Add a provider below to start chatting.
              </p>
              <button
                onClick={onOpenSettings}
                className="px-6 py-3 rounded-lg bg-[var(--accent)] hover:bg-[var(--accent-hover)] font-medium"
              >
                Add API Key →
              </button>
            </div>
          )}
          {messages.length === 0 && (profiles.length > 0 || ollama?.available || !onOpenSettings) && (
            <div className="text-center py-12 text-[var(--text-secondary)]">
              <p className="text-lg mb-2">Start a conversation</p>
              <p className="text-sm">Select a model and type a message. Use RAG by selecting document collections below.</p>
            </div>
          )}
          {messages.map((m) => (
            <div
              key={m.id}
              className={`group flex ${m.role === "user" ? "justify-end" : "justify-start"} items-start gap-1`}
            >
              <div
                className={`max-w-[80%] rounded-xl px-4 py-2 ${
                  m.role === "user"
                    ? "bg-[var(--accent)] text-white"
                    : "bg-[var(--bg-tertiary)] border border-[var(--border)]"
                }`}
              >
                {m.role === "assistant" ? (
                  <div>
                    <div className="[&_pre]:bg-[var(--bg-primary)] [&_pre]:rounded [&_pre]:p-2 [&_pre]:overflow-x-auto [&_pre]:my-2 [&_code]:bg-[var(--bg-primary)] [&_code]:px-1 [&_code]:rounded [&_code]:text-[var(--accent)] [&_p]:my-1 [&_ul]:list-disc [&_ul]:ml-4 [&_ol]:list-decimal [&_ol]:ml-4">
                      <ReactMarkdown key={m.id}>
                        {m.content || (loading && m.id === messages[messages.length - 1]?.id ? "..." : "")}
                      </ReactMarkdown>
                    </div>
                    {loading && m.id === messages[messages.length - 1]?.id && (toolStatus || (!m.content && !toolStatus)) && (
                      <div className="mt-2 flex items-center gap-2 text-xs text-[var(--text-secondary)] animate-pulse">
                        <span className="inline-block w-2 h-2 rounded-full bg-[var(--accent)] animate-pulse" />
                        {toolStatus || "Thinking..."}
                      </div>
                    )}
                    <div className="mt-2 flex items-center gap-2">
                      {conversationId && (
                        <button
                          onClick={() => fetchTrace(m.id)}
                          className="text-xs text-[var(--text-secondary)] hover:text-[var(--accent)]"
                        >
                          {traceForMessage === m.id ? "Hide trace" : "View trace"}
                        </button>
                      )}
                      {conversationId && (
                        <button
                          onClick={async () => {
                            if (!confirm("Delete this message? It will be removed from context for future replies.")) return;
                            try {
                              await apiDelete(`/conversations/${conversationId}/messages/${m.id}`);
                              loadMessages(conversationId);
                              if (traceForMessage === m.id) setTraceForMessage(null);
                            } catch { alert("Failed to delete"); }
                          }}
                          className="text-xs text-[var(--text-secondary)] hover:text-red-400 opacity-0 group-hover:opacity-100 transition-opacity"
                          title="Delete message"
                        >
                          Delete
                        </button>
                      )}
                    </div>
                    {traceForMessage === m.id && traceData && (
                      <div className="mt-2 p-3 rounded bg-[var(--bg-primary)] border border-[var(--border)] text-xs">
                        <p className="font-medium mb-2">Prompt trace</p>
                        <div className="space-y-1 text-[var(--text-secondary)]">
                          {!traceData.model_used && !traceData.prompt_trace && (traceData.tools_used?.length ?? 0) === 0 && (
                            <div className="italic">No trace data (message may predate tracing)</div>
                          )}
                          {traceData.model_used && (
                            <div><span className="text-[var(--accent)]">Model:</span> {traceData.model_used}</div>
                          )}
                          {traceData.in_context_count != null && (
                            <div><span className="text-[var(--accent)]">In-context:</span> {traceData.in_context_count} msgs</div>
                          )}
                          {traceData.prompt_trace && (
                            <>
                              {traceData.prompt_trace.rag_chunks != null && traceData.prompt_trace.rag_chunks > 0 && (
                                <div><span className="text-[var(--accent)]">RAG chunks:</span> {traceData.prompt_trace.rag_chunks}</div>
                              )}
                              {traceData.prompt_trace.memory_items != null && traceData.prompt_trace.memory_items > 0 && (
                                <div><span className="text-[var(--accent)]">Memory items:</span> {traceData.prompt_trace.memory_items}</div>
                              )}
                              {traceData.prompt_trace.tools_available != null && (
                                <div><span className="text-[var(--accent)]">Tools available:</span> {traceData.prompt_trace.tools_available}</div>
                              )}
                            </>
                          )}
                          {(traceData.tools_used?.length ?? 0) > 0 && (
                            <div><span className="text-[var(--accent)]">Tools used:</span> {traceData.tools_used!.join(", ")}</div>
                          )}
                          {(traceData.external_dbs_used?.length ?? 0) > 0 && (
                            <div><span className="text-[var(--accent)]">RAG DBs:</span> {traceData.external_dbs_used!.join(", ")}</div>
                          )}
                          {traceData.prompt_trace?.system_prompt_preview && (
                            <details className="mt-2">
                              <summary className="cursor-pointer">System prompt preview</summary>
                              <pre className="mt-1 p-2 rounded bg-[var(--bg-tertiary)] overflow-x-auto whitespace-pre-wrap break-words max-h-40 overflow-y-auto">
                                {traceData.prompt_trace.system_prompt_preview}
                              </pre>
                            </details>
                          )}
                          {traceData.prompt_trace?.graph_steps && traceData.prompt_trace.graph_steps.length > 0 && (
                            <div className="mt-3">
                              <p className="font-medium mb-1">Execution flow</p>
                              <div className="space-y-2">
                                {traceData.prompt_trace.graph_steps.map((step, i) => (
                                  <div
                                    key={i}
                                    className={`p-2 rounded border ${
                                      step.type === "agent"
                                        ? "border-[var(--accent)]/50 bg-[var(--accent)]/10"
                                        : "border-[var(--border)] bg-[var(--bg-tertiary)]"
                                    }`}
                                  >
                                    <span className="font-medium">
                                      {step.type === "agent" ? "🔄 " : "🔧 "}
                                      {step.type === "tool" && step.args_label
                                        ? `${step.name}(${step.args_label})`
                                        : (step.label || step.name || step.type)}
                                    </span>
                                    {step.args_preview && (
                                      <div className="mt-1 text-[var(--text-secondary)] text-[10px]">
                                        Args: {step.args_preview}
                                      </div>
                                    )}
                                    {step.result_preview && (
                                      <div className="mt-1 text-[var(--text-secondary)] text-[10px] truncate max-w-full" title={step.result_preview}>
                                        Result: {step.result_preview}
                                      </div>
                                    )}
                                  </div>
                                ))}
                                {traceData.prompt_trace?.mermaid && (
                                  <details className="mt-2">
                                    <summary className="cursor-pointer">View flowchart (Mermaid)</summary>
                                    <div className="mt-2 p-2 rounded bg-[var(--bg-tertiary)]">
                                      <MermaidDiagram code={traceData.prompt_trace.mermaid} className="min-h-[100px]" />
                                    </div>
                                    <a
                                      href="https://mermaid.live/"
                                      target="_blank"
                                      rel="noopener noreferrer"
                                      className="text-[var(--accent)] text-[10px] mt-1 inline-block"
                                    >
                                      Open in Mermaid Live Editor →
                                    </a>
                                  </details>
                                )}
                              </div>
                            </div>
                          )}
                        </div>
                      </div>
                    )}
                  </div>
                ) : (
                  <div>
                    <p className="whitespace-pre-wrap">{m.content || (loading ? "..." : "")}</p>
                    {conversationId && (
                      <button
                        onClick={async () => {
                          if (!confirm("Delete this message? It will be removed from context for future replies.")) return;
                          try {
                            await apiDelete(`/conversations/${conversationId}/messages/${m.id}`);
                            loadMessages(conversationId);
                          } catch { alert("Failed to delete"); }
                        }}
                        className="mt-1 text-xs text-[var(--text-secondary)] hover:text-red-400 opacity-0 group-hover:opacity-100 transition-opacity"
                        title="Delete message"
                      >
                        Delete
                      </button>
                    )}
                  </div>
                )}
              </div>
            </div>
          ))}
          <div ref={messagesEndRef} />
        </div>

        {/* Memory indicators - clearly distinguishable */}
        {memoryDebug && showDebug && (
          <div className="mx-4 mb-2 p-3 rounded-lg bg-[var(--bg-tertiary)] border border-[var(--border)] text-xs">
            <p className="font-medium mb-2">Memory Used (This Response)</p>
            <div className="grid grid-cols-2 gap-2 text-[var(--text-secondary)]">
              <div>
                <span className="text-[var(--accent)]">In-Context:</span> {memoryDebug.in_context_messages ?? 0} messages
              </div>
              <div>
                <span className="text-[var(--accent)]">External Memory:</span> {memoryDebug.external_memory_items ?? 0} items
              </div>
              <div>
                <span className="text-[var(--accent)]">In-Cache Hit:</span> {memoryDebug.memory_cache_hit ? "Yes" : "No"}
              </div>
              <div>
                <span className="text-[var(--accent)]">Tools Available:</span> {memoryDebug.tools_available ?? 0}
              </div>
              <div>
                <span className="text-[var(--accent)]">Tools Used:</span>{" "}
                {(memoryDebug.tools_used?.length ?? 0) > 0 ? memoryDebug.tools_used.join(", ") : "0"}
              </div>
              {(memoryDebug.external_dbs_used?.length ?? 0) > 0 && (
                <div className="col-span-2">
                  <span className="text-[var(--accent)]">RAG DBs Used:</span> {memoryDebug.external_dbs_used?.join(", ")}
                </div>
              )}
              {(memoryDebug.rag_chunks_retrieved ?? 0) > 0 && (
                <div>
                  <span className="text-[var(--accent)]">RAG Chunks:</span> {memoryDebug.rag_chunks_retrieved}
                </div>
              )}
              {memoryDebug.ollama_tools_disabled && (
                <div className="col-span-2 text-amber-500">
                  {memoryDebug.ollama_tools_disabled}
                </div>
              )}
            </div>
          </div>
        )}

        <div className="p-4 border-t border-[var(--border)]">
          {rateLimitError && (
            <div className="mb-3 px-4 py-2 rounded-lg bg-amber-500/20 border border-amber-500/50 text-amber-700 dark:text-amber-300 text-sm">
              <p className="font-medium">
                {rateLimitError.retryAfter > 0 ? "Rate limited" : "Error"}
              </p>
              <p className="mt-1 opacity-90">
                {rateLimitError.retryAfter > 0
                  ? `Retry in ${rateLimitError.retryAfter}s — ${rateLimitError.message.slice(0, 80)}${rateLimitError.message.length > 80 ? "…" : ""}`
                  : rateLimitError.message}
              </p>
              {rateLimitError.retryAfter <= 0 && (
                <button
                  onClick={() => setRateLimitError(null)}
                  className="mt-2 text-xs underline"
                >
                  Dismiss
                </button>
              )}
            </div>
          )}
            <div className="flex flex-wrap items-center gap-2 mb-2">
            <select
              value={profileId || ""}
              onChange={(e) => setProfileId(e.target.value || null)}
              disabled={loadingProfiles}
              className="px-3 py-1.5 rounded-lg bg-[var(--bg-tertiary)] border border-[var(--border)] text-sm disabled:opacity-70 min-w-[180px]"
            >
              <option value="">{loadingProfiles ? "Loading..." : "Select model"}</option>
              {ollama?.available && ollama.models.length > 0 && (
                <optgroup label={`Ollama (${ollama.models.length} local)`}>
                  {ollama.models.map((m) => (
                    <option key={m.name} value={`ollama:${m.name}`}>
                      {m.name}{m.family ? ` · ${m.family}` : ""}
                    </option>
                  ))}
                </optgroup>
              )}
              {profiles.length > 0 && (
                <optgroup label="API profiles">
                  {profiles.map((p) => (
                    <option key={p.id} value={p.id}>
                      {p.display_name}
                    </option>
                  ))}
                </optgroup>
              )}
            </select>
            {ollama?.available && (
              <button
                type="button"
                onClick={() => loadOllama()}
                className="text-xs text-[var(--text-secondary)] hover:text-[var(--accent)] px-1"
                title="Refresh Ollama models"
              >
                ↻
              </button>
            )}
            <div className="flex items-center gap-2" title="Select RAG collections to search for this message">
              <span className="text-xs text-[var(--text-secondary)]">RAG:</span>
              {collections.map((c) => (
                <label key={c.id} className="flex items-center gap-1 text-xs cursor-pointer">
                  <input
                    type="checkbox"
                    checked={selectedCollections.includes(c.id)}
                    onChange={(e) => {
                      if (e.target.checked) setSelectedCollections((prev) => [...prev, c.id]);
                      else setSelectedCollections((prev) => prev.filter((id) => id !== c.id));
                    }}
                  />
                  {c.name}
                </label>
              ))}
            </div>
            <label className="flex items-center gap-1 text-sm text-[var(--text-secondary)]">
              <input
                type="checkbox"
                checked={saveToMemory}
                onChange={(e) => setSaveToMemory(e.target.checked)}
              />
              Save to memory
            </label>
            <button
              onClick={() => setShowDebug(!showDebug)}
              className="ml-auto text-sm text-[var(--text-secondary)] hover:text-[var(--accent)]"
            >
              {showDebug ? "Hide" : "Show"} Memory
            </button>
          </div>

          <form onSubmit={handleSubmit} className="flex gap-2">
            <textarea
              ref={inputRef}
              value={input}
              onChange={(e) => setInput(e.target.value)}
              onKeyDown={(e) => {
                if (e.key === "Enter" && !e.shiftKey) {
                  e.preventDefault();
                  handleSubmit(e);
                }
              }}
              placeholder="Type a message..."
              rows={1}
              className="flex-1 resize-none rounded-xl px-4 py-3 bg-[var(--bg-tertiary)] border border-[var(--border)] focus:outline-none focus:ring-2 focus:ring-[var(--accent)]"
              disabled={loading}
            />
            <button
              type="submit"
              disabled={loading || !input.trim()}
              className="px-4 py-2 rounded-xl bg-[var(--accent)] hover:bg-[var(--accent-hover)] disabled:opacity-50 transition-colors"
            >
              Send
            </button>
          </form>
        </div>
      </div>
    </div>
  );
}
