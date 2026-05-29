"use client";

import { useMemo, useState, useEffect, useRef } from "react";
import {
  DndContext,
  DragOverlay,
  PointerSensor,
  useSensor,
  useSensors,
  closestCorners,
  pointerWithin,
  rectIntersection,
  type CollisionDetection,
  type DragEndEvent,
  type DragStartEvent,
} from "@dnd-kit/core";
import { KanbanColumn } from "@/components/KanbanColumn";
import { KanbanCardPreview } from "@/components/KanbanCardPreview";
import { SidebarChat } from "@/components/SidebarChat";
import { createId, moveCard, type BoardData } from "@/lib/kanban";

// Custom collision detection strategy to support dropping into empty columns
const customCollisionDetection: CollisionDetection = (args) => {
  // 1. Try pointerWithin
  const pointerCollisions = pointerWithin(args);
  if (pointerCollisions.length > 0) {
    const cardCollision = pointerCollisions.find((c) => String(c.id).startsWith("card-"));
    if (cardCollision) return [cardCollision];
    return pointerCollisions;
  }
  
  // 2. Fallback to rectIntersection
  const rectCollisions = rectIntersection(args);
  if (rectCollisions.length > 0) {
    const cardCollision = rectCollisions.find((c) => String(c.id).startsWith("card-"));
    if (cardCollision) return [cardCollision];
    return rectCollisions;
  }
  
  // 3. Fallback to closestCorners
  const cornerCollisions = closestCorners(args);
  if (cornerCollisions.length > 0) {
    const cardCollision = cornerCollisions.find((c) => String(c.id).startsWith("card-"));
    if (cardCollision) return [cardCollision];
    return cornerCollisions;
  }
  
  return [];
};


export const KanbanBoard = ({ onLogout }: { onLogout?: () => void }) => {
  const [board, setBoard] = useState<BoardData>({ columns: [], cards: {} });
  const [activeCardId, setActiveCardId] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [saveError, setSaveError] = useState(false);

  // Mirror the latest board so blur-triggered saves persist the current state
  // without recomputing it from a stale closure.
  const boardRef = useRef(board);
  useEffect(() => {
    boardRef.current = board;
  }, [board]);

  useEffect(() => {
    const fetchBoard = async () => {
      try {
        const res = await fetch("/api/kanban");
        if (res.ok) {
          const data = await res.json();
          setBoard(data);
        }
      } catch (err) {
        console.error("Failed to fetch board data:", err);
      } finally {
        setLoading(false);
      }
    };
    fetchBoard();
  }, []);

  const saveBoard = async (updatedBoard: BoardData) => {
    try {
      const res = await fetch("/api/kanban", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(updatedBoard),
      });
      if (!res.ok) {
        throw new Error(`Save failed with status ${res.status}`);
      }
      setSaveError(false);
    } catch (err) {
      console.error("Failed to save board:", err);
      setSaveError(true);
    }
  };

  const handleLogout = async () => {
    try {
      await fetch("/api/auth/logout", { method: "POST" });
      if (onLogout) {
        onLogout();
      }
    } catch (err) {
      console.error("Logout failed:", err);
    }
  };

  const sensors = useSensors(
    useSensor(PointerSensor, {
      activationConstraint: { distance: 6 },
    })
  );

  const cardsById = useMemo(() => board.cards, [board.cards]);

  const handleDragStart = (event: DragStartEvent) => {
    setActiveCardId(event.active.id as string);
  };

  const handleDragEnd = (event: DragEndEvent) => {
    const { active, over } = event;
    setActiveCardId(null);

    if (!over || active.id === over.id) {
      return;
    }

    const nextBoard = {
      ...board,
      columns: moveCard(board.columns, active.id as string, over.id as string),
    };
    setBoard(nextBoard);
    saveBoard(nextBoard);
  };

  // Live, local-only update while the user types a column title (no network call).
  const handleRenameColumn = (columnId: string, title: string) => {
    setBoard((prev) => ({
      ...prev,
      columns: prev.columns.map((column) =>
        column.id === columnId ? { ...column, title } : column
      ),
    }));
  };

  // Persist once editing finishes (input blur), saving the latest board state.
  const handleCommitBoard = () => {
    saveBoard(boardRef.current);
  };

  const handleAddCard = (columnId: string, title: string, details: string) => {
    const id = createId("card");
    const nextBoard = {
      ...board,
      cards: {
        ...board.cards,
        [id]: { id, title, details: details || "No details yet." },
      },
      columns: board.columns.map((column) =>
        column.id === columnId
          ? { ...column, cardIds: [...column.cardIds, id] }
          : column
      ),
    };
    setBoard(nextBoard);
    saveBoard(nextBoard);
  };

  const handleDeleteCard = (columnId: string, cardId: string) => {
    const nextBoard = {
      ...board,
      cards: Object.fromEntries(
        Object.entries(board.cards).filter(([id]) => id !== cardId)
      ),
      columns: board.columns.map((column) =>
        column.id === columnId
          ? {
              ...column,
              cardIds: column.cardIds.filter((id) => id !== cardId),
            }
          : column
      ),
    };
    setBoard(nextBoard);
    saveBoard(nextBoard);
  };

  if (loading) {
    return (
      <div className="flex min-h-screen items-center justify-center bg-[var(--surface)]">
        <div className="flex flex-col items-center gap-4">
          <div className="h-10 w-10 animate-spin rounded-full border-4 border-[var(--stroke)] border-t-[var(--primary-blue)]" />
          <p className="text-xs font-semibold uppercase tracking-[0.25em] text-[var(--gray-text)]">
            Loading Kanban Board...
          </p>
        </div>
      </div>
    );
  }

  const activeCard = activeCardId ? cardsById[activeCardId] : null;

  return (
    <div className="relative bg-[var(--surface)]">
      <div className="pointer-events-none absolute left-0 top-0 h-[420px] w-[420px] -translate-x-1/3 -translate-y-1/3 rounded-full bg-[radial-gradient(circle,_rgba(32,157,215,0.25)_0%,_rgba(32,157,215,0.05)_55%,_transparent_70%)]" />
      <div className="pointer-events-none absolute bottom-0 right-0 h-[520px] w-[520px] translate-x-1/4 translate-y-1/4 rounded-full bg-[radial-gradient(circle,_rgba(117,57,145,0.18)_0%,_rgba(117,57,145,0.05)_55%,_transparent_75%)]" />

      <main className="relative mx-auto flex min-h-screen max-w-[1500px] flex-col gap-10 px-6 pb-16 pt-12">
        <header className="flex flex-col gap-6 rounded-[32px] border border-[var(--stroke)] bg-white/80 p-8 shadow-[var(--shadow)] backdrop-blur">
          <div className="flex flex-wrap items-start justify-between gap-6">
            <div>
              <p className="text-xs font-semibold uppercase tracking-[0.35em] text-[var(--gray-text)]">
                Single Board Kanban
              </p>
              <h1 className="mt-3 font-display text-4xl font-semibold text-[var(--navy-dark)]">
                Kanban Studio
              </h1>
              <p className="mt-3 max-w-xl text-sm leading-6 text-[var(--gray-text)]">
                Keep momentum visible. Rename columns, drag cards between stages,
                and capture quick notes without getting buried in settings.
              </p>
            </div>
            <div className="flex items-center gap-4">
              <div className="rounded-2xl border border-[var(--stroke)] bg-[var(--surface)] px-5 py-4">
                <p className="text-xs font-semibold uppercase tracking-[0.25em] text-[var(--gray-text)]">
                  Focus
                </p>
                <p className="mt-2 text-lg font-semibold text-[var(--primary-blue)]">
                  One board. Five columns. Zero clutter.
                </p>
              </div>
              {onLogout && (
                <button
                  onClick={handleLogout}
                  className="rounded-2xl border border-[var(--stroke)] bg-white px-5 py-4 text-sm font-semibold text-[var(--navy-dark)] transition hover:bg-[var(--surface)] cursor-pointer"
                >
                  Sign Out
                </button>
              )}
            </div>
          </div>
          <div className="flex flex-wrap items-center gap-4">
            {board.columns.map((column) => (
              <div
                key={column.id}
                className="flex items-center gap-2 rounded-full border border-[var(--stroke)] px-4 py-2 text-xs font-semibold uppercase tracking-[0.2em] text-[var(--navy-dark)]"
              >
                <span className="h-2 w-2 rounded-full bg-[var(--accent-yellow)]" />
                {column.title}
              </div>
            ))}
          </div>
        </header>

        {saveError && (
          <div
            role="alert"
            className="flex items-center justify-between gap-4 rounded-2xl border border-red-200 bg-red-50 px-5 py-4 text-sm text-red-700"
          >
            <span>
              We couldn&apos;t save your latest change. Your edits may not persist —
              check your connection and try again.
            </span>
            <button
              type="button"
              onClick={() => saveBoard(boardRef.current)}
              className="rounded-xl border border-red-300 bg-white px-4 py-2 text-sm font-semibold text-red-700 transition hover:bg-red-100 cursor-pointer"
            >
              Retry
            </button>
          </div>
        )}

        <DndContext
          sensors={sensors}
          collisionDetection={customCollisionDetection}
          onDragStart={handleDragStart}
          onDragEnd={handleDragEnd}
        >
          <section className="grid gap-6 lg:grid-cols-5 w-full">
            {board.columns.map((column) => (
              <KanbanColumn
                key={column.id}
                column={column}
                cards={column.cardIds.map((cardId) => board.cards[cardId])}
                onRename={handleRenameColumn}
                onRenameCommit={handleCommitBoard}
                onAddCard={handleAddCard}
                onDeleteCard={handleDeleteCard}
              />
            ))}
          </section>
          <DragOverlay>
            {activeCard ? (
              <div className="w-[260px]">
                <KanbanCardPreview card={activeCard} />
              </div>
            ) : null}
          </DragOverlay>
        </DndContext>

        <SidebarChat currentBoard={board} onBoardUpdate={setBoard} />
      </main>
    </div>
  );
};
