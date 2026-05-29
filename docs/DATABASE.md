# Database Design Documentation

This document describes the SQLite schema and configuration for Kanban Studio.

## Technology Choice
- **Engine**: SQLite
- **Path**: Stored at `/app/data/pm.db` (mounted to a persistent Docker volume `sqlite-data` to preserve data across container recreation).
- **ORM**: SQLAlchemy (Python Object Relational Mapper) for database connection management.

## Schema Modeling

We employ a normalized relational schema with three tables:

### 1. `users`
Represents the registered users. In the MVP, a default user `user` with password `password` is seeded automatically.
- `id` (INTEGER, Primary Key, Auto-increment)
- `username` (TEXT, Unique, Index, Not Null)
- `password_hash` (TEXT, Not Null)

### 2. `columns`
Represents the vertical columns on the Kanban board.
- `id` (TEXT, e.g. `"col-backlog"`): Client-side unique identifier.
- `user_id` (INTEGER, Foreign Key referencing `users(id)`): Links the column to its owner.
- `title` (TEXT): The visible name of the column (can be renamed by the user).
- `position` (INTEGER): The index order of the column.
- **Constraints**:
  - Composite Primary Key: `(id, user_id)` (allows different users to have columns with the same ID, e.g., `"col-backlog"`, with user-specific titles and positions).

### 3. `cards`
Represents individual tasks in the Kanban board.
- `id` (TEXT, e.g., `"card-1"`): Globally unique identifier generated on the client.
- `column_id` (TEXT): The column containing the card.
- `user_id` (INTEGER): Owner of the card.
- `title` (TEXT): Card header/title.
- `details` (TEXT): Card descriptions.
- `position` (INTEGER): The relative order of the card inside its column (0-indexed).
- **Constraints**:
  - Primary Key: `id`
  - Foreign Key: `(column_id, user_id)` references `columns(id, user_id)` on cascade delete.
  - Foreign Key: `user_id` references `users(id)` on cascade delete.

## Seeding & Initialization
On server startup:
1. SQLAlchemy auto-generates tables if they do not exist.
2. The seed script checks if the default account (`user`) exists. If not, it creates it with a hashed password (`password`).
3. It seeds the user's board with the initial 5 columns and 8 cards using the default board layout structure.
