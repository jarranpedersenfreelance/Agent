import datetime
import time
from typing import Dict, Any

class ResourceManager:
    """Manages cycle count, API quota, and slumber state."""

    def __init__(self, constants: Dict[str, Any]):
        self.constants = constants
        self.last_api_reset_date = datetime.datetime.utcnow().date()
        self.api_calls_today = 0
        self.api_calls_remaining = constants['API']['MAX_DAILY_QUOTA']
        self.cycle_count = 0
        self.is_slumbering = False
        self.slumber_until_cycle = 0

    def check_api_quota_reset(self):
        """Resets API quota daily based on UTC date."""
        current_date = datetime.datetime.utcnow().date()
        if current_date > self.last_api_reset_date:
            self.last_api_reset_date = current_date
            self.api_calls_today = 0
            self.api_calls_remaining = self.constants['API']['MAX_DAILY_QUOTA']
            print("[INFO] API quota reset performed for new day (UTC).")
        else:
            self.api_calls_remaining = self.constants['API']['MAX_DAILY_QUOTA'] - self.api_calls_today
    
    def handle_slumber(self) -> bool:
        """Handles the slumber state at the start of a cycle. Returns True if slumbering."""
        if not self.is_slumbering:
            return False
            
        print(f"[{time.ctime()}] Scion Agent is SLUMBERING. Cycles remaining: {self.slumber_until_cycle - self.cycle_count}")
        
        if self.cycle_count < self.slumber_until_cycle:
            time.sleep(self.constants['AGENT']['CYCLE_SLEEP_TIME'])
            return True
        else:
            self.is_slumbering = False
            print("[INFO] SLUMBER period expired. Resuming full operation.")
            return False