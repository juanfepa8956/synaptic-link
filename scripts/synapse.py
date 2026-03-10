#!/usr/bin/env python3
"""
Synaptic Link - Local knowledge retrieval for AI agents.

Indexes an Obsidian vault (or any Markdown directory) with SQLite FTS5.
Chunks notes by section (## headings) for paragraph-level retrieval.

Zero dependencies for index / search / read.
Requires: pip install watchdog   (for the 'watch' command only)

Usage:
    python synapse.py index  [--vault PATH] [--db PATH] [--full]
    python synapse.py search QUERY [--vault PATH] [--db PATH] [--limit N]
    python synapse.py read   PATH
    python synapse.py watch  [--vault PATH] [--db PATH]

Environment variables (fallback when flags not given):
    OBSIDIAN_VAULT   path to vault directory
    SYNAPTIC_DB      path to SQLite database file
"""

import hashlib
import json
import os
import re
import sqlite3
import sys
import threading
from datetime import datetime
from pathlib import Path


# ── Configuration ──────────────────────────────────────────────────────────────

def _vault_path(args):
    for i, a in enumerate(args):
        if a == "--vault" and i + 1 < len(args):
            return Path(args[i + 1])
    env = os.environ.get("OBSIDIAN_VAULT")
    if env:
        return Path(env)
    return Path.home() / "Documents" / "Obsidian Vault"


def _db_path(args):
    for i, a in enumerate(args):
        if a == "--db" and i + 1 < len(args):
            return Path(args[i + 1])
    env = os.environ.get("SYNAPTIC_DB")
    if env:
        return Path(env)
    default = Path.home() / ".synaptic-link" / "synapse.db"
    default.parent.mkdir(parents=True, exist_ok=True)
    return default


# ── Database ───────────────────────────────────────────────────────────────────

def _conn(db_path):
    conn = sqlite3.connect(str(db_path))
    conn.row_factory = sqlite3.Row
    return conn


def _init(db_path):
    conn = _conn(db_path)
    conn.executescript("""
        CREATE VIRTUAL TABLE IF NOT EXISTS notes_fts
        USING fts5(
            path,
            title,
            section,
            content,
            tags,
            modified,
            tokenize='trigram'
        );

        CREATE TABLE IF NOT EXISTS file_meta (
            path   TEXT PRIMARY KEY,
            mtime  REAL,
            hash   TEXT
        );
    """)
    conn.commit()
    conn.close()


# ── Parsing ────────────────────────────────────────────────────────────────────

def _hash(text):
    return hashlib.sha256(text.encode("utf-8", errors="ignore")).hexdigest()[:16]


def _parse_frontmatter(raw):
    """Return (title, tags, body)."""
    title = tags = ""
    body = raw
    if raw.startswith("---"):
        parts = raw.split("---", 2)
        if len(parts) >= 3:
            fm, body = parts[1], parts[2]
            for line in fm.splitlines():
                if line.startswith("title:"):
                    title = line[6:].strip().strip("\"'")
                elif line.startswith("tags:"):
                    tags = line[5:].strip().strip("[]")
    return title, tags, body


def _chunk(body):
    """Split body into [(section_heading, text)] by #/##/### headings."""
    chunks = []
    cur_heading = ""
    cur_lines = []

    for line in body.splitlines():
        if re.match(r"^#{1,3} ", line):
            if cur_lines:
                chunks.append((cur_heading, "\n".join(cur_lines).strip()))
            cur_heading = line.lstrip("#").strip()
            cur_lines = []
        else:
            cur_lines.append(line)

    if cur_lines:
        chunks.append((cur_heading, "\n".join(cur_lines).strip()))

    return [(h, c) for h, c in chunks if c.strip()]


# ── Index one file ─────────────────────────────────────────────────────────────

def _index_file(conn, filepath, fallback_title, modified):
    raw = filepath.read_text(encoding="utf-8", errors="ignore")
    title, tags, body = _parse_frontmatter(raw)
    if not title:
        title = fallback_title

    chunks = _chunk(body) or [("", body.strip())]

    conn.execute("DELETE FROM notes_fts WHERE path = ?", (str(filepath),))
    for section, text in chunks:
        if text:
            conn.execute(
                "INSERT INTO notes_fts (path,title,section,content,tags,modified)"
                " VALUES (?,?,?,?,?,?)",
                (str(filepath), title, section, text, tags, modified),
            )
    return len(chunks)


# ── Full / incremental vault index ────────────────────────────────────────────

def index_vault(vault_path, db_path, full=False):
    if not vault_path.exists():
        print(f"Vault not found: {vault_path}", file=sys.stderr)
        sys.exit(1)

    _init(db_path)
    conn = _conn(db_path)

    meta = {r["path"]: (r["mtime"], r["hash"])
            for r in conn.execute("SELECT path,mtime,hash FROM file_meta")}

    current = set()
    added = updated = skipped = 0

    for md in vault_path.rglob("*.md"):
        if md.stem.startswith("_draft_"):   # drafts excluded from index
            continue

        path_str = str(md)
        current.add(path_str)
        mtime = md.stat().st_mtime

        if not full and path_str in meta:
            old_mtime, old_hash = meta[path_str]
            if abs(mtime - old_mtime) < 0.01:
                skipped += 1
                continue
            # mtime changed — verify with hash before re-indexing
            raw = md.read_text(encoding="utf-8", errors="ignore")
            if _hash(raw) == old_hash:
                conn.execute("UPDATE file_meta SET mtime=? WHERE path=?",
                             (mtime, path_str))
                skipped += 1
                continue

        try:
            raw = md.read_text(encoding="utf-8", errors="ignore")
            h = _hash(raw)
            modified = datetime.fromtimestamp(mtime).isoformat()
            _index_file(conn, md, md.stem, modified)

            if path_str in meta:
                conn.execute("UPDATE file_meta SET mtime=?,hash=? WHERE path=?",
                             (mtime, h, path_str))
                updated += 1
            else:
                conn.execute("INSERT INTO file_meta VALUES (?,?,?)",
                             (path_str, mtime, h))
                added += 1
        except Exception as e:
            print(f"[skip] {md.name}: {e}", file=sys.stderr)

    # Remove deleted files from index
    deleted = 0
    for path_str in set(meta) - current:
        conn.execute("DELETE FROM notes_fts WHERE path=?", (path_str,))
        conn.execute("DELETE FROM file_meta WHERE path=?", (path_str,))
        deleted += 1

    conn.commit()
    conn.close()
    print(f"index: +{added} updated={updated} skipped={skipped} deleted={deleted}")


# ── Search ─────────────────────────────────────────────────────────────────────

def search(query, db_path, limit=8):
    conn = _conn(db_path)
    try:
        rows = conn.execute("""
            SELECT path, title, section,
                   snippet(notes_fts, 3, '**', '**', '…', 48) AS snippet
            FROM notes_fts
            WHERE notes_fts MATCH ?
            ORDER BY rank
            LIMIT ?
        """, (query, limit)).fetchall()
    except sqlite3.OperationalError:
        conn.close()
        return []
    conn.close()
    return [dict(r) for r in rows]


# ── Read ───────────────────────────────────────────────────────────────────────

def read_note(path):
    p = Path(path)
    return p.read_text(encoding="utf-8", errors="ignore") if p.exists() else None


# ── Watch (requires watchdog) ──────────────────────────────────────────────────

def watch_vault(vault_path, db_path):
    try:
        from watchdog.events import FileSystemEventHandler
        from watchdog.observers import Observer
    except ImportError:
        print("watchdog not installed. Run: pip install watchdog", file=sys.stderr)
        sys.exit(1)

    import time

    print("[watch] Initial index...")
    index_vault(vault_path, db_path)

    class Handler(FileSystemEventHandler):
        def __init__(self):
            self._timer = None

        def _schedule(self):
            if self._timer:
                self._timer.cancel()
            self._timer = threading.Timer(0.5, lambda: index_vault(vault_path, db_path))
            self._timer.start()

        def _handle(self, path):
            if not path.endswith(".md"):
                return
            if Path(path).stem.startswith("_draft_"):
                return
            print(f"[watch] changed: {Path(path).name}")
            self._schedule()

        def on_modified(self, e):
            if not e.is_directory:
                self._handle(e.src_path)

        def on_created(self, e):
            if not e.is_directory:
                self._handle(e.src_path)

        def on_deleted(self, e):
            if not e.is_directory:
                self._handle(e.src_path)

    obs = Observer()
    obs.schedule(Handler(), str(vault_path), recursive=True)  # noqa: instantiated with state
    obs.start()
    print(f"[watch] Watching {vault_path}  (Ctrl+C to stop)")
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        obs.stop()
    obs.join()


# ── CLI ────────────────────────────────────────────────────────────────────────

def main():
    args = sys.argv[1:]
    if not args or args[0] in ("-h", "--help"):
        print(__doc__)
        return

    cmd = args[0]
    rest = args[1:]
    vault = _vault_path(rest)
    db = _db_path(rest)

    if cmd == "index":
        full = "--full" in rest
        index_vault(vault, db, full=full)

    elif cmd == "search":
        pos = [a for a in rest if not a.startswith("-")]
        if not pos:
            print("Usage: synapse.py search <query> [--limit N] [--json]")
            return
        query = pos[0]
        limit = 8
        as_json = "--json" in rest
        for i, a in enumerate(rest):
            if a == "--limit" and i + 1 < len(rest):
                limit = int(rest[i + 1])

        if len(query) < 3:
            msg = f"Query too short: '{query}' — trigram index requires 3+ characters."
            print(msg, file=sys.stderr)
            if as_json:
                print("[]")
            return

        results = search(query, db, limit)

        if as_json:
            print(json.dumps(results, ensure_ascii=False))
            return

        if not results:
            print("No results.")
            return
        for r in results:
            sec = f" § {r['section']}" if r["section"] else ""
            print(f"## {r['title']}{sec}")
            print(f"   {r['path']}")
            print(f"   {r['snippet']}")
            print()

    elif cmd == "read":
        pos = [a for a in rest if not a.startswith("-")]
        if not pos:
            print("Usage: synapse.py read <path>")
            return
        content = read_note(pos[0])
        print(content if content else f"Not found: {pos[0]}")

    elif cmd == "watch":
        watch_vault(vault, db)

    else:
        print(f"Unknown command: {cmd}")
        print("Commands: index, search, read, watch")


if __name__ == "__main__":
    main()
