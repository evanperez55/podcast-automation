"""Tests for scripts/preview_page_publish.py — render → write → optional git push."""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import patch

from scripts import preview_page_publish as pub


def _seed_project(tmp_path: Path, slug: str = "test-church") -> dict:
    """Build a minimal clients/ + output/ tree the generator can render from."""
    clients = tmp_path / "clients"
    output = tmp_path / "output"
    (clients / slug).mkdir(parents=True)
    (clients / slug / "logo.png").write_bytes(b"png")
    (clients / f"{slug}.yaml").write_text(
        f"client_name: {slug}\n"
        f'podcast_name: "Test Church"\n'
        f"branding:\n  logo_path: clients/{slug}/logo.png\n",
        encoding="utf-8",
    )
    ep = output / slug / "ep_1_20260423_120000"
    (ep / "clips" / "final").mkdir(parents=True)
    (ep / "clips" / "final" / "clip_01_topic.mp4").write_bytes(b"v")
    (ep / "ep1_analysis.json").write_text(
        json.dumps({"episode_title": "Hello"}), encoding="utf-8"
    )
    return {"clients_dir": clients, "output_dir": output, "slug": slug}


# ---------------------------------------------------------------------------
# Write-out (no git)
# ---------------------------------------------------------------------------


class TestPublishLocally:
    """Without push=True, publisher just writes to the repo dir — no git."""

    def test_writes_index_html_and_assets(self, tmp_path):
        proj = _seed_project(tmp_path)
        repo = tmp_path / "previews-repo"
        repo.mkdir()

        url = pub.publish_preview_page(
            proj["slug"],
            repo_dir=repo,
            base_url="https://episodepreview.com",
            push=False,
            clients_dir=proj["clients_dir"],
            output_dir=proj["output_dir"],
        )

        target = repo / proj["slug"]
        assert (target / "index.html").exists()
        assert (target / "logo.png").exists()
        assert (target / "clip_01_topic.mp4").exists()
        assert url == f"https://episodepreview.com/{proj['slug']}/"

    def test_overwrites_previous_render(self, tmp_path):
        """Re-publishing the same slug must replace stale files, not pile them up."""
        proj = _seed_project(tmp_path)
        repo = tmp_path / "previews-repo"
        repo.mkdir()
        target = repo / proj["slug"]
        target.mkdir(parents=True)
        # Stale leftover from a prior publish that should be removed
        (target / "stale_old_clip.mp4").write_bytes(b"old")

        pub.publish_preview_page(
            proj["slug"],
            repo_dir=repo,
            base_url="https://episodepreview.com",
            push=False,
            clients_dir=proj["clients_dir"],
            output_dir=proj["output_dir"],
        )

        assert not (target / "stale_old_clip.mp4").exists(), (
            "publisher must wipe stale files in the slug dir before writing"
        )
        assert (target / "index.html").exists()

    @patch("scripts.preview_page_publish.subprocess.run")
    def test_does_not_run_git_when_push_false(self, mock_run, tmp_path):
        proj = _seed_project(tmp_path)
        repo = tmp_path / "previews-repo"
        repo.mkdir()
        pub.publish_preview_page(
            proj["slug"],
            repo_dir=repo,
            base_url="https://episodepreview.com",
            push=False,
            clients_dir=proj["clients_dir"],
            output_dir=proj["output_dir"],
        )
        mock_run.assert_not_called()


# ---------------------------------------------------------------------------
# Push
# ---------------------------------------------------------------------------


class TestGitPush:
    @patch("scripts.preview_page_publish.subprocess.run")
    def test_runs_git_add_commit_push(self, mock_run, tmp_path):
        proj = _seed_project(tmp_path)
        repo = tmp_path / "previews-repo"
        repo.mkdir()
        # All three subprocess calls succeed
        mock_run.return_value.returncode = 0

        pub.publish_preview_page(
            proj["slug"],
            repo_dir=repo,
            base_url="https://episodepreview.com",
            push=True,
            clients_dir=proj["clients_dir"],
            output_dir=proj["output_dir"],
        )

        # Verify the three git commands ran in the repo_dir, in order
        cmds = [call.args[0] for call in mock_run.call_args_list]
        assert any("add" in c for c in cmds), "git add must run"
        assert any("commit" in c for c in cmds), "git commit must run"
        assert any("push" in c for c in cmds), "git push must run"
        # All git commands target the repo dir (-C <repo>)
        for c in cmds:
            assert "-C" in c
            assert str(repo) in c

    @patch("scripts.preview_page_publish.subprocess.run")
    def test_commit_message_includes_slug(self, mock_run, tmp_path):
        proj = _seed_project(tmp_path)
        repo = tmp_path / "previews-repo"
        repo.mkdir()
        mock_run.return_value.returncode = 0

        pub.publish_preview_page(
            proj["slug"],
            repo_dir=repo,
            base_url="https://episodepreview.com",
            push=True,
            clients_dir=proj["clients_dir"],
            output_dir=proj["output_dir"],
        )

        commit_call = next(c for c in mock_run.call_args_list if "commit" in c.args[0])
        # -m message contains the slug
        cmd = commit_call.args[0]
        msg = cmd[cmd.index("-m") + 1]
        assert proj["slug"] in msg

    @patch("scripts.preview_page_publish.subprocess.run")
    def test_skips_commit_when_no_changes(self, mock_run, tmp_path):
        """If the working tree is clean after writing (idempotent re-publish),
        git commit returns nonzero — must not raise, must still print URL."""
        proj = _seed_project(tmp_path)
        repo = tmp_path / "previews-repo"
        repo.mkdir()

        # add succeeds; commit returns nonzero (nothing to commit); push not reached
        def fake_run(cmd, **_kwargs):
            from unittest.mock import MagicMock

            res = MagicMock()
            if "commit" in cmd:
                res.returncode = 1
                res.stdout = "nothing to commit, working tree clean"
            else:
                res.returncode = 0
                res.stdout = ""
            return res

        mock_run.side_effect = fake_run

        # Should not raise
        url = pub.publish_preview_page(
            proj["slug"],
            repo_dir=repo,
            base_url="https://episodepreview.com",
            push=True,
            clients_dir=proj["clients_dir"],
            output_dir=proj["output_dir"],
        )
        assert url.endswith(f"/{proj['slug']}/")
