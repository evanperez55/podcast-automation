"""Pipeline state management for checkpointing and resume support."""

import json
from datetime import datetime
from logger import logger
from config import Config


class PipelineState:
    """
    Tracks pipeline execution state per episode for checkpoint/resume.

    Each step records its outputs (file paths). On resume, completed
    steps are skipped and their outputs reloaded.
    """

    def __init__(self, episode_id: str):
        """
        Initialize pipeline state for an episode.

        Args:
            episode_id: Unique episode identifier (e.g., 'ep_25')
        """
        self.episode_id = episode_id
        self.state_dir = Config.OUTPUT_DIR / ".pipeline_state"
        self.state_dir.mkdir(exist_ok=True, parents=True)
        self.state_file = self.state_dir / f"{episode_id}.json"
        self.state = self._load()

    def _load(self) -> dict:
        """Load state from disk, or create fresh state."""
        if self.state_file.exists():
            try:
                with open(self.state_file, "r", encoding="utf-8") as f:
                    state = json.load(f)
                logger.info(
                    "Loaded pipeline state for %s (%d steps completed)",
                    self.episode_id,
                    len(state.get("completed_steps", {})),
                )
                return state
            except (json.JSONDecodeError, KeyError) as e:
                logger.warning("Corrupt state file, starting fresh: %s", e)

        return {
            "episode_id": self.episode_id,
            "created_at": datetime.now().isoformat(),
            "completed_steps": {},
            "current_step": None,
        }

    def _save(self):
        """Persist state to disk."""
        self.state["updated_at"] = datetime.now().isoformat()
        with open(self.state_file, "w", encoding="utf-8") as f:
            json.dump(self.state, f, indent=2, ensure_ascii=False)

    def is_step_completed(self, step_name: str) -> bool:
        """Check if a step has been completed."""
        return step_name in self.state["completed_steps"]

    def get_step_outputs(self, step_name: str) -> dict:
        """
        Get outputs from a completed step.

        Args:
            step_name: Name of the step

        Returns:
            Dictionary of outputs, or empty dict if step not completed
        """
        return self.state["completed_steps"].get(step_name, {}).get("outputs", {})

    def complete_step(self, step_name: str, outputs: dict = None):
        """
        Mark a step as completed and record its outputs.

        Args:
            step_name: Name of the step
            outputs: Dictionary of output paths/values
        """
        self.state["completed_steps"][step_name] = {
            "completed_at": datetime.now().isoformat(),
            "outputs": outputs or {},
        }
        self.state["current_step"] = None
        self._save()
        logger.debug("Step '%s' completed and checkpointed", step_name)

    def start_step(self, step_name: str):
        """Mark a step as in-progress."""
        self.state["current_step"] = step_name
        self._save()

    def clear(self):
        """Clear all state (for re-processing)."""
        if self.state_file.exists():
            self.state_file.unlink()
        self.state = {
            "episode_id": self.episode_id,
            "created_at": datetime.now().isoformat(),
            "completed_steps": {},
            "current_step": None,
        }
        logger.info("Pipeline state cleared for %s", self.episode_id)
