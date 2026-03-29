# Phase 19: Outreach Tracker - Research

**Researched:** 2026-03-28
**Domain:** SQLite contact tracking, CLI command dispatch, status lifecycle management
**Confidence:** HIGH

## Summary

Phase 19 implements `outreach_tracker.py` — a lightweight SQLite module that tracks prospects through a defined lifecycle and surfaces them via four CLI subcommands (`outreach add`, `outreach list`, `outreach update`, `outreach status`). The design is already fully specified in `.planning/research/ARCHITECTURE.md` and `.planning/research/STACK.md`. No architectural decisions remain open.

The implementation pattern is a direct copy of `search_index.py`: raw `sqlite3`, no ORM, per-operation connection open/close, `tmp_path` tests with real SQLite (no mocking the DB layer). The only meaningful design question is the schema: the ARCHITECTURE.md doc specifies a two-table design (`prospects` + `contacts`) but the additional context specifies a single-table design with status fields directly on prospects. This research reconciles the two.

The CLI wires into `main.py`'s `_handle_client_command()` dispatch table under the `outreach` command with subcommands dispatched by `sys.argv[2]`. This phase touches exactly two files: creates `outreach_tracker.py`, creates `tests/test_outreach_tracker.py`, and adds an `outreach` branch to `_handle_client_command()` in `main.py`.

**Primary recommendation:** Use a single `prospects` table with `status` and `last_contact_date` columns. The two-table design in ARCHITECTURE.md is premature for 3-5 prospects; the `contacts` table is Phase 21's concern (logging each outreach attempt). Phase 19 only needs to track current status, not history.

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|-----------------|
| TRACK-01 | User can add, list, and update prospect status via CLI (identified → contacted → interested → demo_sent → converted/declined) | `outreach add/list/update` commands + `OutreachTracker` CRUD methods + status validation in Python |
| TRACK-02 | User can view a summary of all prospects and their current outreach status | `outreach list` prints tabular summary with slug, show_name, status, last_contact_date; `outreach status` shows single-prospect detail |
</phase_requirements>

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| `sqlite3` | stdlib | Prospect database | Already used in `search_index.py`; zero new deps |
| `datetime` | stdlib | ISO 8601 timestamps | `datetime.utcnow().isoformat()` for created_at/updated_at |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| `typing` | stdlib | Type hints on public methods | All public method signatures |
| `config.Config` | project | `Config.OUTPUT_DIR` for default DB path | Always |
| `logger.logger` | project | All logging | Always |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| stdlib `sqlite3` | SQLAlchemy | ORM adds 0 value for a 5-row table; `sqlite3` is the project pattern |
| Single `prospects` table | Two-table `prospects + contacts` | Two tables is ARCHITECTURE.md's design for full contact log; overkill for Phase 19 which only needs current status. Add `contacts` table in Phase 21 if needed. |

**Installation:**
```bash
# No new packages. All stdlib.
uv sync
```

## Architecture Patterns

### Recommended Project Structure
```
outreach_tracker.py          # OutreachTracker class (new)
tests/test_outreach_tracker.py  # real SQLite + tmp_path (new)
main.py                      # add outreach branch to _handle_client_command()
```

### Pattern 1: search_index.py SQLite Pattern
**What:** Per-operation connection open/close. `conn.row_factory = sqlite3.Row` for dict-like access. `try/finally conn.close()`. Schema creation in `_init_db()` called from `__init__`.
**When to use:** All database operations in this module.
**Example:**
```python
# Source: search_index.py (direct inspection)
def _init_db(self) -> None:
    conn = sqlite3.connect(self.db_path)
    try:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS prospects (
                slug          TEXT PRIMARY KEY,
                ...
            );
        """)
        conn.commit()
    finally:
        conn.close()

def get_prospect(self, slug: str) -> Optional[dict]:
    conn = sqlite3.connect(self.db_path)
    conn.row_factory = sqlite3.Row
    try:
        row = conn.execute(
            "SELECT * FROM prospects WHERE slug = ?", (slug,)
        ).fetchone()
        return dict(row) if row else None
    except Exception as e:
        logger.warning("Failed to get prospect %s: %s", slug, e)
        return None
    finally:
        conn.close()
```

### Pattern 2: Idempotent INSERT OR IGNORE
**What:** `INSERT OR IGNORE` on the slug primary key prevents duplicates silently. Caller can check return value or call `get_prospect` to detect duplicates explicitly.
**When to use:** `add_prospect()` method — satisfies the "duplicate entries prevented (idempotent on slug)" success criterion.
**Example:**
```python
# Source: SQLite docs — INSERT OR IGNORE
conn.execute("""
    INSERT OR IGNORE INTO prospects (slug, show_name, ..., created_at, updated_at)
    VALUES (?, ?, ..., ?, ?)
""", (slug, data.get("show_name"), ..., now, now))
conn.commit()
```

### Pattern 3: Status Validation in Python (not DB CHECK constraint)
**What:** Valid statuses defined as a module-level tuple. Validation raises `ValueError` before any SQL. DB stores TEXT without constraint. This matches project convention — errors at system boundaries, trust internal code.
**When to use:** `add_prospect()` and `update_status()` calls.
**Example:**
```python
VALID_STATUSES = (
    "identified",
    "contacted",
    "interested",
    "demo_sent",
    "converted",
    "declined",
)

def update_status(self, slug: str, new_status: str) -> bool:
    if new_status not in VALID_STATUSES:
        raise ValueError(f"Invalid status '{new_status}'. Valid: {VALID_STATUSES}")
    ...
```

### Pattern 4: CLI Subcommand Dispatch in `_handle_client_command()`
**What:** The `outreach` command is added to `_handle_client_command()`. Subcommand is `sys.argv[2]`. Positional arg (slug) is `sys.argv[3]`.
**When to use:** main.py additions.
**Example:**
```python
# Source: main.py direct inspection — follows existing pattern
elif cmd == "outreach":
    from outreach_tracker import OutreachTracker
    subcmd = sys.argv[2] if len(sys.argv) > 2 else None
    tracker = OutreachTracker()
    if subcmd == "add" and len(sys.argv) > 3:
        slug = sys.argv[3]
        # parse remaining kwargs...
        tracker.add_prospect(slug, data)
    elif subcmd == "list":
        prospects = tracker.list_prospects()
        _print_prospects_table(prospects)
    elif subcmd == "update" and len(sys.argv) > 4:
        tracker.update_status(sys.argv[3], sys.argv[4])
    elif subcmd == "status" and len(sys.argv) > 3:
        p = tracker.get_prospect(sys.argv[3])
        _print_prospect_detail(p)
    else:
        print("Usage: uv run main.py outreach <add|list|update|status> ...")
```

### Recommended Schema
```sql
CREATE TABLE IF NOT EXISTS prospects (
    slug            TEXT PRIMARY KEY,
    show_name       TEXT NOT NULL,
    genre           TEXT,
    rss_feed_url    TEXT,
    contact_email   TEXT,
    social_links    TEXT,   -- JSON-encoded dict or comma-separated
    status          TEXT NOT NULL DEFAULT 'identified',
    notes           TEXT,
    last_contact_date TEXT, -- ISO 8601, updated on status change
    created_at      TEXT NOT NULL,
    updated_at      TEXT NOT NULL
);
```

Note: `social_links` stored as JSON string (stdlib `json.dumps`/`json.loads`) — avoids a separate table for a 5-row dataset.

### Anti-Patterns to Avoid
- **Two-table design in Phase 19:** Don't create the `contacts` log table now. That's needed for Phase 21 (pitch tracking). Single table is sufficient for TRACK-01 and TRACK-02.
- **ORM or query builder:** The project pattern is raw SQL. No SQLAlchemy, no peewee.
- **`datetime.now()` without UTC:** Use `datetime.utcnow().isoformat()` for consistent ISO 8601 timestamps. Or `datetime.now(timezone.utc).isoformat()` with `from datetime import datetime, timezone`.
- **DB path inside per-client directory:** `output/outreach.db` at root output level, not `output/<client>/outreach.db`. This is a shared tracker across all prospects.
- **Storing connection as instance attribute:** Open/close per operation. Instance attribute connections cause "closed connection" errors in tests.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Duplicate prevention | Custom check-then-insert | `INSERT OR IGNORE` on PRIMARY KEY | Atomic, race-safe |
| ISO 8601 timestamps | String formatting | `datetime.utcnow().isoformat()` | Correct format, stdlib |
| Dict rows from DB | Manual `dict(zip(cols, row))` | `conn.row_factory = sqlite3.Row` then `dict(row)` | Project pattern, cleaner |
| Status validation | Complex state machine | Module-level tuple + `ValueError` | 6 valid values, no transitions enforced |

**Key insight:** This is a 6-field form with 6 valid status values. Any abstraction beyond raw SQL + a tuple of valid statuses is over-engineering.

## Common Pitfalls

### Pitfall 1: Connection Left Open on Exception
**What goes wrong:** If `conn.execute()` raises and there is no `finally: conn.close()`, the SQLite WAL file persists and subsequent test runs in the same `tmp_path` see a locked DB.
**Why it happens:** Exception skips the close call.
**How to avoid:** Always wrap SQL in `try/finally conn.close()`. The `search_index.py` pattern is the reference.
**Warning signs:** `sqlite3.OperationalError: database is locked` in tests.

### Pitfall 2: `INSERT OR IGNORE` Returns No Error on Duplicate
**What goes wrong:** `add_prospect()` silently succeeds on a duplicate slug. If the caller needs to know whether the row was new or existing, checking `conn.execute().rowcount` is required (`0` = ignored, `1` = inserted).
**Why it happens:** `INSERT OR IGNORE` is designed to be silent.
**How to avoid:** Return `True` if inserted (rowcount=1), `False` if already existed (rowcount=0). Document this in the docstring.

### Pitfall 3: `sys.argv` Parsing for Subcommands with Optional Keyword Args
**What goes wrong:** `outreach add <slug> --show "Show Name" --email host@example.com` requires simple flag parsing. If `_parse_flags()` in `main.py` doesn't strip these before command dispatch, `sys.argv` indices shift.
**Why it happens:** `_parse_flags()` only strips the flags it knows about (`--test`, `--dry-run`, etc.). New `--show` and `--email` flags are not stripped.
**How to avoid:** Parse `outreach add` arguments inline in the `outreach` dispatch block using a simple loop over remaining `sys.argv` entries. Don't extend `_parse_flags()`. Or accept positional-only args for the CLI (simpler: `outreach add <slug> <show_name> [<email>]`).

### Pitfall 4: `row_factory = sqlite3.Row` Not Set on All Connections
**What goes wrong:** Some methods set `row_factory`, others don't. Methods without it return tuples, not dict-like Row objects. Callers get `TypeError: 'tuple' object is not subscriptable` when accessing `row["slug"]`.
**Why it happens:** Setting `row_factory` is easy to forget on connections that only need to return rows.
**How to avoid:** Set `conn.row_factory = sqlite3.Row` on every connection that fetches rows. Write-only connections (INSERT/UPDATE) don't need it.

### Pitfall 5: `updated_at` Not Updated on `update_status()`
**What goes wrong:** `updated_at` stays at original `created_at` value; `last_contact_date` is also not updated.
**Why it happens:** SQL UPDATE statement omits the timestamp columns.
**How to avoid:** Always include `updated_at = ?, last_contact_date = ?` in every `UPDATE` statement.

## Code Examples

### OutreachTracker class skeleton
```python
# Source: search_index.py pattern (direct codebase inspection)
"""Prospect outreach tracker backed by SQLite."""

import json
import sqlite3
from datetime import datetime, timezone
from typing import Optional

from config import Config
from logger import logger

VALID_STATUSES = (
    "identified",
    "contacted",
    "interested",
    "demo_sent",
    "converted",
    "declined",
)


class OutreachTracker:
    """SQLite-backed prospect tracker with status lifecycle."""

    def __init__(self, db_path: Optional[str] = None):
        self.db_path = db_path or str(Config.OUTPUT_DIR / "outreach.db")
        self._init_db()

    def _init_db(self) -> None:
        conn = sqlite3.connect(self.db_path)
        try:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS prospects (
                    slug              TEXT PRIMARY KEY,
                    show_name         TEXT NOT NULL,
                    genre             TEXT,
                    rss_feed_url      TEXT,
                    contact_email     TEXT,
                    social_links      TEXT,
                    status            TEXT NOT NULL DEFAULT 'identified',
                    notes             TEXT,
                    last_contact_date TEXT,
                    created_at        TEXT NOT NULL,
                    updated_at        TEXT NOT NULL
                );
            """)
            conn.commit()
        finally:
            conn.close()

    def add_prospect(self, slug: str, data: dict) -> bool:
        """Insert prospect. Returns True if new, False if already existed."""
        now = datetime.now(timezone.utc).isoformat()
        social = json.dumps(data.get("social_links", {}))
        conn = sqlite3.connect(self.db_path)
        try:
            conn.execute(
                """INSERT OR IGNORE INTO prospects
                   (slug, show_name, genre, rss_feed_url, contact_email,
                    social_links, status, notes, created_at, updated_at)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    slug,
                    data.get("show_name", slug),
                    data.get("genre"),
                    data.get("rss_feed_url"),
                    data.get("contact_email"),
                    social,
                    data.get("status", "identified"),
                    data.get("notes", ""),
                    now,
                    now,
                ),
            )
            conn.commit()
            inserted = conn.execute(
                "SELECT changes()"
            ).fetchone()[0]
            return inserted == 1
        except Exception as e:
            logger.warning("Failed to add prospect %s: %s", slug, e)
            return False
        finally:
            conn.close()
```

### Test pattern (real SQLite, tmp_path)
```python
# Source: test_search_index.py pattern (direct codebase inspection)
import pytest
from outreach_tracker import OutreachTracker


def _make_tracker(tmp_path):
    return OutreachTracker(db_path=str(tmp_path / "test_outreach.db"))


class TestOutreachTrackerInit:
    def test_init_creates_db(self, tmp_path):
        """DB file is created on instantiation."""
        from pathlib import Path
        tracker = _make_tracker(tmp_path)
        assert Path(tracker.db_path).exists()


class TestAddProspect:
    def test_add_prospect_returns_true_on_insert(self, tmp_path):
        """add_prospect returns True for new slug."""
        tracker = _make_tracker(tmp_path)
        result = tracker.add_prospect("test-show", {"show_name": "Test Show"})
        assert result is True

    def test_add_prospect_idempotent_on_duplicate_slug(self, tmp_path):
        """add_prospect returns False and does not raise on duplicate slug."""
        tracker = _make_tracker(tmp_path)
        tracker.add_prospect("test-show", {"show_name": "Test Show"})
        result = tracker.add_prospect("test-show", {"show_name": "Test Show Duplicate"})
        assert result is False
        # Original name preserved
        p = tracker.get_prospect("test-show")
        assert p["show_name"] == "Test Show"
```

### list_prospects tabular output helper
```python
def _print_prospects_table(prospects: list) -> None:
    """Print prospects as a formatted table."""
    if not prospects:
        print("No prospects found.")
        return
    fmt = "{:<20} {:<30} {:<15} {:<12}"
    print(fmt.format("Slug", "Show Name", "Status", "Last Contact"))
    print("-" * 80)
    for p in prospects:
        print(fmt.format(
            p["slug"][:20],
            p["show_name"][:30],
            p["status"],
            (p["last_contact_date"] or "—")[:12],
        ))
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| ORM (SQLAlchemy) | Raw `sqlite3` | v1.0 (search_index.py established) | Zero new deps, test with real DB via tmp_path |
| Per-episode JSON files | SQLite for relational data | v1.0 | Enables cross-prospect queries for list/filter |

**Deprecated/outdated:**
- Two-table schema (prospects + contacts): Specified in ARCHITECTURE.md but premature for Phase 19 scope. Single table is correct for TRACK-01 and TRACK-02. Add contacts log table in a later phase if pitch tracking requires it.

## Open Questions

1. **CLI argument style for `outreach add`**
   - What we know: `_parse_flags()` only strips known flags; `sys.argv` is cleaned before dispatch
   - What's unclear: Whether to use `--show "Name" --email foo@bar.com` kwargs or positional `<slug> <show_name>` args
   - Recommendation: Use positional args for the MVP (`outreach add <slug> <show_name> [<email>]`). Simpler parsing, consistent with how `init-client <name>` works. The user can update fields with `outreach update` after adding.

2. **`changes()` vs `rowcount` for INSERT OR IGNORE detection**
   - What we know: Both are valid SQLite approaches
   - What's unclear: Whether `conn.execute().rowcount` is reliably populated in Python's `sqlite3` module for all versions
   - Recommendation: Use `SELECT changes()` immediately after INSERT for portability (confirmed reliable in CPython's sqlite3 module).

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest (project standard) |
| Config file | `pyproject.toml` — `testpaths = ["tests"]` |
| Quick run command | `uv run pytest tests/test_outreach_tracker.py -x` |
| Full suite command | `uv run pytest` |

### Phase Requirements → Test Map
| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| TRACK-01 | add_prospect inserts row | unit | `uv run pytest tests/test_outreach_tracker.py::TestAddProspect -x` | Wave 0 |
| TRACK-01 | Duplicate slug is idempotent (INSERT OR IGNORE) | unit | `uv run pytest tests/test_outreach_tracker.py::TestAddProspect::test_add_prospect_idempotent_on_duplicate_slug -x` | Wave 0 |
| TRACK-01 | update_status changes status column | unit | `uv run pytest tests/test_outreach_tracker.py::TestUpdateStatus -x` | Wave 0 |
| TRACK-01 | update_status raises ValueError for invalid status | unit | `uv run pytest tests/test_outreach_tracker.py::TestUpdateStatus::test_update_status_invalid_raises -x` | Wave 0 |
| TRACK-01 | list_prospects returns all rows | unit | `uv run pytest tests/test_outreach_tracker.py::TestListProspects -x` | Wave 0 |
| TRACK-02 | list_prospects returns status and last_contact_date | unit | `uv run pytest tests/test_outreach_tracker.py::TestListProspects::test_list_includes_status_and_date -x` | Wave 0 |
| TRACK-02 | outreach list CLI command prints table | smoke | `uv run main.py outreach list` (manual verify) | manual-only |

### Sampling Rate
- **Per task commit:** `uv run pytest tests/test_outreach_tracker.py -x`
- **Per wave merge:** `uv run pytest`
- **Phase gate:** Full suite green before `/gsd:verify-work`

### Wave 0 Gaps
- [ ] `tests/test_outreach_tracker.py` — covers TRACK-01, TRACK-02 (file does not yet exist)

## Sources

### Primary (HIGH confidence)
- `search_index.py` (direct codebase inspection) — SQLite pattern, per-operation connection, row_factory usage
- `tests/test_search_index.py` (direct codebase inspection) — tmp_path test pattern, _make_index helper, round-trip tests
- `main.py` (direct codebase inspection) — `_handle_client_command()` dispatch pattern, `sys.argv` parsing
- `.planning/research/ARCHITECTURE.md` (direct read) — OutreachTracker design, schema, method signatures
- `.planning/research/STACK.md` (direct read) — Zero new packages, sqlite3 pattern confirmed

### Secondary (MEDIUM confidence)
- Python `sqlite3` docs — `INSERT OR IGNORE`, `row_factory`, `changes()` — standard stdlib behavior

### Tertiary (LOW confidence)
- None

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — zero new packages, pattern established in search_index.py
- Architecture: HIGH — ARCHITECTURE.md fully specifies the design
- Pitfalls: HIGH — derived from direct code inspection of search_index.py pattern
- Schema: HIGH — specified in ARCHITECTURE.md, reconciled with phase scope

**Research date:** 2026-03-28
**Valid until:** 2026-06-28 (stable stdlib; no external APIs in this phase)
