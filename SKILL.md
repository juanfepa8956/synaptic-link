---
name: synaptic-link
description: >
  Search and retrieve notes from a local Markdown vault (e.g. Obsidian).
  Use when the user asks about past decisions, project history, personal notes,
  architecture choices, or anything previously recorded in their knowledge base.
  Triggers on: "search my notes", "do you remember", "we discussed before",
  or any question that requires personal/project context beyond training data.
---

# Synaptic Link

Local full-text search for AI agents. Indexes a Markdown vault with SQLite FTS5,
chunked by section headings for paragraph-level retrieval.

**Zero dependencies** for `index`, `search`, `read`.
`watch` requires `pip install watchdog`.

---

## Setup

```bash
# Index your vault (run once, then use 'watch' to keep it current)
python skills/synaptic-link/scripts/synapse.py index --vault /path/to/vault

# Or use environment variables
export OBSIDIAN_VAULT=/path/to/vault
export SYNAPTIC_DB=~/.synaptic-link/synapse.db
python skills/synaptic-link/scripts/synapse.py index
```

SQLite 3.35+ required (FTS5 trigram tokenizer). macOS ships 3.37+, Windows/Linux
distributions from 2021+ are fine.

---

## Commands

```bash
# Search — always do this first
python synapse.py search "keyword or phrase" [--vault PATH] [--db PATH] [--limit N]

# Read full note after a search hit
python synapse.py read "/absolute/path/to/note.md"

# Rebuild index (full)
python synapse.py index [--vault PATH] [--db PATH] [--full]

# Watch vault for changes and auto-update index (requires watchdog)
python synapse.py watch [--vault PATH] [--db PATH]
```

---

## Search output format

```
## Note Title § Section Heading
   /path/to/note.md
   ...matched **snippet** with highlights…
```

The `§ Section` gives paragraph-level context — use it to decide whether to read
the full file or if the snippet is already sufficient.

---

## Usage pattern

```
search "query"
  ├─ results → snippet enough? → use it directly
  │                no?         → read full file path
  └─ no results → try broader terms → report no results
```

---

## Notes

- Files prefixed with `_draft_` are excluded from the index.
- Trigram tokenizer requires **3+ character queries**. Single/two-character CJK
  terms won't match — use longer phrases (e.g. `knowledge base` not `kb`).
- Default DB location: `~/.synaptic-link/synapse.db` (auto-created).
  Override with `--db` or `SYNAPTIC_DB`.
