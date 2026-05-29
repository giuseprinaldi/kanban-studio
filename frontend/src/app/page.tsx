"use client";

import { useEffect, useState } from "react";
import { KanbanBoard } from "@/components/KanbanBoard";
import { Login } from "@/components/Login";

export default function Home() {
  const [username, setUsername] = useState<string | null>(null);
  const [checkingAuth, setCheckingAuth] = useState(true);

  useEffect(() => {
    const checkSession = async () => {
      try {
        const res = await fetch("/api/auth/me");
        if (res.ok) {
          const data = await res.json();
          setUsername(data.username);
        }
      } catch (err) {
        console.error("Auth check failed:", err);
      } finally {
        setCheckingAuth(false);
      }
    };

    checkSession();
  }, []);

  if (checkingAuth) {
    return (
      <div className="flex min-h-screen items-center justify-center bg-[var(--surface)]">
        <div className="flex flex-col items-center gap-4">
          <div className="h-10 w-10 animate-spin rounded-full border-4 border-[var(--stroke)] border-t-[var(--primary-blue)]" />
          <p className="text-xs font-semibold uppercase tracking-[0.25em] text-[var(--gray-text)]">
            Loading Studio...
          </p>
        </div>
      </div>
    );
  }

  if (!username) {
    return <Login onLoginSuccess={(user) => setUsername(user)} />;
  }

  return <KanbanBoard onLogout={() => setUsername(null)} />;
}
