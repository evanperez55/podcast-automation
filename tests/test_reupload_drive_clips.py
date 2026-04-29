"""Tests for scripts/reupload_drive_clips.py."""

from __future__ import annotations

import json
import sys
from pathlib import Path
from unittest.mock import MagicMock

import pytest

# Ensure scripts/ is importable
_REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(_REPO_ROOT / "scripts"))

import reupload_drive_clips as r  # noqa: E402


class TestFolderIdFromLink:
    def test_extracts_basic(self):
        link = "https://drive.google.com/drive/folders/1AbCdEfG12345"
        assert r._folder_id_from_link(link) == "1AbCdEfG12345"

    def test_strips_query_string(self):
        link = "https://drive.google.com/drive/folders/1AbCdEfG12345?usp=sharing"
        assert r._folder_id_from_link(link) == "1AbCdEfG12345"

    def test_strips_trailing_path(self):
        link = "https://drive.google.com/drive/folders/1AbCdEfG12345/inner"
        assert r._folder_id_from_link(link) == "1AbCdEfG12345"

    def test_returns_none_for_non_folder_link(self):
        assert r._folder_id_from_link("https://example.com") is None

    def test_returns_none_for_empty(self):
        assert r._folder_id_from_link("") is None


class TestCollectSlugFolderMap:
    def _make_status(
        self, tmp_path: Path, label: str, started: str, rows: list[dict]
    ) -> Path:
        d = tmp_path / f"prepare2_{label}"
        d.mkdir()
        (d / "status.json").write_text(
            json.dumps({"batch_started_at": started, "results": rows}),
            encoding="utf-8",
        )
        return d

    def test_picks_prepared_rows_only(self, tmp_path):
        d = self._make_status(
            tmp_path,
            "wed",
            "2026-04-27T17:18:00+00:00",
            [
                {
                    "slug": "good-slug",
                    "status": "prepared",
                    "drive_link": "https://drive.google.com/drive/folders/F_GOOD",
                },
                {
                    "slug": "bad-slug",
                    "status": "failed",
                    "error": "boom",
                },
            ],
        )
        result = r.collect_slug_folder_map([d])
        assert result == {"good-slug": "F_GOOD"}

    def test_later_batch_overrides_earlier_for_same_slug(self, tmp_path):
        early = self._make_status(
            tmp_path,
            "wed",
            "2026-04-27T17:00:00+00:00",
            [
                {
                    "slug": "park-church-denver",
                    "status": "prepared",
                    "drive_link": "https://drive.google.com/drive/folders/F_OLD",
                }
            ],
        )
        late = self._make_status(
            tmp_path,
            "denver-fix",
            "2026-04-27T20:00:00+00:00",
            [
                {
                    "slug": "park-church-denver",
                    "status": "prepared",
                    "drive_link": "https://drive.google.com/drive/folders/F_NEW",
                }
            ],
        )
        result = r.collect_slug_folder_map([early, late])
        assert result == {"park-church-denver": "F_NEW"}

    def test_skips_missing_status_file(self, tmp_path):
        empty_dir = tmp_path / "prepare2_empty"
        empty_dir.mkdir()
        result = r.collect_slug_folder_map([empty_dir])
        assert result == {}


class TestFindLocalClips:
    def test_returns_clip_files_from_latest_ep_dir(self, tmp_path, monkeypatch):
        slug_root = tmp_path / "my-slug"
        ep = slug_root / "ep_2026"
        final = ep / "clips" / "final"
        final.mkdir(parents=True)
        (final / "clip_01_a.mp4").write_bytes(b"x")
        (final / "clip_02_b.mp4").write_bytes(b"y")

        monkeypatch.setattr(r, "OUTPUT_ROOT", tmp_path)

        result = r.find_local_clips("my-slug")
        assert set(result.keys()) == {"clip_01_a.mp4", "clip_02_b.mp4"}

    def test_returns_empty_when_slug_missing(self, tmp_path, monkeypatch):
        monkeypatch.setattr(r, "OUTPUT_ROOT", tmp_path)
        assert r.find_local_clips("missing") == {}

    def test_returns_empty_when_no_final_dir(self, tmp_path, monkeypatch):
        (tmp_path / "my-slug" / "ep_1").mkdir(parents=True)
        monkeypatch.setattr(r, "OUTPUT_ROOT", tmp_path)
        assert r.find_local_clips("my-slug") == {}


class TestListDriveMp4s:
    def _make_service(self, pages_by_parent: dict[str, list[dict]]):
        """Mock Drive service that returns canned page responses keyed by parent."""
        service = MagicMock()

        def list_call(q, fields, pageSize, pageToken):
            # parse "'PARENT' in parents and ..."
            parent = q.split("'", 2)[1]
            files = pages_by_parent.get(parent, [])
            return MagicMock(
                execute=MagicMock(return_value={"files": files, "nextPageToken": None})
            )

        service.files.return_value.list.side_effect = list_call
        return service

    def test_collects_mp4s_recursively(self):
        service = self._make_service(
            {
                "ROOT": [
                    {
                        "id": "F1",
                        "name": "clips",
                        "mimeType": "application/vnd.google-apps.folder",
                    },
                    {"id": "X1", "name": "thumbnail.png", "mimeType": "image/png"},
                ],
                "F1": [
                    {"id": "C1", "name": "clip_01_a.mp4", "mimeType": "video/mp4"},
                    {"id": "C2", "name": "clip_02_b.mp4", "mimeType": "video/mp4"},
                ],
            }
        )
        result = r.list_drive_mp4s(service, "ROOT")
        names = sorted(f["name"] for f in result)
        assert names == ["clip_01_a.mp4", "clip_02_b.mp4"]

    def test_ignores_non_mp4(self):
        service = self._make_service(
            {
                "ROOT": [
                    {"id": "X1", "name": "blog_post.md", "mimeType": "text/markdown"},
                ]
            }
        )
        assert r.list_drive_mp4s(service, "ROOT") == []


class TestReuploadOne:
    @pytest.fixture
    def service(self):
        return MagicMock()

    def test_dry_run_makes_no_update_calls(self, service, tmp_path, monkeypatch):
        ep_final = tmp_path / "my-slug" / "ep_1" / "clips" / "final"
        ep_final.mkdir(parents=True)
        (ep_final / "clip_01_a.mp4").write_bytes(b"x")
        monkeypatch.setattr(r, "OUTPUT_ROOT", tmp_path)
        monkeypatch.setattr(
            r,
            "list_drive_mp4s",
            lambda svc, fid: [{"id": "C1", "name": "clip_01_a.mp4", "parent_id": fid}],
        )
        update_spy = MagicMock()
        monkeypatch.setattr(r, "update_file_blob", update_spy)

        matched, updated, skipped = r.reupload_one(
            service, "my-slug", "FOLDER", dry_run=True
        )
        assert matched == 1
        assert updated == 0
        assert skipped == 0
        update_spy.assert_not_called()

    def test_real_run_updates_matched_files(self, service, tmp_path, monkeypatch):
        ep_final = tmp_path / "my-slug" / "ep_1" / "clips" / "final"
        ep_final.mkdir(parents=True)
        (ep_final / "clip_01_a.mp4").write_bytes(b"x")
        (ep_final / "clip_02_b.mp4").write_bytes(b"y")
        monkeypatch.setattr(r, "OUTPUT_ROOT", tmp_path)
        monkeypatch.setattr(
            r,
            "list_drive_mp4s",
            lambda svc, fid: [
                {"id": "C1", "name": "clip_01_a.mp4", "parent_id": fid},
                {"id": "C2", "name": "clip_02_b.mp4", "parent_id": fid},
                {"id": "C3", "name": "orphan.mp4", "parent_id": fid},
            ],
        )
        update_spy = MagicMock()
        monkeypatch.setattr(r, "update_file_blob", update_spy)

        matched, updated, skipped = r.reupload_one(
            service, "my-slug", "FOLDER", dry_run=False
        )
        assert matched == 2
        assert updated == 2
        assert skipped == 1  # orphan
        assert update_spy.call_count == 2
        called_ids = {c.args[1] for c in update_spy.call_args_list}
        assert called_ids == {"C1", "C2"}

    def test_skips_when_no_local_clips(self, service, tmp_path, monkeypatch):
        monkeypatch.setattr(r, "OUTPUT_ROOT", tmp_path)
        m, u, s = r.reupload_one(service, "missing", "FOLDER", dry_run=False)
        assert (m, u, s) == (0, 0, 0)
