import json
import os
from pathlib import Path
from src.utils.logger import setup_logger

logger = setup_logger(__name__)

PREFERENCES_FILE = Path("preferences.json")

class Memory:
    """
    A simple file-backed key-value store for user preferences.
    """
    
    def __init__(self, filepath: Path = PREFERENCES_FILE):
        self.filepath = filepath
        self._cache = self._load()
        
    def _load(self) -> dict:
        if self.filepath.exists():
            try:
                with open(self.filepath, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    logger.info(f"Loaded preferences from {self.filepath}")
                    return data
            except Exception as e:
                logger.error(f"Failed to load preferences from {self.filepath}: {e}")
        return {}
        
    def _save(self) -> None:
        try:
            with open(self.filepath, "w", encoding="utf-8") as f:
                json.dump(self._cache, f, indent=4)
            logger.info(f"Saved preferences to {self.filepath}")
        except Exception as e:
            logger.error(f"Failed to save preferences to {self.filepath}: {e}")

    def get_preferences(self) -> dict:
        return self._cache.copy()
        
    def update_preferences(self, new_prefs: dict) -> dict:
        self._cache.update(new_prefs)
        self._save()
        return self._cache.copy()

# Singleton instance for the application
memory = Memory()
