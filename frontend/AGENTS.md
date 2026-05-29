# Frontend Code Overview

This directory contains the Next.js React codebase for the Kanban application.

## Tech Stack
- **Framework**: Next.js 16 (App Router)
- **Styling**: TailwindCSS v4 (configured via CSS variables in `src/app/globals.css`)
- **Drag & Drop**: `@dnd-kit/core` and `@dnd-kit/sortable`
- **Testing**: Vitest (Unit) and Playwright (E2E)

## CSS Theme Variables
Defined in [globals.css](file:///c:/Users/giuse/projects/Code%20Builder%20Course/pm/frontend/src/app/globals.css):
- `--accent-yellow`: `#ecad0a`
- `--primary-blue`: `#209dd7`
- `--secondary-purple`: `#753991`
- `--navy-dark`: `#032147`
- `--gray-text`: `#888888`
- `--surface`: `#f7f8fb`
- `--surface-strong`: `#ffffff`

## State & Data Structures
Defined in [kanban.ts](file:///c:/Users/giuse/projects/Code%20Builder%20Course/pm/frontend/src/lib/kanban.ts):
- `Card`: `{ id: string; title: string; details: string; }`
- `Column`: `{ id: string; title: string; cardIds: string[]; }`
- `BoardData`: `{ columns: Column[]; cards: Record<string, Card>; }`

Key utilities:
- `moveCard(columns, activeId, overId)`: Implements the column-to-column or intra-column card sorting/movement math.
- `createId(prefix)`: Generates randomized IDs for newly created cards.

## Component Hierarchy
- [page.tsx](file:///c:/Users/giuse/projects/Code%20Builder%20Course/pm/frontend/src/app/page.tsx): Main entrypoint rendering the Kanban board.
- [KanbanBoard.tsx](file:///c:/Users/giuse/projects/Code%20Builder%20Course/pm/frontend/src/components/KanbanBoard.tsx): Parent board container. Manages react state, coordinates `DndContext` drag operations, and maps columns.
  - [KanbanColumn.tsx](file:///c:/Users/giuse/projects/Code%20Builder%20Course/pm/frontend/src/components/KanbanColumn.tsx): Column component using `useDroppable`. Allows column renaming and lists cards.
    - [KanbanCard.tsx](file:///c:/Users/giuse/projects/Code%20Builder%20Course/pm/frontend/src/components/KanbanCard.tsx): Draggable card using `useSortable`. Displays title and details.
    - [NewCardForm.tsx](file:///c:/Users/giuse/projects/Code%20Builder%20Course/pm/frontend/src/components/NewCardForm.tsx): Local form for creating a new card at the bottom of the column.
  - [KanbanCardPreview.tsx](file:///c:/Users/giuse/projects/Code%20Builder%20Course/pm/frontend/src/components/KanbanCardPreview.tsx): Renders the visual card preview in the `DragOverlay` container during dragging.
