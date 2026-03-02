"""Tests for pipeline_state module."""

import pytest
from pipeline_state import PipelineState


@pytest.fixture
def state(tmp_path, monkeypatch):
    import config

    monkeypatch.setattr(config.Config, "OUTPUT_DIR", tmp_path)
    return PipelineState("ep_test")


class TestPipelineState:
    def test_fresh_state(self, state):
        assert state.episode_id == "ep_test"
        assert state.state["completed_steps"] == {}

    def test_complete_step(self, state):
        state.complete_step("transcribe", {"path": "/tmp/t.json"})
        assert state.is_step_completed("transcribe")
        assert state.get_step_outputs("transcribe") == {"path": "/tmp/t.json"}

    def test_step_not_completed(self, state):
        assert not state.is_step_completed("nonexistent")
        assert state.get_step_outputs("nonexistent") == {}

    def test_persistence(self, state):
        state.complete_step("step1", {"out": "val"})
        # Create new instance to load from disk
        state2 = PipelineState.__new__(PipelineState)
        state2.episode_id = state.episode_id
        state2.state_dir = state.state_dir
        state2.state_file = state.state_file
        state2.state = state2._load()
        assert state2.is_step_completed("step1")
        assert state2.get_step_outputs("step1") == {"out": "val"}

    def test_clear(self, state):
        state.complete_step("step1", {})
        state.clear()
        assert not state.is_step_completed("step1")
        assert not state.state_file.exists()

    def test_start_step(self, state):
        state.start_step("processing")
        assert state.state["current_step"] == "processing"
