"""Tests for scripts/preview_page_generator.py — hosted episode preview page."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from scripts import preview_page_generator as gen


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


def _make_client_yaml(clients_dir: Path, slug: str, podcast_name: str) -> Path:
    clients_dir.mkdir(parents=True, exist_ok=True)
    (clients_dir / slug).mkdir(parents=True, exist_ok=True)
    logo = clients_dir / slug / "logo.png"
    logo.write_bytes(b"png-bytes")
    yaml_path = clients_dir / f"{slug}.yaml"
    yaml_path.write_text(
        f"client_name: {slug}\n"
        f'podcast_name: "{podcast_name}"\n'
        f"branding:\n"
        f"  logo_path: clients/{slug}/logo.png\n",
        encoding="utf-8",
    )
    return yaml_path


def _make_ep_dir(output_dir: Path, slug: str) -> Path:
    ep = output_dir / slug / "ep_42_20260423_120000"
    (ep / "clips" / "final").mkdir(parents=True)

    # 5 final clips
    for i in range(1, 6):
        (ep / "clips" / "final" / f"clip_0{i}_topic_{i}.mp4").write_bytes(
            f"clip{i}".encode()
        )

    # Thumbnail
    (ep / "ep42_20260423_120000_thumbnail.png").write_bytes(b"thumb-bytes")

    # Analysis: episode_title, chapters, social_captions
    (ep / "ep42_20260423_120000_analysis.json").write_text(
        json.dumps(
            {
                "episode_title": "The Mission That Started It All",
                "episode_summary": "A 10-year reflection on Acts 1.",
                "chapters": [
                    {
                        "start_timestamp": "00:00:00",
                        "title": "Intro",
                        "start_seconds": 0.0,
                    },
                    {
                        "start_timestamp": "00:05:30",
                        "title": "Acts 1 setup",
                        "start_seconds": 330.0,
                    },
                ],
                "best_clips": [
                    {"title": "Clip A"},
                    {"title": "Clip B"},
                    {"title": "Clip C"},
                    {"title": "Clip D"},
                    {"title": "Clip E"},
                ],
            }
        ),
        encoding="utf-8",
    )

    # Transcript segments
    (ep / "ep42_20260423_120000_transcript.json").write_text(
        json.dumps(
            {
                "segments": [
                    {"start": 0.0, "end": 5.0, "text": " Welcome to Redeemer."},
                    {"start": 330.0, "end": 335.0, "text": " Let's read Acts 1."},
                ]
            }
        ),
        encoding="utf-8",
    )

    # Blog post markdown
    (ep / "ep42_20260423_120000_blog_post.md").write_text(
        "# 10 Years of Grace\n\nThis week, **Redeemer** turned ten.\n", encoding="utf-8"
    )
    return ep


@pytest.fixture
def project(tmp_path) -> dict:
    """Returns dict of clients_dir + output_dir for a fully-populated slug."""
    clients = tmp_path / "clients"
    output = tmp_path / "output"
    _make_client_yaml(clients, "test-church", "Test Church")
    _make_ep_dir(output, "test-church")
    return {"clients_dir": clients, "output_dir": output, "slug": "test-church"}


# ---------------------------------------------------------------------------
# Shape contract
# ---------------------------------------------------------------------------


class TestGenerateReturnShape:
    def test_returns_html_and_assets_keys(self, project):
        result = gen.generate_preview_page(
            project["slug"],
            clients_dir=project["clients_dir"],
            output_dir=project["output_dir"],
        )
        assert "html" in result
        assert "assets" in result
        assert isinstance(result["html"], str)
        assert isinstance(result["assets"], list)

    def test_raises_when_client_yaml_missing(self, project):
        with pytest.raises(FileNotFoundError, match="client"):
            gen.generate_preview_page(
                "no-such-slug",
                clients_dir=project["clients_dir"],
                output_dir=project["output_dir"],
            )

    def test_raises_when_no_ep_dir(self, tmp_path):
        clients = tmp_path / "clients"
        output = tmp_path / "output"
        _make_client_yaml(clients, "ghost-church", "Ghost Church")
        # Intentionally no ep_dir
        with pytest.raises(FileNotFoundError, match="episode"):
            gen.generate_preview_page(
                "ghost-church", clients_dir=clients, output_dir=output
            )


# ---------------------------------------------------------------------------
# HTML contents
# ---------------------------------------------------------------------------


class TestGeneratedHtml:
    def test_includes_church_display_name(self, project):
        html = gen.generate_preview_page(
            project["slug"],
            clients_dir=project["clients_dir"],
            output_dir=project["output_dir"],
        )["html"]
        assert "Test Church" in html

    def test_includes_episode_title(self, project):
        html = gen.generate_preview_page(
            project["slug"],
            clients_dir=project["clients_dir"],
            output_dir=project["output_dir"],
        )["html"]
        assert "The Mission That Started It All" in html

    def test_has_noindex_meta(self, project):
        html = gen.generate_preview_page(
            project["slug"],
            clients_dir=project["clients_dir"],
            output_dir=project["output_dir"],
        )["html"]
        assert "noindex" in html.lower()
        assert 'name="robots"' in html

    def test_has_video_tag_per_clip(self, project):
        html = gen.generate_preview_page(
            project["slug"],
            clients_dir=project["clients_dir"],
            output_dir=project["output_dir"],
        )["html"]
        # One <video> per clip, src is relative (clips/clip_NN_*.mp4 OR clip_NN_*.mp4)
        assert html.count("<video") == 5
        for i in range(1, 6):
            assert f"clip_0{i}_topic_{i}.mp4" in html

    def test_has_chapters_table(self, project):
        html = gen.generate_preview_page(
            project["slug"],
            clients_dir=project["clients_dir"],
            output_dir=project["output_dir"],
        )["html"]
        assert "00:00:00" in html
        assert "Intro" in html
        assert "00:05:30" in html
        assert "Acts 1 setup" in html

    def test_has_transcript_with_timestamps(self, project):
        html = gen.generate_preview_page(
            project["slug"],
            clients_dir=project["clients_dir"],
            output_dir=project["output_dir"],
        )["html"]
        assert "[00:00:00]" in html
        assert "Welcome to Redeemer." in html
        assert "[00:05:30]" in html

    def test_renders_blog_post_markdown_to_html(self, project):
        html = gen.generate_preview_page(
            project["slug"],
            clients_dir=project["clients_dir"],
            output_dir=project["output_dir"],
        )["html"]
        # `# 10 Years of Grace` becomes <h1>...</h1>
        assert "10 Years of Grace" in html
        assert "<strong>Redeemer</strong>" in html

    def test_footer_has_evan_mailto(self, project):
        html = gen.generate_preview_page(
            project["slug"],
            clients_dir=project["clients_dir"],
            output_dir=project["output_dir"],
        )["html"]
        assert "evan@neurovai.org" in html
        assert "mailto:evan@neurovai.org" in html

    def test_logo_referenced_relatively(self, project):
        html = gen.generate_preview_page(
            project["slug"],
            clients_dir=project["clients_dir"],
            output_dir=project["output_dir"],
        )["html"]
        # Logo should ship alongside index.html as logo.png (relative ref).
        assert 'src="logo.png"' in html


# ---------------------------------------------------------------------------
# Asset list
# ---------------------------------------------------------------------------


class TestAssetList:
    """Each asset is {src: Path, dst_name: str}. dst_name is what the publisher
    writes the file as in the deployed dir (must match what the HTML refs)."""

    def test_includes_all_clips(self, project):
        assets = gen.generate_preview_page(
            project["slug"],
            clients_dir=project["clients_dir"],
            output_dir=project["output_dir"],
        )["assets"]
        dst_names = {a["dst_name"] for a in assets}
        for i in range(1, 6):
            assert f"clip_0{i}_topic_{i}.mp4" in dst_names

    def test_includes_logo_renamed(self, project):
        assets = gen.generate_preview_page(
            project["slug"],
            clients_dir=project["clients_dir"],
            output_dir=project["output_dir"],
        )["assets"]
        # Source can have any name; in the deployed dir it becomes logo.png
        # so the template's <img src="logo.png"> resolves.
        logo = next((a for a in assets if a["dst_name"] == "logo.png"), None)
        assert logo is not None
        assert logo["src"].exists()

    def test_includes_thumbnail_renamed(self, project):
        assets = gen.generate_preview_page(
            project["slug"],
            clients_dir=project["clients_dir"],
            output_dir=project["output_dir"],
        )["assets"]
        thumb = next((a for a in assets if a["dst_name"] == "thumbnail.png"), None)
        assert thumb is not None
        assert thumb["src"].exists()


# ---------------------------------------------------------------------------
# Graceful degradation
# ---------------------------------------------------------------------------


class TestMissingOptionalData:
    """Older episodes may lack chapters/transcript/blog. Page must still render."""

    def test_no_blog_post(self, tmp_path):
        clients = tmp_path / "clients"
        output = tmp_path / "output"
        _make_client_yaml(clients, "minimal", "Minimal Church")
        ep = _make_ep_dir(output, "minimal")
        (ep / "ep42_20260423_120000_blog_post.md").unlink()

        result = gen.generate_preview_page(
            "minimal", clients_dir=clients, output_dir=output
        )
        # Renders without raising; "Blog post" section omitted
        assert "Test Church" not in result["html"]
        assert "Minimal Church" in result["html"]

    def test_no_transcript(self, tmp_path):
        clients = tmp_path / "clients"
        output = tmp_path / "output"
        _make_client_yaml(clients, "minimal2", "Minimal2 Church")
        ep = _make_ep_dir(output, "minimal2")
        (ep / "ep42_20260423_120000_transcript.json").unlink()

        result = gen.generate_preview_page(
            "minimal2", clients_dir=clients, output_dir=output
        )
        assert "Minimal2 Church" in result["html"]
        # Transcript section absent — no [00:00:00] markers present
        assert "[00:00:00]" not in result["html"]

    def test_no_chapters(self, tmp_path):
        clients = tmp_path / "clients"
        output = tmp_path / "output"
        _make_client_yaml(clients, "minimal3", "Minimal3 Church")
        ep = _make_ep_dir(output, "minimal3")
        # Strip chapters from analysis
        ap = ep / "ep42_20260423_120000_analysis.json"
        d = json.loads(ap.read_text(encoding="utf-8"))
        d.pop("chapters", None)
        ap.write_text(json.dumps(d), encoding="utf-8")

        result = gen.generate_preview_page(
            "minimal3", clients_dir=clients, output_dir=output
        )
        assert "Minimal3 Church" in result["html"]
        # Should not have an empty "Chapters" header section if no chapters
        # (presence of "Chapters" word is fine in surrounding prose, but the
        # specific table shouldn't be there)
        assert "Acts 1 setup" not in result["html"]


# ---------------------------------------------------------------------------
# Latest ep_dir selection
# ---------------------------------------------------------------------------


class TestLatestEpDir:
    """When multiple ep_dirs exist, picks the most recent one."""

    def test_picks_latest_by_name_sort(self, tmp_path):
        clients = tmp_path / "clients"
        output = tmp_path / "output"
        _make_client_yaml(clients, "multi", "Multi Church")

        # Two ep_dirs — newer one wins (lex sort works because timestamp suffix)
        old = output / "multi" / "ep_1_20260101_000000"
        (old / "clips" / "final").mkdir(parents=True)
        (old / "clips" / "final" / "clip_01_old.mp4").write_bytes(b"old")
        (old / "ep1_old_analysis.json").write_text(
            json.dumps({"episode_title": "OLD episode"}), encoding="utf-8"
        )

        new = output / "multi" / "ep_2_20260423_120000"
        (new / "clips" / "final").mkdir(parents=True)
        (new / "clips" / "final" / "clip_01_new.mp4").write_bytes(b"new")
        (new / "ep2_new_analysis.json").write_text(
            json.dumps({"episode_title": "NEW episode"}), encoding="utf-8"
        )

        result = gen.generate_preview_page(
            "multi", clients_dir=clients, output_dir=output
        )
        assert "NEW episode" in result["html"]
        assert "OLD episode" not in result["html"]
