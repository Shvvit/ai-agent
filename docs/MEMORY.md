# Pamięć

Własne AI uses two separate memory layers:

- `ConversationMemory` is a bounded in-process message buffer. It is not persisted.
- `MemoryManager` stores explicit notes in SQLite (default: `data/memory.sqlite3`).

The agent does not automatically save arbitrary chat messages. A note is
persisted only when the user explicitly calls `/remember` in the CLI or code
calls `MemoryManager.remember()`. Relevant notes can be retrieved for a task
and are added to planning/execution context as data, not as instructions.

CLI commands:
- `/remember text` — save a note;
- `/memory` — list saved notes;
- `/search text` — search saved notes;
- `/forget ID` — delete one note;
- `/clear` — clear only current conversation history, not durable memory.

The database supports categories, tags, importance, pinned notes and deletion.
Pinned notes are preserved by `clear()` unless `include_pinned=True` is
explicitly supplied. Search currently uses lightweight lexical matching; it
does not claim semantic/vector retrieval. Embeddings and automatic summarizing
remain future work.
