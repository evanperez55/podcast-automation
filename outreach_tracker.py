"""Prospect outreach tracker backed by SQLite."""

import json
import sqlite3
from datetime import datetime, timezone
from typing import Dict, List, Optional

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
    """SQLite-backed prospect tracker with status lifecycle management.

    Tracks podcast prospects from initial identification through conversion.
    Uses a single prospects table with status and last_contact_date columns.
    """

    def __init__(self, db_path: Optional[str] = None):
        """Initialize tracker with optional custom DB path.

        Args:
            db_path: Path to SQLite database file. Defaults to
                Config.OUTPUT_DIR / "outreach.db".
        """
        self.db_path = db_path or str(Config.OUTPUT_DIR / "outreach.db")
        self._init_db()

    def _init_db(self) -> None:
        """Create prospects table if it does not exist."""
        conn = sqlite3.connect(self.db_path)
        try:
            conn.execute(
                """
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
                """
            )
            conn.commit()
        finally:
            conn.close()

    def add_prospect(self, slug: str, data: Dict) -> bool:
        """Insert a new prospect. Idempotent on duplicate slug.

        Args:
            slug: Unique identifier for the prospect (e.g. "comedy-pod").
            data: Dict with optional keys: show_name, genre, rss_feed_url,
                contact_email, social_links (dict), status, notes.

        Returns:
            True if inserted (new), False if already existed (duplicate slug).
        """
        now = datetime.now(timezone.utc).isoformat()
        social_links = data.get("social_links", {})
        social_json = (
            json.dumps(social_links) if isinstance(social_links, dict) else social_links
        )
        conn = sqlite3.connect(self.db_path)
        try:
            conn.execute(
                """
                INSERT OR IGNORE INTO prospects
                    (slug, show_name, genre, rss_feed_url, contact_email,
                     social_links, status, notes, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    slug,
                    data.get("show_name", slug),
                    data.get("genre"),
                    data.get("rss_feed_url"),
                    data.get("contact_email"),
                    social_json,
                    data.get("status", "identified"),
                    data.get("notes", ""),
                    now,
                    now,
                ),
            )
            conn.commit()
            inserted = conn.execute("SELECT changes()").fetchone()[0]
            return inserted == 1
        except Exception as e:
            logger.warning("Failed to add prospect %s: %s", slug, e)
            return False
        finally:
            conn.close()

    def get_prospect(self, slug: str) -> Optional[Dict]:
        """Retrieve a single prospect by slug.

        Args:
            slug: The prospect's unique identifier.

        Returns:
            Dict with all prospect fields, or None if not found.
            social_links is deserialized from JSON to a dict.
        """
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        try:
            row = conn.execute(
                "SELECT * FROM prospects WHERE slug = ?", (slug,)
            ).fetchone()
            if row is None:
                return None
            result = dict(row)
            # Deserialize social_links JSON string back to dict
            if result.get("social_links"):
                try:
                    result["social_links"] = json.loads(result["social_links"])
                except (json.JSONDecodeError, TypeError):
                    pass
            return result
        except Exception as e:
            logger.warning("Failed to get prospect %s: %s", slug, e)
            return None
        finally:
            conn.close()

    def update_status(self, slug: str, new_status: str) -> bool:
        """Update a prospect's status and contact timestamps.

        Args:
            slug: The prospect's unique identifier.
            new_status: New status value. Must be in VALID_STATUSES.

        Returns:
            True if updated successfully, False if slug not found.

        Raises:
            ValueError: If new_status is not in VALID_STATUSES.
        """
        if new_status not in VALID_STATUSES:
            raise ValueError(
                f"Invalid status '{new_status}'. Valid statuses: {VALID_STATUSES}"
            )
        now = datetime.now(timezone.utc).isoformat()
        conn = sqlite3.connect(self.db_path)
        try:
            conn.execute(
                """
                UPDATE prospects
                SET status = ?, updated_at = ?, last_contact_date = ?
                WHERE slug = ?
                """,
                (new_status, now, now, slug),
            )
            conn.commit()
            rowcount = conn.execute("SELECT changes()").fetchone()[0]
            return rowcount > 0
        except Exception as e:
            logger.warning("Failed to update status for %s: %s", slug, e)
            return False
        finally:
            conn.close()

    def list_prospects(self) -> List[Dict]:
        """Return all prospects ordered by created_at descending.

        Returns:
            List of dicts with all prospect fields. social_links is
            deserialized from JSON to a dict.
        """
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        try:
            rows = conn.execute(
                "SELECT * FROM prospects ORDER BY created_at DESC"
            ).fetchall()
            results = []
            for row in rows:
                p = dict(row)
                if p.get("social_links"):
                    try:
                        p["social_links"] = json.loads(p["social_links"])
                    except (json.JSONDecodeError, TypeError):
                        pass
                results.append(p)
            return results
        except Exception as e:
            logger.warning("Failed to list prospects: %s", e)
            return []
        finally:
            conn.close()
