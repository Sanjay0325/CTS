"use client";

import { useState, useEffect } from "react";
import { apiPost, apiDelete, apiFetch, getAuthHeaders, getApiUrl } from "@/lib/api";

interface ModelProfile {
  id: string;
  display_name: string;
  provider_base_url: string;
  api_style: string;
  model_name: string;
  model_version?: string;
}

interface MCPServer {
  id: string;
  name: string;
  server_url: string;
  transport: string;
}

interface MCPTool {
  name: string;
  description?: string;
}

interface MCPResource {
  uri: string;
  name?: string;
  description?: string;
}

interface MCPPrompt {
  name: string;
  description?: string;
}

interface AvailableMCPServer {
  name: string;
  server_url: string;
  description: string;
}

function formatRelativeTime(iso: string): string {
  try {
    const d = new Date(iso);
    const sec = Math.floor((Date.now() - d.getTime()) / 1000);
    if (sec < 60) return "just now";
    if (sec < 3600) return `${Math.floor(sec / 60)}m ago`;
    if (sec < 86400) return `${Math.floor(sec / 3600)}h ago`;
    if (sec < 604800) return `${Math.floor(sec / 86400)}d ago`;
    return d.toLocaleDateString();
  } catch {
    return "";
  }
}

/** Universal provider presets - like USB ports for any LLM API */
const PROVIDER_PRESETS: Record<string, { url: string; model: string; style: string; keyUrl?: string }> = {
  openai: {
    url: "https://api.openai.com",
    model: "gpt-4o-mini",
    style: "openai",
    keyUrl: "https://platform.openai.com/api-keys",
  },
  gemini: {
    url: "https://generativelanguage.googleapis.com/v1beta",
    model: "gemini-2.0-flash",
    style: "gemini",
    keyUrl: "https://aistudio.google.com/apikey",
  },
  groq: {
    url: "https://api.groq.com/openai",
    model: "llama-3.1-70b-versatile",
    style: "openai",
    keyUrl: "https://console.groq.com/keys",
  },
  grok: {
    url: "https://api.groq.com/openai",
    model: "openai/gpt-oss-120b",
    style: "openai",
    keyUrl: "https://console.groq.com/keys",
  },
  openrouter: {
    url: "https://openrouter.ai/api",
    model: "openai/gpt-4o-mini",
    style: "openai",
    keyUrl: "https://openrouter.ai/keys",
  },
  together: {
    url: "https://api.together.xyz",
    model: "meta-llama/Llama-3.2-3B-Instruct-Turbo",
    style: "openai",
    keyUrl: "https://api.together.xyz/settings/api-keys",
  },
  fireworks: {
    url: "https://api.fireworks.ai/inference",
    model: "accounts/fireworks/models/llama-v3p3-70b-instruct",
    style: "openai",
    keyUrl: "https://fireworks.ai/dashboard",
  },
  anthropic: {
    url: "https://openrouter.ai/api",
    model: "anthropic/claude-3.5-sonnet",
    style: "openai",
    keyUrl: "https://openrouter.ai/keys",
  },
  qwen: {
    url: "https://openrouter.ai/api",
    model: "qwen/qwen-2.5-72b-instruct",
    style: "openai",
    keyUrl: "https://openrouter.ai/keys",
  },
  kimi: {
    url: "https://openrouter.ai/api",
    model: "moonshotai/kimi-k2",
    style: "openai",
    keyUrl: "https://openrouter.ai/keys",
  },
  custom: {
    url: "",
    model: "",
    style: "openai",
  },
};

export function SettingsPanel({ onClose }: { onClose: () => void }) {
  const [profiles, setProfiles] = useState<ModelProfile[]>([]);
  const [servers, setServers] = useState<MCPServer[]>([]);
  const [activeTab, setActiveTab] = useState<"models" | "mcp" | "documents" | "data">("models");

  // Documents
  const [collections, setCollections] = useState<{ id: string; name: string; description?: string }[]>([]);
  const [documents, setDocuments] = useState<{ id: string; name: string; collection_id?: string }[]>([]);
  const [collectionName, setCollectionName] = useState("");
  const [collectionDesc, setCollectionDesc] = useState("");
  const [docName, setDocName] = useState("");
  const [docContent, setDocContent] = useState("");
  const [docCollectionId, setDocCollectionId] = useState<string>("");

  // Model form
  const [displayName, setDisplayName] = useState("");
  const [providerUrl, setProviderUrl] = useState("https://api.openai.com");
  const [apiKey, setApiKey] = useState("");
  const [apiStyle, setApiStyle] = useState("openai");
  const [modelName, setModelName] = useState("gpt-4o-mini");
  const [modelVersion, setModelVersion] = useState("");
  const [lastPresetId, setLastPresetId] = useState<string | null>(null);

  // MCP form
  const [serverName, setServerName] = useState("");
  const [serverUrl, setServerUrl] = useState("http://localhost:8002/mcp");
  const [toolsByServer, setToolsByServer] = useState<Record<string, MCPTool[]>>({});
  const [resourcesByServer, setResourcesByServer] = useState<Record<string, MCPResource[]>>({});
  const [promptsByServer, setPromptsByServer] = useState<Record<string, MCPPrompt[]>>({});
  const [availableServers, setAvailableServers] = useState<AvailableMCPServer[]>([]);
  const [addingServer, setAddingServer] = useState<string | null>(null);

  // MCP Data view
  const [dataView, setDataView] = useState<"notes" | "todos" | "reminders" | null>(null);
  const [dataItems, setDataItems] = useState<Record<string, unknown[]>>({ notes: [], todos: [], reminders: [] });
  const [dataStorage, setDataStorage] = useState<string>("");
  const [dataError, setDataError] = useState<string>("");
  const [dataPopup, setDataPopup] = useState<{ type: string; item: Record<string, unknown> } | null>(null);

  useEffect(() => {
    loadProfiles();
    loadServers();
    loadCollections();
  }, []);

  useEffect(() => {
    if (activeTab === "mcp") loadAvailableServers();
  }, [activeTab]);

  async function loadCollections() {
    try {
      const data = await apiFetch<{ id: string; name: string; description?: string }[]>("/documents/collections");
      setCollections(data);
    } catch {
      setCollections([]);
    }
  }

  async function loadDocuments() {
    try {
      const data = await apiFetch<{ id: string; name: string; collection_id?: string }[]>("/documents/documents");
      setDocuments(data);
    } catch {
      setDocuments([]);
    }
  }

  async function loadProfiles() {
    try {
      const headers = await getAuthHeaders();
      const res = await fetch(`${getApiUrl()}/profiles`, { headers });
      if (res.ok) setProfiles(await res.json());
    } catch {
      // Ignore
    }
  }

  async function loadServers() {
    try {
      const headers = await getAuthHeaders();
      const res = await fetch(`${getApiUrl()}/mcp/servers`, { headers });
      if (res.ok) setServers(await res.json());
    } catch {
      // Ignore
    }
  }

  async function loadAvailableServers() {
    try {
      const headers = await getAuthHeaders();
      const res = await fetch(`${getApiUrl()}/mcp/available-servers`, { headers });
      if (res.ok) {
        const data = await res.json();
        setAvailableServers(data.servers || []);
      }
    } catch {
      setAvailableServers([]);
    }
  }

  async function quickAddServer(av: AvailableMCPServer) {
    if (servers.some((s) => s.server_url === av.server_url)) return;
    setAddingServer(av.server_url);
    try {
      await apiPost("/mcp/servers", {
        name: av.name,
        server_url: av.server_url,
        transport: "streamable-http",
      });
      loadServers();
    } catch (err) {
      alert(err instanceof Error ? err.message : "Failed to add server");
    } finally {
      setAddingServer(null);
    }
  }

  async function quickAddAll() {
    const toAdd = availableServers.filter((av) => !servers.some((s) => s.server_url === av.server_url));
    if (toAdd.length === 0) {
      alert("All available servers are already added.");
      return;
    }
    setAddingServer("__all__");
    let added = 0;
    for (const av of toAdd) {
      try {
        await apiPost("/mcp/servers", {
          name: av.name,
          server_url: av.server_url,
          transport: "streamable-http",
        });
        added++;
      } catch {
        // Skip failed
      }
    }
    loadServers();
    setAddingServer(null);
    if (added > 0) alert(`Added ${added} server(s). Start them with: pnpm dev:mcp:all`);
  }

  async function addProfile(e: React.FormEvent) {
    e.preventDefault();
    try {
      await apiPost("/profiles", {
        display_name: displayName,
        provider_base_url: providerUrl,
        api_key: apiKey,
        api_style: apiStyle,
        model_name: modelName,
        model_version: modelVersion || undefined,
      });
      setDisplayName("");
      setProviderUrl("https://api.openai.com");
      setApiKey("");
      setApiStyle("openai");
      setModelName("gpt-4o-mini");
      setModelVersion("");
      setLastPresetId(null);
      loadProfiles();
    } catch (err) {
      alert(err instanceof Error ? err.message : "Failed to add profile");
    }
  }

  function applyPreset(presetId: string) {
    const p = PROVIDER_PRESETS[presetId];
    if (!p) return;
    setLastPresetId(presetId);
    setApiStyle(p.style);
    setProviderUrl(p.url || providerUrl);
    setModelName(p.model || modelName);
    setDisplayName(presetId.charAt(0).toUpperCase() + presetId.slice(1));
  }

  async function deleteProfile(id: string) {
    try {
      await apiDelete(`/profiles/${id}`);
      loadProfiles();
    } catch (err) {
      alert(err instanceof Error ? err.message : "Failed to delete");
    }
  }

  async function setActiveProfile(id: string) {
    try {
      const headers = await getAuthHeaders();
      await fetch(`${getApiUrl()}/conversations/settings/active-profile`, {
        method: "PUT",
        headers: { ...headers, "Content-Type": "application/json" },
        body: JSON.stringify({ profile_id: id }),
      });
    } catch {
      // Ignore
    }
  }

  async function addServer(e: React.FormEvent) {
    e.preventDefault();
    try {
      await apiPost("/mcp/servers", {
        name: serverName,
        server_url: serverUrl,
        transport: "streamable-http",
      });
      setServerName("");
      setServerUrl("http://localhost:8002/mcp");
      loadServers();
    } catch (err) {
      alert(err instanceof Error ? err.message : "Failed to add server");
    }
  }

  async function deleteServer(id: string) {
    try {
      await apiDelete(`/mcp/servers/${id}`);
      loadServers();
      setToolsByServer((prev) => {
        const next = { ...prev };
        delete next[id];
        return next;
      });
    } catch (err) {
      alert(err instanceof Error ? err.message : "Failed to delete");
    }
  }

  async function loadTools(serverId: string) {
    try {
      const headers = await getAuthHeaders();
      const res = await fetch(`${getApiUrl()}/mcp/servers/${serverId}/tools`, { headers });
      if (res.ok) {
        const data = await res.json();
        setToolsByServer((prev) => ({ ...prev, [serverId]: data.tools || [] }));
      } else {
        setToolsByServer((prev) => ({ ...prev, [serverId]: [] }));
      }
    } catch {
      setToolsByServer((prev) => ({ ...prev, [serverId]: [] }));
    }
  }

  async function loadResources(serverId: string) {
    try {
      const headers = await getAuthHeaders();
      const res = await fetch(`${getApiUrl()}/mcp/servers/${serverId}/resources`, { headers });
      if (res.ok) {
        const data = await res.json();
        setResourcesByServer((prev) => ({ ...prev, [serverId]: data.resources || [] }));
      } else {
        setResourcesByServer((prev) => ({ ...prev, [serverId]: [] }));
      }
    } catch {
      setResourcesByServer((prev) => ({ ...prev, [serverId]: [] }));
    }
  }

  async function loadPrompts(serverId: string) {
    try {
      const headers = await getAuthHeaders();
      const res = await fetch(`${getApiUrl()}/mcp/servers/${serverId}/prompts`, { headers });
      if (res.ok) {
        const data = await res.json();
        setPromptsByServer((prev) => ({ ...prev, [serverId]: data.prompts || [] }));
      } else {
        setPromptsByServer((prev) => ({ ...prev, [serverId]: [] }));
      }
    } catch {
      setPromptsByServer((prev) => ({ ...prev, [serverId]: [] }));
    }
  }

  async function loadAllForServer(serverId: string) {
    await Promise.all([loadTools(serverId), loadResources(serverId), loadPrompts(serverId)]);
  }

  async function loadMcpData(type: "notes" | "todos" | "reminders") {
    setDataView(type);
    setDataError("");
    try {
      const headers = await getAuthHeaders();
      const res = await fetch(`${getApiUrl()}/mcp/data/${type}`, { headers });
      const data = await res.json();
      setDataStorage(data.storage || "");
      if (res.ok && data.items) {
        setDataItems((prev) => ({ ...prev, [type]: data.items }));
        setDataError(data.error || "");
      } else {
        setDataItems((prev) => ({ ...prev, [type]: [] }));
        setDataError(data.error || "Failed to load.");
      }
    } catch {
      setDataItems((prev) => ({ ...prev, [type]: [] }));
      setDataError("Failed to load. Ensure MCP server is running.");
    }
  }

  return (
    <div className="w-full max-w-2xl overflow-y-auto p-6 border-l border-[var(--border)] bg-[var(--bg-secondary)]">
      <div className="flex items-center justify-between mb-6">
        <h2 className="text-xl font-semibold">Settings</h2>
        <button
          onClick={onClose}
          className="p-2 rounded-lg hover:bg-[var(--bg-tertiary)] transition-colors"
        >
          ✕
        </button>
      </div>

      <div className="flex gap-2 mb-6">
        <button
          onClick={() => setActiveTab("models")}
          className={`px-4 py-2 rounded-lg transition-colors ${
            activeTab === "models" ? "bg-[var(--accent)]" : "bg-[var(--bg-tertiary)]"
          }`}
        >
          Model Profiles
        </button>
        <button
          onClick={() => setActiveTab("mcp")}
          className={`px-4 py-2 rounded-lg transition-colors ${
            activeTab === "mcp" ? "bg-[var(--accent)]" : "bg-[var(--bg-tertiary)]"
          }`}
        >
          MCP Servers
        </button>
        <button
          onClick={() => { setActiveTab("documents"); loadCollections(); loadDocuments(); }}
          className={`px-4 py-2 rounded-lg transition-colors ${
            activeTab === "documents" ? "bg-[var(--accent)]" : "bg-[var(--bg-tertiary)]"
          }`}
        >
          RAG Documents
        </button>
        <button
          onClick={() => setActiveTab("data")}
          className={`px-4 py-2 rounded-lg transition-colors ${
            activeTab === "data" ? "bg-[var(--accent)]" : "bg-[var(--bg-tertiary)]"
          }`}
        >
          MCP Data
        </button>
      </div>

      {activeTab === "models" && (
        <div className="space-y-6">
          <form onSubmit={addProfile} className="space-y-3 p-4 rounded-lg bg-[var(--bg-tertiary)] border border-[var(--border)]">
            <h3 className="font-medium">Add Model Profile (Universal – any API)</h3>
            <p className="text-xs text-[var(--text-secondary)]">Pick a preset, paste API key, add. Works like a USB port for OpenAI, Groq, OpenRouter, Qwen, Kimi, etc.</p>
            <div className="flex flex-wrap gap-2">
              {Object.keys(PROVIDER_PRESETS)
                .filter((k) => k !== "custom")
                .map((id) => (
                  <button
                    key={id}
                    type="button"
                    onClick={() => applyPreset(id)}
                    className="px-2 py-1 text-xs rounded bg-[var(--bg-primary)] hover:bg-[var(--accent)] transition-colors capitalize"
                  >
                    {id}
                  </button>
                ))}
            </div>
            <input
              type="text"
              placeholder="Display name"
              value={displayName}
              onChange={(e) => setDisplayName(e.target.value)}
              className="w-full px-3 py-2 rounded-lg bg-[var(--bg-primary)] border border-[var(--border)]"
              required
            />
            <input
              type="url"
              placeholder="Provider URL (e.g. https://api.openai.com)"
              value={providerUrl}
              onChange={(e) => setProviderUrl(e.target.value)}
              className="w-full px-3 py-2 rounded-lg bg-[var(--bg-primary)] border border-[var(--border)]"
              required
            />
            <div>
              <input
                type="password"
                placeholder="API Key (paste from provider dashboard)"
                value={apiKey}
                onChange={(e) => setApiKey(e.target.value)}
                className="w-full px-3 py-2 rounded-lg bg-[var(--bg-primary)] border border-[var(--border)]"
                required
              />
              {lastPresetId && PROVIDER_PRESETS[lastPresetId]?.keyUrl && (
                <p className="mt-1 text-xs text-[var(--text-secondary)]">
                  Get key:{" "}
                  <a href={PROVIDER_PRESETS[lastPresetId].keyUrl} target="_blank" rel="noopener noreferrer" className="text-[var(--accent)] underline">
                    {PROVIDER_PRESETS[lastPresetId].keyUrl}
                  </a>
                </p>
              )}
            </div>
            <input
              type="text"
              placeholder="Model name (e.g. gpt-4o-mini)"
              value={modelName}
              onChange={(e) => setModelName(e.target.value)}
              className="w-full px-3 py-2 rounded-lg bg-[var(--bg-primary)] border border-[var(--border)]"
              required
            />
            <input
              type="text"
              placeholder="Model version (optional)"
              value={modelVersion}
              onChange={(e) => setModelVersion(e.target.value)}
              className="w-full px-3 py-2 rounded-lg bg-[var(--bg-primary)] border border-[var(--border)]"
            />
            <button type="submit" className="px-4 py-2 rounded-lg bg-[var(--accent)] hover:bg-[var(--accent-hover)]">
              Add Profile
            </button>
          </form>

          <div>
            <h3 className="font-medium mb-2">Your API Profiles</h3>
            <p className="text-xs text-[var(--text-secondary)] mb-2">Ollama models are local and not stored here.</p>
            <ul className="space-y-2">
              {profiles.map((p) => (
                <li
                  key={p.id}
                  className="flex items-center justify-between p-3 rounded-lg bg-[var(--bg-tertiary)] border border-[var(--border)]"
                >
                  <div>
                    <p className="font-medium">{p.display_name}</p>
                    <p className="text-sm text-[var(--text-secondary)]">{p.model_name}</p>
                  </div>
                  <div className="flex gap-2">
                    <button
                      onClick={() => setActiveProfile(p.id)}
                      className="px-2 py-1 text-xs rounded bg-[var(--accent)]"
                    >
                      Use
                    </button>
                    <button
                      onClick={() => deleteProfile(p.id)}
                      className="px-2 py-1 text-xs rounded bg-red-600/50 hover:bg-red-600/70"
                    >
                      Delete
                    </button>
                  </div>
                </li>
              ))}
            </ul>
          </div>
        </div>
      )}

      {activeTab === "documents" && (
        <div className="space-y-6">
          <form
            onSubmit={async (e) => {
              e.preventDefault();
              try {
                await apiPost("/documents/collections", { name: collectionName, description: collectionDesc });
                setCollectionName("");
                setCollectionDesc("");
                loadCollections();
              } catch (err) {
                alert(err instanceof Error ? err.message : "Failed");
              }
            }}
            className="space-y-3 p-4 rounded-lg bg-[var(--bg-tertiary)] border border-[var(--border)]"
          >
            <h3 className="font-medium">Create Collection (RAG DB)</h3>
            <input
              type="text"
              placeholder="Collection name (e.g. Privacy Policy)"
              value={collectionName}
              onChange={(e) => setCollectionName(e.target.value)}
              className="w-full px-3 py-2 rounded-lg bg-[var(--bg-primary)] border border-[var(--border)]"
              required
            />
            <input
              type="text"
              placeholder="Description (optional)"
              value={collectionDesc}
              onChange={(e) => setCollectionDesc(e.target.value)}
              className="w-full px-3 py-2 rounded-lg bg-[var(--bg-primary)] border border-[var(--border)]"
            />
            <button type="submit" className="px-4 py-2 rounded-lg bg-[var(--accent)]">Create</button>
          </form>
          <div>
            <h3 className="font-medium mb-2">Your Collections</h3>
            <ul className="space-y-2">
              {collections.map((c) => (
                <li key={c.id} className="flex justify-between items-center p-3 rounded-lg bg-[var(--bg-tertiary)]">
                  <span>{c.name}</span>
                  <button onClick={async () => { await apiDelete(`/documents/collections/${c.id}`); loadCollections(); }} className="text-red-500 text-sm">Delete</button>
                </li>
              ))}
            </ul>
          </div>
          <form
            onSubmit={async (e) => {
              e.preventDefault();
              try {
                await apiPost("/documents/documents", { name: docName, content: docContent, collection_id: docCollectionId || undefined });
                setDocName("");
                setDocContent("");
                loadDocuments();
              } catch (err) {
                alert(err instanceof Error ? err.message : "Failed");
              }
            }}
            className="space-y-3 p-4 rounded-lg bg-[var(--bg-tertiary)] border border-[var(--border)]"
          >
            <h3 className="font-medium">Upload Document</h3>
            <input
              type="text"
              placeholder="Document name"
              value={docName}
              onChange={(e) => setDocName(e.target.value)}
              className="w-full px-3 py-2 rounded-lg bg-[var(--bg-primary)] border border-[var(--border)]"
              required
            />
            <select
              value={docCollectionId}
              onChange={(e) => setDocCollectionId(e.target.value)}
              className="w-full px-3 py-2 rounded-lg bg-[var(--bg-primary)] border border-[var(--border)]"
            >
              <option value="">No collection</option>
              {collections.map((c) => (
                <option key={c.id} value={c.id}>{c.name}</option>
              ))}
            </select>
            <textarea
              placeholder="Paste document content (privacy policy, etc.)"
              value={docContent}
              onChange={(e) => setDocContent(e.target.value)}
              rows={6}
              className="w-full px-3 py-2 rounded-lg bg-[var(--bg-primary)] border border-[var(--border)]"
              required
            />
            <button type="submit" className="px-4 py-2 rounded-lg bg-[var(--accent)]">Upload</button>
          </form>
          <div>
            <h3 className="font-medium mb-2">Documents</h3>
            <ul className="space-y-2">
              {documents.map((d) => (
                <li key={d.id} className="flex justify-between items-center p-3 rounded-lg bg-[var(--bg-tertiary)]">
                  <span>{d.name}</span>
                  <button onClick={async () => { await apiDelete(`/documents/documents/${d.id}`); loadDocuments(); }} className="text-red-500 text-sm">Delete</button>
                </li>
              ))}
            </ul>
          </div>
        </div>
      )}

      {activeTab === "data" && (
        <div className="space-y-6">
          <div className="p-4 rounded-lg bg-[var(--bg-tertiary)] border border-[var(--border)]">
            <h3 className="font-medium mb-2">MCP Data (Notes, Todos, Reminders)</h3>
            <p className="text-sm text-[var(--text-secondary)] mb-4">
              View data saved by MCP tools. Click an item to see details. Add Notes/Todo servers in the MCP tab and ensure they are running (ports 8004, 8009).
            </p>
            <div className="flex flex-wrap gap-2 mb-4">
              <button onClick={() => loadMcpData("notes")} className="px-3 py-1.5 text-sm rounded-lg bg-[var(--accent)]">View Notes</button>
              <button onClick={() => loadMcpData("todos")} className="px-3 py-1.5 text-sm rounded-lg bg-[var(--accent)]">View Todos</button>
              <button onClick={() => loadMcpData("reminders")} className="px-3 py-1.5 text-sm rounded-lg bg-[var(--accent)]">View Reminders</button>
            </div>
            {dataError && <p className="text-sm text-amber-500 mb-2">{dataError}</p>}
            {dataStorage && <p className="text-xs text-[var(--text-secondary)]">Stored at: {dataStorage}</p>}
          </div>
          {dataView && (
            <div className="p-4 rounded-lg bg-[var(--bg-tertiary)] border border-[var(--border)]">
              <h3 className="font-medium mb-3">{dataView === "notes" ? "Notes" : dataView === "todos" ? "Todos" : "Reminders"}</h3>
              <ul className="space-y-2">
                {dataView === "notes" &&
                  (dataItems.notes as { id?: string; title?: string; content?: string; created_at?: string }[]).map((n, i) => {
                    const isEmpty = !(n.title || "").trim() && !(n.content || "").trim();
                    const displayTitle = (n.title || n.content || "").trim().slice(0, 50) || "(Empty note)";
                    const timeStr = n.created_at ? formatRelativeTime(n.created_at) : "";
                    return (
                      <li key={n.id ?? i} className="flex items-center gap-2 group">
                        <button
                          onClick={() => setDataPopup({ type: "note", item: n })}
                          className={`flex-1 min-w-0 text-left px-3 py-2 rounded-lg hover:bg-[var(--bg-primary)] truncate ${isEmpty ? "text-amber-500" : ""}`}
                        >
                          <span>{displayTitle}{displayTitle.length >= 50 ? "…" : ""}</span>
                          {timeStr && <span className="block text-xs text-[var(--text-secondary)] mt-0.5">{timeStr}</span>}
                        </button>
                        {n.id && (
                          <button
                            onClick={async (e) => { e.stopPropagation(); if (confirm("Delete this note?")) { try { await apiDelete(`/mcp/data/notes/${n.id}`); loadMcpData("notes"); setDataPopup(null); } catch { alert("Failed to delete"); } } }}
                            className="opacity-0 group-hover:opacity-100 p-1.5 rounded text-red-500 hover:bg-red-500/20 transition-opacity"
                            title="Delete"
                          >
                            ✕
                          </button>
                        )}
                      </li>
                    );
                  })}
                {dataView === "todos" &&
                  (dataItems.todos as { id?: string; task?: string; done?: boolean; created_at?: string }[]).map((t, i) => {
                    const isEmpty = !(t.task || "").trim();
                    const displayTask = (t.task || "").trim() || "(Empty task)";
                    const timeStr = t.created_at ? formatRelativeTime(t.created_at) : "";
                    return (
                      <li key={t.id ?? i} className="flex items-center gap-2 group">
                        <button
                          onClick={() => setDataPopup({ type: "todo", item: t })}
                          className={`flex-1 min-w-0 text-left px-3 py-2 rounded-lg hover:bg-[var(--bg-primary)] truncate flex flex-col items-start ${isEmpty ? "text-amber-500" : ""}`}
                        >
                          <span className={t.done ? "line-through text-[var(--text-secondary)]" : ""}>{displayTask}</span>
                          {(timeStr || t.done) && (
                            <span className="text-xs text-[var(--text-secondary)] mt-0.5 flex items-center gap-1">
                              {timeStr}
                              {t.done && <span className="text-[var(--accent)]">✓</span>}
                            </span>
                          )}
                        </button>
                        {t.id && (
                          <button
                            onClick={async (e) => { e.stopPropagation(); if (confirm("Delete this todo?")) { try { await apiDelete(`/mcp/data/todos/${t.id}`); loadMcpData("todos"); setDataPopup(null); } catch { alert("Failed to delete"); } } }}
                            className="opacity-0 group-hover:opacity-100 p-1.5 rounded text-red-500 hover:bg-red-500/20 transition-opacity"
                            title="Delete"
                          >
                            ✕
                          </button>
                        )}
                      </li>
                    );
                  })}
                {dataView === "reminders" &&
                  (dataItems.reminders as { id?: string; text?: string; created_at?: string }[]).map((r, i) => (
                    <li key={r.id ?? i} className="flex items-center gap-2 group">
                      <button
                        onClick={() => setDataPopup({ type: "reminder", item: r })}
                        className="flex-1 min-w-0 text-left px-3 py-2 rounded-lg hover:bg-[var(--bg-primary)] truncate"
                      >
                        <span>{r.text || "Untitled"}</span>
                        {r.created_at && <span className="block text-xs text-[var(--text-secondary)] mt-0.5">{formatRelativeTime(r.created_at)}</span>}
                      </button>
                      {r.id && (
                        <button
                          onClick={async (e) => { e.stopPropagation(); if (confirm("Delete this reminder?")) { try { await apiDelete(`/mcp/data/reminders/${r.id}`); loadMcpData("reminders"); setDataPopup(null); } catch { alert("Failed to delete"); } } }}
                          className="opacity-0 group-hover:opacity-100 p-1.5 rounded text-red-500 hover:bg-red-500/20 transition-opacity"
                          title="Delete"
                        >
                          ✕
                        </button>
                      )}
                    </li>
                  ))}
              </ul>
              {(dataView === "notes" && dataItems.notes.length === 0) ||
              (dataView === "todos" && dataItems.todos.length === 0) ||
              (dataView === "reminders" && dataItems.reminders.length === 0) ? (
                <div className="text-sm text-[var(--text-secondary)] py-4 space-y-2">
                  <p>No items. Click &quot;View Notes&quot; to load, or add via chat (e.g. &quot;save a note with title X&quot;).</p>
                  {dataError && <p className="text-amber-500">{dataError}</p>}
                </div>
              ) : null}
            </div>
          )}
          {dataPopup && (
            <div className="fixed right-4 top-20 z-50 w-full max-w-sm">
              <div className="bg-[var(--bg-secondary)] rounded-xl p-6 border border-[var(--border)] shadow-xl">
                <div className="flex justify-between items-start mb-4">
                  <h3 className="font-semibold text-lg">
                    {dataPopup.type === "note" ? "Note" : dataPopup.type === "todo" ? "Todo" : "Reminder"}
                  </h3>
                  <div className="flex gap-1">
                    {(dataPopup.type === "note" || dataPopup.type === "todo" || dataPopup.type === "reminder") && (dataPopup.item as { id?: string }).id && (
                      <button
                        onClick={async () => {
                          if (!confirm("Delete this item?")) return;
                          try {
                            if (dataPopup.type === "note") await apiDelete(`/mcp/data/notes/${(dataPopup.item as { id: string }).id}`);
                            else if (dataPopup.type === "todo") await apiDelete(`/mcp/data/todos/${(dataPopup.item as { id: string }).id}`);
                            else await apiDelete(`/mcp/data/reminders/${(dataPopup.item as { id: string }).id}`);
                            loadMcpData(dataPopup.type);
                            setDataPopup(null);
                          } catch { alert("Failed to delete"); }
                        }}
                        className="px-2 py-1 text-xs rounded bg-red-600/30 hover:bg-red-600/50 text-red-400"
                      >
                        Delete
                      </button>
                    )}
                    <button onClick={() => setDataPopup(null)} className="text-[var(--text-secondary)] hover:text-white p-1">✕</button>
                  </div>
                </div>
                {dataPopup.type === "note" && (
                  <div className="space-y-3 text-sm">
                    <p className="font-medium">{String((dataPopup.item as { title?: string }).title || "(No title)")}</p>
                    <p className="whitespace-pre-wrap text-[var(--text-secondary)] min-h-[2rem]">{(dataPopup.item as { content?: string }).content || "(Empty content)"}</p>
                    <p className="text-xs text-[var(--text-secondary)]">
                      {(dataPopup.item as { created_at?: string }).created_at
                        ? formatRelativeTime((dataPopup.item as { created_at: string }).created_at)
                        : "—"}
                    </p>
                  </div>
                )}
                {dataPopup.type === "todo" && (
                  <div className="space-y-3 text-sm">
                    <p className="font-medium">{String((dataPopup.item as { task?: string }).task || "(No task)")}</p>
                    <p className="text-[var(--text-secondary)]">Priority: {(dataPopup.item as { priority?: string }).priority || "—"} • {(dataPopup.item as { done?: boolean }).done ? "Done" : "Pending"}</p>
                    <p className="text-xs text-[var(--text-secondary)]">
                      {(dataPopup.item as { created_at?: string }).created_at
                        ? formatRelativeTime((dataPopup.item as { created_at: string }).created_at)
                        : "—"}
                    </p>
                  </div>
                )}
                {dataPopup.type === "reminder" && (
                  <div className="space-y-3 text-sm">
                    <p className="font-medium">{String((dataPopup.item as { text?: string }).text || "Untitled")}</p>
                    <p className="text-[var(--text-secondary)]">When: {(dataPopup.item as { when?: string }).when || "—"}</p>
                    <p className="text-xs text-[var(--text-secondary)]">Created: {(dataPopup.item as { created_at?: string }).created_at || "—"}</p>
                  </div>
                )}
              </div>
            </div>
          )}
        </div>
      )}

      {activeTab === "mcp" && (
        <div className="space-y-6">
          <div className="p-4 rounded-lg bg-[var(--bg-tertiary)] border border-[var(--border)]">
            <h3 className="font-medium mb-2">Available Servers (Quick Add)</h3>
            <p className="text-sm text-[var(--text-secondary)] mb-3">
              One-click add. Start all with: <code className="px-1 py-0.5 bg-[var(--bg-primary)] rounded">pnpm dev:mcp:all</code>
            </p>
            <div className="flex flex-wrap gap-2 mb-2">
              {availableServers
                .filter((av) => !servers.some((s) => s.server_url === av.server_url))
                .map((av) => (
                  <button
                    key={av.server_url}
                    onClick={() => quickAddServer(av)}
                    disabled={addingServer !== null}
                    className="px-3 py-1.5 text-sm rounded-lg bg-[var(--accent)] hover:bg-[var(--accent-hover)] disabled:opacity-50"
                  >
                    + {av.name}
                  </button>
                ))}
              {availableServers.length > 0 && availableServers.some((av) => !servers.some((s) => s.server_url === av.server_url)) && (
                <button
                  onClick={quickAddAll}
                  disabled={addingServer !== null}
                  className="px-3 py-1.5 text-sm rounded-lg border border-[var(--border)] hover:bg-[var(--bg-primary)] disabled:opacity-50"
                >
                  {addingServer === "__all__" ? "Adding…" : "Add All"}
                </button>
              )}
            </div>
            {availableServers.filter((av) => !servers.some((s) => s.server_url === av.server_url)).length === 0 && availableServers.length > 0 && (
              <p className="text-sm text-[var(--text-secondary)]">All available servers added.</p>
            )}
          </div>

          <form onSubmit={addServer} className="space-y-3 p-4 rounded-lg bg-[var(--bg-tertiary)] border border-[var(--border)]">
            <h3 className="font-medium">Add MCP Server (Manual)</h3>
            <input
              type="text"
              placeholder="Friendly name"
              value={serverName}
              onChange={(e) => setServerName(e.target.value)}
              className="w-full px-3 py-2 rounded-lg bg-[var(--bg-primary)] border border-[var(--border)]"
              required
            />
            <input
              type="url"
              placeholder="Server URL (e.g. http://localhost:8023/mcp)"
              value={serverUrl}
              onChange={(e) => setServerUrl(e.target.value)}
              className="w-full px-3 py-2 rounded-lg bg-[var(--bg-primary)] border border-[var(--border)]"
              required
            />
            <button type="submit" className="px-4 py-2 rounded-lg bg-[var(--accent)] hover:bg-[var(--accent-hover)]">
              Add Server
            </button>
          </form>

          <div>
            <h3 className="font-medium mb-2">MCP Servers</h3>
            <ul className="space-y-2">
              {servers.map((s) => (
                <li
                  key={s.id}
                  className="p-3 rounded-lg bg-[var(--bg-tertiary)] border border-[var(--border)]"
                >
                  <div className="flex justify-between items-start">
                    <div>
                      <p className="font-medium">{s.name}</p>
                      <p className="text-sm text-[var(--text-secondary)]">{s.server_url}</p>
                    </div>
                    <div className="flex gap-2 flex-wrap">
                      <button
                        onClick={() => loadAllForServer(s.id)}
                        className="px-2 py-1 text-xs rounded bg-[var(--accent)]"
                      >
                        List All
                      </button>
                      <button
                        onClick={() => loadTools(s.id)}
                        className="px-2 py-1 text-xs rounded bg-[var(--bg-primary)] border border-[var(--border)]"
                      >
                        Tools
                      </button>
                      <button
                        onClick={() => loadResources(s.id)}
                        className="px-2 py-1 text-xs rounded bg-[var(--bg-primary)] border border-[var(--border)]"
                      >
                        Resources
                      </button>
                      <button
                        onClick={() => loadPrompts(s.id)}
                        className="px-2 py-1 text-xs rounded bg-[var(--bg-primary)] border border-[var(--border)]"
                      >
                        Prompts
                      </button>
                      <button
                        onClick={() => deleteServer(s.id)}
                        className="px-2 py-1 text-xs rounded bg-red-600/50"
                      >
                        Delete
                      </button>
                    </div>
                  </div>
                  {(toolsByServer[s.id]?.length > 0 || resourcesByServer[s.id]?.length > 0 || promptsByServer[s.id]?.length > 0) && (
                    <div className="mt-2 text-sm text-[var(--text-secondary)] space-y-1">
                      {toolsByServer[s.id]?.length > 0 && (
                        <div>
                          <span className="font-medium text-[var(--text-primary)]">Tools:</span>
                          <ul className="list-disc list-inside">
                            {toolsByServer[s.id].map((t) => (
                              <li key={t.name}>{t.name}: {t.description || ""}</li>
                            ))}
                          </ul>
                        </div>
                      )}
                      {resourcesByServer[s.id]?.length > 0 && (
                        <div>
                          <span className="font-medium text-[var(--text-primary)]">Resources:</span>
                          <ul className="list-disc list-inside">
                            {resourcesByServer[s.id].map((r) => (
                              <li key={r.uri}>{r.name || r.uri}</li>
                            ))}
                          </ul>
                        </div>
                      )}
                      {promptsByServer[s.id]?.length > 0 && (
                        <div>
                          <span className="font-medium text-[var(--text-primary)]">Prompts:</span>
                          <ul className="list-disc list-inside">
                            {promptsByServer[s.id].map((p) => (
                              <li key={p.name}>{p.name}: {p.description || ""}</li>
                            ))}
                          </ul>
                        </div>
                      )}
                    </div>
                  )}
                </li>
              ))}
            </ul>
          </div>
        </div>
      )}
    </div>
  );
}
