from datetime import date
from . import agent_constants as constants
from typing import Dict, Any

class ResourceManager:
    """Manages the agent's mutable state and resources."""

    def __init__(self):
        self.last_run_date = date.today()
        self.daily_reasoning_count = constants.AGENT.MAX_REASONING_STEPS
        self.is_terminated = False

    def _check_and_reset_daily_resources(self):
        """Resets daily resources if the last run date was yesterday or earlier."""
        today = date.today()
        if today > self.last_run_date:
            self.last_run_date = today
            self.daily_reasoning_count = constants.AGENT.MAX_REASONING_STEPS

    def can_reason(self) -> bool:
        """Checks if the agent can perform a reasoning step."""
        self._check_and_reset_daily_resources()
        if self.daily_reasoning_count <= 0:
            self.is_terminated = True
            return False
        return True

    def record_reasoning_step(self):
        """Decrements the reasoning count."""
        if self.can_reason():
            self.daily_reasoning_count -= 1
        
    def to_dict(self) -> Dict[str, Any]:
        """Returns the state of the resource manager as a dictionary for persistence."""
        return {
            "last_run_date": self.last_run_date.isoformat(),
            "daily_reasoning_count": self.daily_reasoning_count,
            "is_terminated": self.is_terminated,
        }

    def from_dict(self, data: dict):
        """Loads the state of the resource manager from a dictionary."""
        if not data:
            return
            
        if "last_run_date" in data:
            self.last_run_date = date.fromisoformat(data["last_run_date"])
        if "daily_reasoning_count" in data:
            self.daily_reasoning_count = data["daily_reasoning_count"]
        if "is_terminated" in data:
            self.is_terminated = data["is_terminated"]

        self._check_and_reset_daily_resources()