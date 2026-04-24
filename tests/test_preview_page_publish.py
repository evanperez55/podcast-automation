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
            base_url="https://episodespreview.com",
            push=False,
            clients_dir=proj["clients_dir"],
            output_dir=proj["output_dir"],
        )

        target = repo / proj["slug"]
        assert (target / "index.html").exists()
        assert (target / "logo.png").exists()
        assert (target / "clip_01_topic.mp4").exists()
        assert url == f"https://episodespreview.com/{proj['slug']}/"

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
            base_url="https://episodespreview.com",
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
            base_url="https://episodespreview.com",
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
            base_url="https://episodespreview.com",
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
            base_url="https://episodespreview.com",
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
            base_url="https://episodespreview.com",
            push=True,
            clients_dir=proj["clients_dir"],
            output_dir=proj["output_dir"],
        )
        assert url.endswith(f"/{proj['slug']}/")


# ---------------------------------------------------------------------------
# render_locally / --open flag
# ---------------------------------------------------------------------------


class TestRenderLocally:
    """--open / render_locally writes to a tmp dir for fast iteration —
    no repo, no git, no push."""

    @patch("scripts.preview_page_publish.generate_preview_page")
    def test_writes_index_and_assets_to_target(self, mock_gen, tmp_path):
        # Stub a tiny generator output
        clip_src = tmp_path / "src_clip.mp4"
        clip_src.write_bytes(b"video")
        mock_gen.return_value = {
            "html": "<html>preview</html>",
            "assets": [{"src": clip_src, "dst_name": "clip_01.mp4"}],
            "ep_dir": tmp_path,
            "church_name": "Test",
        }

        target = tmp_path / "render"
        index = pub.render_locally("test-slug", target)

        assert index == target / "index.html"
        assert index.read_text(encoding="utf-8") == "<html>preview</html>"
        assert (target / "clip_01.mp4").exists()

    @patch("scripts.preview_page_publish.subprocess.run")
    def test_render_locally_does_not_run_git(self, mock_run, tmp_path):
        with patch("scripts.preview_page_publish.generate_preview_page") as mock_gen:
            mock_gen.return_value = {
                "html": "<html></html>",
                "assets": [],
                "ep_dir": tmp_path,
                "church_name": "Test",
            }
            pub.render_locally("test-slug", tmp_path / "render")
        mock_run.assert_not_called()


class TestOpenFlag:
    """--open invokes webbrowser on the rendered file:// URL and skips
    the entire publish/git pipeline."""

    @patch("scripts.preview_page_publish.webbrowser.open")
    @patch("scripts.preview_page_publish.generate_preview_page")
    def test_open_flag_calls_webbrowser_with_file_uri(self, mock_gen, mock_browser):
        mock_gen.return_value = {
            "html": "<html>x</html>",
            "assets": [],
            "ep_dir": Path("."),
            "church_name": "Test",
        }
        rc = pub.main(["test-slug", "--open"])
        assert rc == 0
        mock_browser.assert_called_once()
        url = mock_browser.call_args.args[0]
        assert url.startswith("file:///")
        assert "test-slug" in url
        assert url.endswith("index.html")

    @patch("scripts.preview_page_publish.webbrowser.open")
    @patch("scripts.preview_page_publish.subprocess.run")
    @patch("scripts.preview_page_publish.generate_preview_page")
    def test_open_flag_does_not_run_git_or_publish(
        self, mock_gen, mock_subproc, mock_browser
    ):
        mock_gen.return_value = {
            "html": "<html>x</html>",
            "assets": [],
            "ep_dir": Path("."),
            "church_name": "Test",
        }
        pub.main(["test-slug", "--open"])
        mock_subproc.assert_not_called()

    def test_open_and_push_are_mutually_exclusive(self):
        # argparse's mutually_exclusive_group raises SystemExit on conflict
        with patch("scripts.preview_page_publish.generate_preview_page"):
            try:
                pub.main(["test-slug", "--open", "--push"])
                assert False, "should have errored"
            except SystemExit as e:
                assert e.code != 0
