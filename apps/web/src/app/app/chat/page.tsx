"use client";

import { useState, useRef, useEffect } from "react";
import { createClient } from "@/lib/supabase";
import { useRouter } from "next/navigation";
import { ChatInterface } from "@/components/ChatInterface";
import { SettingsPanel } from "@/components/SettingsPanel";

export default function ChatPage() {
  const [mounted, setMounted] = useState(false);
  const [session, setSession] = useState<{ access_token: string } | null>(null);
  const [showSettings, setShowSettings] = useState(false);
  const router = useRouter();

  useEffect(() => {
    const supabase = createClient();
    supabase.auth.getSession().then(({ data: { session } }) => {
      if (!session) {
        router.replace("/login");
        return;
      }
      setSession(session);
      setMounted(true);
    });
  }, [router]);

  if (!mounted || !session) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <div className="animate-pulse text-[var(--text-secondary)]">Loading...</div>
      </div>
    );
  }

  return (
    <div className="flex h-screen bg-[var(--bg-primary)]">
      <main className="flex-1 flex flex-col min-w-0">
        <header className="flex items-center justify-between px-4 py-3 border-b border-[var(--border)]">
          <h1 className="text-lg font-semibold">CTS Chat</h1>
          <div className="flex items-center gap-2">
            <button
              onClick={() => setShowSettings(!showSettings)}
              className="px-3 py-1.5 rounded-lg bg-[var(--bg-tertiary)] hover:bg-[var(--border)] text-sm transition-colors"
            >
              {showSettings ? "Close Settings" : "Settings"}
            </button>
            <button
              onClick={async () => {
                const supabase = createClient();
                await supabase.auth.signOut();
                router.replace("/login");
                router.refresh();
              }}
              className="px-3 py-1.5 rounded-lg bg-[var(--bg-tertiary)] hover:bg-[var(--border)] text-sm transition-colors"
            >
              Sign out
            </button>
          </div>
        </header>

        <div className="flex flex-1 overflow-hidden" key={showSettings ? "settings" : "chat"}>
          {showSettings ? (
            <SettingsPanel onClose={() => setShowSettings(false)} />
          ) : (
            <ChatInterface onOpenSettings={() => setShowSettings(true)} />
          )}
        </div>
      </main>
    </div>
  );
}
