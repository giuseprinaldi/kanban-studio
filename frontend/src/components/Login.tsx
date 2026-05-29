"use client";

import { useState } from "react";

type LoginProps = {
  onLoginSuccess: (username: string) => void;
};

export const Login = ({ onLoginSuccess }: LoginProps) => {
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);
    setLoading(true);

    try {
      const res = await fetch("/api/auth/login", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({ username, password }),
      });

      if (!res.ok) {
        const data = await res.json().catch(() => ({}));
        throw new Error(data.detail || "Authentication failed");
      }

      const data = await res.json();
      onLoginSuccess(data.username);
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Something went wrong");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="relative flex min-h-screen items-center justify-center overflow-hidden bg-[var(--surface)] px-4">
      {/* Background ambient light effects */}
      <div className="pointer-events-none absolute left-0 top-0 h-[400px] w-[400px] -translate-x-1/3 -translate-y-1/3 rounded-full bg-[radial-gradient(circle,_rgba(32,157,215,0.15)_0%,_transparent_70%)]" />
      <div className="pointer-events-none absolute bottom-0 right-0 h-[500px] w-[500px] translate-x-1/4 translate-y-1/4 rounded-full bg-[radial-gradient(circle,_rgba(117,57,145,0.12)_0%,_transparent_75%)]" />

      <div className="w-full max-w-md rounded-[32px] border border-[var(--stroke)] bg-white/80 p-10 shadow-[var(--shadow)] backdrop-blur-md">
        <header className="text-center">
          <p className="text-xs font-semibold uppercase tracking-[0.35em] text-[var(--gray-text)]">
            Kanban Studio
          </p>
          <h1 className="mt-3 font-display text-3xl font-semibold text-[var(--navy-dark)]">
            Sign In
          </h1>
          <p className="mt-2 text-sm text-[var(--gray-text)]">
            Access your secure project board
          </p>
        </header>

        <form onSubmit={handleSubmit} className="mt-8 flex flex-col gap-6">
          {error && (
            <div className="rounded-2xl bg-red-50 border border-red-200 px-4 py-3 text-sm text-red-600">
              {error}
            </div>
          )}

          <div className="flex flex-col gap-2">
            <label
              htmlFor="username"
              className="text-xs font-semibold uppercase tracking-[0.15em] text-[var(--navy-dark)]"
            >
              Username
            </label>
            <input
              id="username"
              type="text"
              required
              value={username}
              onChange={(e) => setUsername(e.target.value)}
              className="rounded-2xl border border-[var(--stroke)] bg-white px-4 py-3 text-sm text-[var(--navy-dark)] outline-none transition focus:border-[var(--primary-blue)]"
              placeholder="Enter your username"
            />
          </div>

          <div className="flex flex-col gap-2">
            <label
              htmlFor="password"
              className="text-xs font-semibold uppercase tracking-[0.15em] text-[var(--navy-dark)]"
            >
              Password
            </label>
            <input
              id="password"
              type="password"
              required
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              className="rounded-2xl border border-[var(--stroke)] bg-white px-4 py-3 text-sm text-[var(--navy-dark)] outline-none transition focus:border-[var(--primary-blue)]"
              placeholder="Enter your password"
            />
          </div>

          <button
            type="submit"
            disabled={loading}
            className="mt-2 rounded-2xl bg-[var(--secondary-purple)] py-4 text-sm font-semibold text-white shadow-md transition hover:bg-[#612c7a] focus:outline-none disabled:opacity-50"
          >
            {loading ? "Authenticating..." : "Sign In"}
          </button>
        </form>
      </div>
    </div>
  );
};
