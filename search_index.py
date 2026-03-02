"""Episode search index using SQLite FTS5 for full-text podcast search."""

import sqlite3
from typing import Any, Dict, List, Optional

from config import Config
from logger import logger


class EpisodeSearchIndex:
    """Full-text search index for podcast episodes backed by SQLite FTS5."""

    def __init__(self, db_path: Optional[str] = None):
        self.db_path = db_path or str(Config.OUTPUT_DIR / "episode_search.db")
        self._init_db()

    def _init_db(self) -> None:
        """Create FTS5 virtual table and metadata table if they don't exist."""
        conn = sqlite3.connect(self.db_path)
        try:
            conn.execute(
                """
                CREATE VIRTUAL TABLE IF NOT EXISTS episodes USING fts5(
                    episode_number,
                    title,
                    summary,
                    show_notes,
                    transcript_text,
                    topics
                );
                """
            )
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS episode_meta (
                    episode_number INTEGER PRIMARY KEY,
                    title TEXT,
                    indexed_at TEXT
                );
                """
            )
            conn.commit()
        finally:
            conn.close()

    def index_episode(
        self,
        episode_number: int,
        title: str,
        summary: str,
        show_notes: str,
        transcript_text: str,
        topics: Optional[Any] = None,
    ) -> bool:
        """Index an episode for full-text search.

        Removes any existing entry first to allow re-indexing.
        Returns True on success, False on error.
        """
        if isinstance(topics, list):
            topics_str = ", ".join(str(t) for t in topics)
        else:
            topics_str = str(topics) if topics else ""

        conn = sqlite3.connect(self.db_path)
        try:
            # Remove existing entry for dedup on re-index
            conn.execute(
                "DELETE FROM episodes WHERE episode_number = ?",
                (str(episode_number),),
            )
            conn.execute(
                "DELETE FROM episode_meta WHERE episode_number = ?",
                (episode_number,),
            )

            conn.execute(
                """
                INSERT INTO episodes (
                    episode_number, title, summary, show_notes,
                    transcript_text, topics
                ) VALUES (?, ?, ?, ?, ?, ?);
                """,
                (
                    str(episode_number),
                    title,
                    summary,
                    show_notes,
                    transcript_text,
                    topics_str,
                ),
            )

            conn.execute(
                """
                INSERT INTO episode_meta (episode_number, title, indexed_at)
                VALUES (?, ?, datetime('now'));
                """,
                (episode_number, title),
            )

            conn.commit()
            logger.info("Indexed episode %s: %s", episode_number, title)
            return True
        except Exception as e:
            logger.error("Failed to index episode %s: %s", episode_number, e)
            return False
        finally:
            conn.close()

    def search(
        self,
        query: str,
        limit: int = 10,
        episode_range: Optional[tuple] = None,
    ) -> List[Dict[str, Any]]:
        """Search indexed episodes using FTS5 MATCH.

        Args:
            query: Full-text search query string.
            limit: Maximum number of results to return.
            episode_range: Optional (min, max) tuple to filter by episode number.

        Returns:
            List of dicts with episode_number, title, snippet, and rank.
        """
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        try:
            if episode_range is not None:
                ep_min, ep_max = episode_range
                rows = conn.execute(
                    """
                    SELECT
                        episode_number,
                        title,
                        snippet(episodes, -1, '<b>', '</b>', '...', 32) AS snippet,
                        rank
                    FROM episodes
                    WHERE episodes MATCH ?
                      AND CAST(episode_number AS INTEGER) BETWEEN ? AND ?
                    ORDER BY rank
                    LIMIT ?;
                    """,
                    (query, ep_min, ep_max, limit),
                ).fetchall()
            else:
                rows = conn.execute(
                    """
                    SELECT
                        episode_number,
                        title,
                        snippet(episodes, -1, '<b>', '</b>', '...', 32) AS snippet,
                        rank
                    FROM episodes
                    WHERE episodes MATCH ?
                    ORDER BY rank
                    LIMIT ?;
                    """,
                    (query, limit),
                ).fetchall()

            return [
                {
                    "episode_number": row["episode_number"],
                    "title": row["title"],
                    "snippet": row["snippet"],
                    "rank": row["rank"],
                }
                for row in rows
            ]
        except Exception as e:
            logger.error("Search failed for query '%s': %s", query, e)
            return []
        finally:
            conn.close()

    def get_indexed_episodes(self) -> List[Dict[str, Any]]:
        """Return all indexed episodes sorted by episode number."""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        try:
            rows = conn.execute(
                """
                SELECT episode_number, title, indexed_at
                FROM episode_meta
                ORDER BY episode_number;
                """
            ).fetchall()
            return [
                {
                    "episode_number": row["episode_number"],
                    "title": row["title"],
                    "indexed_at": row["indexed_at"],
                }
                for row in rows
            ]
        except Exception as e:
            logger.error("Failed to retrieve indexed episodes: %s", e)
            return []
        finally:
            conn.close()

    def remove_episode(self, episode_number: int) -> bool:
        """Remove an episode from both the FTS5 index and metadata table."""
        conn = sqlite3.connect(self.db_path)
        try:
            conn.execute(
                "DELETE FROM episodes WHERE episode_number = ?",
                (str(episode_number),),
            )
            conn.execute(
                "DELETE FROM episode_meta WHERE episode_number = ?",
                (episode_number,),
            )
            conn.commit()
            logger.info("Removed episode %s from search index", episode_number)
            return True
        except Exception as e:
            logger.error("Failed to remove episode %s: %s", episode_number, e)
            return False
        finally:
            conn.close()

    def close(self) -> None:
        """No-op for API compatibility.

        Connections are opened and closed per operation, so there is
        nothing to tear down.
        """
