"""Tests for search_index module."""

from pathlib import Path

from search_index import EpisodeSearchIndex


def _make_index(tmp_path):
    """Helper to create an EpisodeSearchIndex backed by a temp database."""
    db_path = str(tmp_path / "test.db")
    return EpisodeSearchIndex(db_path=db_path)


def _index_sample(index, episode_number=1, title="Test Episode", keyword="testing"):
    """Helper to index a sample episode containing a keyword in the summary."""
    return index.index_episode(
        episode_number=episode_number,
        title=title,
        summary=f"A great discussion about {keyword} and more",
        show_notes=f"- Topic: {keyword}\n- Links: example.com",
        transcript_text=f"Host: Welcome back. Today we talk about {keyword}. Guest: Absolutely.",
        topics=None,
    )


class TestEpisodeSearchIndex:
    def test_init_creates_db(self, tmp_path):
        db_path = str(tmp_path / "test.db")
        EpisodeSearchIndex(db_path=db_path)
        assert Path(db_path).exists()

    def test_index_episode_success(self, tmp_path):
        index = _make_index(tmp_path)
        result = index.index_episode(
            episode_number=1,
            title="Pilot Episode",
            summary="The very first episode of the podcast.",
            show_notes="- Introductions\n- What to expect",
            transcript_text="Host: Welcome to the show!",
        )
        assert result is True

    def test_index_episode_list_topics(self, tmp_path):
        index = _make_index(tmp_path)
        result = index.index_episode(
            episode_number=1,
            title="Topics Episode",
            summary="We discuss many topics.",
            show_notes="- Topic list included",
            transcript_text="Host: Let's get started.",
            topics=["python", "automation", "podcasting"],
        )
        assert result is True
        # Verify topics were joined and are searchable
        results = index.search("python")
        assert len(results) == 1
        assert results[0]["episode_number"] == "1"

    def test_search_basic(self, tmp_path):
        index = _make_index(tmp_path)
        _index_sample(index, episode_number=1, keyword="testing")
        results = index.search("testing")
        assert len(results) == 1
        assert results[0]["episode_number"] == "1"
        assert results[0]["title"] == "Test Episode"

    def test_search_returns_snippet(self, tmp_path):
        index = _make_index(tmp_path)
        _index_sample(index, episode_number=1, keyword="microservices")
        results = index.search("microservices")
        assert len(results) == 1
        snippet = results[0]["snippet"]
        # FTS5 snippet() wraps matches in <b> tags
        assert "<b>microservices</b>" in snippet

    def test_search_no_results(self, tmp_path):
        index = _make_index(tmp_path)
        _index_sample(index, episode_number=1, keyword="testing")
        results = index.search("zyxnonexistent")
        assert results == []

    def test_search_multiple_episodes(self, tmp_path):
        index = _make_index(tmp_path)
        _index_sample(index, episode_number=1, title="Python Basics", keyword="python")
        _index_sample(index, episode_number=2, title="Java Deep Dive", keyword="java")
        _index_sample(
            index, episode_number=3, title="Python Advanced", keyword="python"
        )

        results = index.search("python")
        assert len(results) == 2
        episode_numbers = {r["episode_number"] for r in results}
        assert episode_numbers == {"1", "3"}

    def test_search_episode_range(self, tmp_path):
        index = _make_index(tmp_path)
        for i in range(1, 6):
            _index_sample(
                index, episode_number=i, title=f"Episode {i}", keyword="automation"
            )

        results = index.search("automation", episode_range=(2, 4))
        episode_numbers = {r["episode_number"] for r in results}
        assert episode_numbers == {"2", "3", "4"}

    def test_get_indexed_episodes(self, tmp_path):
        index = _make_index(tmp_path)
        _index_sample(index, episode_number=3, title="Episode Three")
        _index_sample(index, episode_number=1, title="Episode One")

        episodes = index.get_indexed_episodes()
        assert len(episodes) == 2
        # Should be sorted by episode_number
        assert episodes[0]["episode_number"] == 1
        assert episodes[0]["title"] == "Episode One"
        assert episodes[1]["episode_number"] == 3
        assert episodes[1]["title"] == "Episode Three"
        # Each entry should have an indexed_at timestamp
        assert episodes[0]["indexed_at"] is not None

    def test_remove_episode(self, tmp_path):
        index = _make_index(tmp_path)
        _index_sample(index, episode_number=1, keyword="removable")
        # Verify it exists first
        assert len(index.search("removable")) == 1

        result = index.remove_episode(1)
        assert result is True
        assert index.search("removable") == []
        assert index.get_indexed_episodes() == []

    def test_reindex_dedup(self, tmp_path):
        index = _make_index(tmp_path)
        _index_sample(index, episode_number=1, keyword="dedup")
        _index_sample(index, episode_number=1, keyword="dedup")

        results = index.search("dedup")
        assert len(results) == 1

        episodes = index.get_indexed_episodes()
        assert len(episodes) == 1

    def test_search_limit(self, tmp_path):
        index = _make_index(tmp_path)
        for i in range(1, 6):
            _index_sample(
                index, episode_number=i, title=f"Episode {i}", keyword="common"
            )

        results = index.search("common", limit=2)
        assert len(results) == 2
