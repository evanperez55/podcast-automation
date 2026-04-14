"""Tests for pipeline/cleanup.py — GPU resource teardown."""

from __future__ import annotations

from unittest.mock import MagicMock, patch


from pipeline.cleanup import release_gpu_resources


class TestReleaseGpuResources:
    def test_drops_transcriber_model_reference(self):
        """Transcriber.model should be explicitly deleted + set to None."""
        fake_model = MagicMock()
        transcriber = MagicMock()
        transcriber.model = fake_model
        components = {"transcriber": transcriber}

        release_gpu_resources(components)

        # After cleanup, the model attribute is set to None
        assert transcriber.model is None

    def test_clears_components_dict(self):
        """After release, components dict should be empty so refs don't linger."""
        components = {
            "transcriber": MagicMock(model=None),
            "uploaders": {"foo": "bar"},
            "other": 123,
        }

        release_gpu_resources(components)

        assert components == {}

    def test_calls_torch_cuda_empty_cache_when_available(self):
        """If torch is installed and CUDA is available, we must call empty_cache."""
        fake_torch = MagicMock()
        fake_torch.cuda.is_available.return_value = True

        with patch.dict("sys.modules", {"torch": fake_torch}):
            release_gpu_resources({"transcriber": MagicMock(model=None)})

        fake_torch.cuda.synchronize.assert_called_once()
        fake_torch.cuda.empty_cache.assert_called_once()

    def test_skips_cuda_when_unavailable(self):
        """If CUDA isn't available, empty_cache must not be called."""
        fake_torch = MagicMock()
        fake_torch.cuda.is_available.return_value = False

        with patch.dict("sys.modules", {"torch": fake_torch}):
            release_gpu_resources({"transcriber": MagicMock(model=None)})

        fake_torch.cuda.empty_cache.assert_not_called()

    def test_swallows_torch_import_error(self):
        """If torch isn't installed at all, cleanup should still succeed."""
        # Make import torch raise ImportError inside release_gpu_resources.
        with patch.dict("sys.modules", {"torch": None}):
            # components=None path + no-torch path — must not raise
            release_gpu_resources(None)

    def test_handles_none_components(self):
        """Passing None components is valid — skip everything that requires them."""
        release_gpu_resources(None)  # must not raise

    def test_handles_empty_components(self):
        """Empty components dict — same as None."""
        release_gpu_resources({})  # must not raise

    def test_handles_missing_transcriber_key(self):
        """components without 'transcriber' key — skip the model-drop step."""
        release_gpu_resources({"uploaders": {}})  # must not raise

    def test_handles_transcriber_without_model_attr(self):
        """If transcriber has no .model attribute, cleanup still proceeds."""
        t = MagicMock(spec=[])  # no .model
        release_gpu_resources({"transcriber": t})  # must not raise

    def test_exception_during_model_delete_is_swallowed(self):
        """A destructor that raises during `del transcriber.model` must not
        crash cleanup — the whole point is to make cleanup bulletproof."""
        transcriber = MagicMock()

        # Configure model's __del__ path to raise via property setter
        type(transcriber).model = property(
            fget=lambda self: self._model,
            fset=lambda self, v: (_ for _ in ()).throw(RuntimeError("destructor boom")),
        )

        # Should NOT raise
        release_gpu_resources({"transcriber": transcriber})

    def test_exception_in_gc_collect_is_swallowed(self):
        with patch("pipeline.cleanup.gc.collect", side_effect=RuntimeError("gc boom")):
            release_gpu_resources({"transcriber": MagicMock(model=None)})

    def test_exception_in_cuda_empty_cache_is_swallowed(self):
        fake_torch = MagicMock()
        fake_torch.cuda.is_available.return_value = True
        fake_torch.cuda.empty_cache.side_effect = RuntimeError("cuda boom")

        with patch.dict("sys.modules", {"torch": fake_torch}):
            # Must not raise even if empty_cache crashes
            release_gpu_resources({"transcriber": MagicMock(model=None)})
