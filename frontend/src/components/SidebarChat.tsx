"use client";

import { useState, useRef, useEffect } from "react";
import type { BoardData } from "@/lib/kanban";

type Message = {
  role: "user" | "assistant";
  content: string;
};

type SidebarChatProps = {
  currentBoard: BoardData;
  onBoardUpdate: (updatedBoard: BoardData) => void;
};

export const SidebarChat = ({ currentBoard, onBoardUpdate }: SidebarChatProps) => {
  const [messages, setMessages] = useState<Message[]>([
    {
      role: "assistant",
      content: "Hello! I am your Kanban Studio assistant. Ask me to add cards, move tasks, or rename columns.",
    },
  ]);
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const [isOpen, setIsOpen] = useState(false);
  
  const chatEndRef = useRef<HTMLDivElement | null>(null);

  useEffect(() => {
    if (isOpen) {
      chatEndRef.current?.scrollIntoView?.({ behavior: "smooth" });
    }
  }, [messages, loading, isOpen]);

  const handleSend = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!input.trim() || loading) return;

    const userMessage = input.trim();
    setInput("");
    
    // Add user message to history
    const nextMessages = [...messages, { role: "user", content: userMessage } as Message];
    setMessages(nextMessages);
    setLoading(true);

    // Drop the client-only seeded greeting (always the first assistant message)
    // so the LLM conversation doesn't start with an assistant turn.
    const llmMessages = nextMessages.filter(
      (msg, idx) => !(idx === 0 && msg.role === "assistant")
    );

    try {
      const res = await fetch("/api/chat", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          messages: llmMessages,
          currentBoard: currentBoard,
        }),
      });

      if (!res.ok) {
        throw new Error("Chat request failed");
      }

      const data = await res.json();
      
      // Add assistant response
      setMessages((prev) => [...prev, { role: "assistant", content: data.chatResponse }]);
      
      // Update board if LLM modified it
      if (data.boardUpdate) {
        onBoardUpdate(data.boardUpdate);
      }
    } catch (err: unknown) {
      console.error("Chat request failed:", err);
      setMessages((prev) => [
        ...prev,
        {
          role: "assistant",
          content: "Sorry, I had trouble reaching the AI server. Please try again.",
        },
      ]);
    } finally {
      setLoading(false);
    }
  };

  return (
    <>
      {/* Floating Chat Panel */}
      {isOpen && (
        <aside className="fixed bottom-24 right-6 z-50 flex h-[520px] w-[380px] flex-col rounded-[32px] border border-[var(--stroke)] bg-white/95 p-6 shadow-[0_20px_50px_rgba(3,33,71,0.18)] backdrop-blur transition-all duration-200 ease-out">
          <header className="border-b border-[var(--stroke)] pb-4">
            <h2 className="font-display text-lg font-semibold text-[var(--navy-dark)]">
              AI Board Assistant
            </h2>
            <p className="mt-1 text-xs text-[var(--gray-text)]">
              Create, edit, or move cards conversationally
            </p>
          </header>

          {/* Message History */}
          <div className="mt-4 flex-1 overflow-y-auto pr-1 flex flex-col gap-4 scrollbar-thin">
            {messages.map((msg, idx) => (
              <div
                key={idx}
                className={`flex flex-col max-w-[85%] rounded-2xl px-4 py-3 text-sm leading-6 ${
                  msg.role === "user"
                    ? "self-end bg-[var(--primary-blue)] text-white"
                    : "self-start bg-[var(--surface)] text-[var(--navy-dark)] border border-[var(--stroke)]"
                }`}
              >
                <p className="whitespace-pre-wrap">{msg.content}</p>
              </div>
            ))}
            {loading && (
              <div className="self-start rounded-2xl bg-[var(--surface)] border border-[var(--stroke)] px-4 py-3 text-sm text-[var(--gray-text)] flex items-center gap-2">
                <span className="h-2 w-2 animate-bounce rounded-full bg-[var(--gray-text)]" />
                <span className="h-2 w-2 animate-bounce rounded-full bg-[var(--gray-text)] [animation-delay:0.2s]" />
                <span className="h-2 w-2 animate-bounce rounded-full bg-[var(--gray-text)] [animation-delay:0.4s]" />
              </div>
            )}
            <div ref={chatEndRef} />
          </div>

          {/* Input Form */}
          <form onSubmit={handleSend} className="mt-4 border-t border-[var(--stroke)] pt-4 flex gap-2">
            <input
              type="text"
              value={input}
              onChange={(e) => setInput(e.target.value)}
              disabled={loading}
              placeholder="Ask AI to make changes..."
              className="flex-1 rounded-2xl border border-[var(--stroke)] bg-white px-4 py-3 text-sm text-[var(--navy-dark)] outline-none transition focus:border-[var(--primary-blue)] disabled:opacity-50"
            />
            <button
              type="submit"
              disabled={loading || !input.trim()}
              className="rounded-2xl bg-[var(--secondary-purple)] px-5 py-3 text-sm font-semibold text-white shadow transition hover:bg-[#612c7a] disabled:opacity-50 cursor-pointer"
            >
              Send
            </button>
          </form>
        </aside>
      )}

      {/* Floating Chat Trigger Button */}
      <button
        onClick={() => setIsOpen((prev) => !prev)}
        className="fixed bottom-6 right-6 z-50 flex h-14 w-14 items-center justify-center rounded-full bg-[var(--secondary-purple)] hover:bg-[#612c7a] text-white shadow-[0_8px_30px_rgba(117,57,145,0.3)] transition duration-200 active:scale-95 cursor-pointer focus:outline-none"
        aria-label="Toggle AI Assistant Chat"
      >
        {isOpen ? (
          // Close Icon
          <svg className="h-6 w-6" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
            <path strokeLinecap="round" strokeLinejoin="round" d="M6 18L18 6M6 6l12 12" />
          </svg>
        ) : (
          // Chat Bubble Icon
          <svg className="h-6 w-6" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
            <path strokeLinecap="round" strokeLinejoin="round" d="M8 12h.01M12 12h.01M16 12h.01M21 12c0 4.418-4.03 8-9 8a9.863 9.863 0 01-4.255-.949L3 20l1.395-3.72C3.512 15.042 3 13.574 3 12c0-4.418 4.03-8 9-8s9 3.582 9 8z" />
          </svg>
        )}
      </button>
    </>
  );
};
