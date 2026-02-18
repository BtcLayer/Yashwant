"""
Cohort State Persistence Cache
Allows cohort signals to survive bot restarts and temporary data unavailability.
"""

import json
import os
from datetime import datetime, timezone
from typing import Dict, Optional


class CohortCache:
    """Persist cohort signals to disk for warm restarts"""
    
    def __init__(self, cache_path: str = "paper_trading_outputs/cohort_state.json"):
        self.cache_path = cache_path
        
    def save(self, cohort_state: Dict[str, float]) -> bool:
        """
        Save current cohort signals to cache.
        
        Args:
            cohort_state: Dict with keys: pros, amateurs, mood
            
        Returns:
            True if save successful, False otherwise
        """
        try:
            data = {
                "ts": int(datetime.now(timezone.utc).timestamp() * 1000),
                "ts_iso": datetime.now(timezone.utc).isoformat(),
                "pros": float(cohort_state.get("pros", 0.0)),
                "amateurs": float(cohort_state.get("amateurs", 0.0)),
                "mood": float(cohort_state.get("mood", 0.0)),
            }
            
            # Ensure directory exists
            os.makedirs(os.path.dirname(self.cache_path), exist_ok=True)
            
            # Write atomically (temp file + rename)
            temp_path = self.cache_path + ".tmp"
            with open(temp_path, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2)
            
            # Atomic rename
            if os.path.exists(self.cache_path):
                os.remove(self.cache_path)
            os.rename(temp_path, self.cache_path)
            
            return True
        except Exception as e:
            print(f"❌ CohortCache: Failed to save: {e}")
            return False
    
    def load(self, max_age_hours: int = 24) -> Optional[Dict[str, float]]:
        """
        Load last known cohort signals if fresh enough.
        
        Args:
            max_age_hours: Maximum age in hours before cache is considered stale
            
        Returns:
            Dict with pros, amateurs, mood if cache is fresh, None otherwise
        """
        try:
            if not os.path.exists(self.cache_path):
                print("ℹ️  CohortCache: No cache file found (cold start)")
                return None
            
            with open(self.cache_path, "r", encoding="utf-8") as f:
                data = json.load(f)
            
            # Check staleness
            now_ms = datetime.now(timezone.utc).timestamp() * 1000
            age_ms = now_ms - data["ts"]
            age_hours = age_ms / (1000 * 3600)
            
            if age_hours > max_age_hours:
                print(f"⚠️  CohortCache: Cache too old ({age_hours:.1f}h > {max_age_hours}h), ignoring")
                return None
            
            cached = {
                "pros": float(data.get("pros", 0.0)),
                "amateurs": float(data.get("amateurs", 0.0)),
                "mood": float(data.get("mood", 0.0)),
            }
            
            print(f"✅ CohortCache: Loaded signals (age: {age_hours:.1f}h)")
            print(f"   Pros: {cached['pros']:.4f}, Amateurs: {cached['amateurs']:.4f}, Mood: {cached['mood']:.4f}")
            
            return cached
        except Exception as e:
            print(f"❌ CohortCache: Failed to load: {e}")
            return None
    
    def get_age_hours(self) -> Optional[float]:
        """Get age of cached data in hours, or None if no cache"""
        try:
            if not os.path.exists(self.cache_path):
                return None
            
            with open(self.cache_path, "r", encoding="utf-8") as f:
                data = json.load(f)
            
            now_ms = datetime.now(timezone.utc).timestamp() * 1000
            age_ms = now_ms - data["ts"]
            return age_ms / (1000 * 3600)
        except Exception:
            return None
    
    def clear(self) -> bool:
        """Delete cache file"""
        try:
            if os.path.exists(self.cache_path):
                os.remove(self.cache_path)
                print("✅ CohortCache: Cleared")
                return True
            return False
        except Exception as e:
            print(f"❌ CohortCache: Failed to clear: {e}")
            return False
