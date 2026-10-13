"""
AuraMotion Pro - Persistent Settings & Calibration Storage Manager
Handles atomic, corruption-proof JSON serialization to %LOCALAPPDATA%/AuraMotion/config.json
"""
import json
import os
import threading
from typing import Tuple, Optional

from ..domain.models import AppSettings, CalibrationProfile


def get_default_config_path() -> str:
    local_app_data = os.environ.get("LOCALAPPDATA")
    if local_app_data:
        base_dir = os.path.join(local_app_data, "AuraMotion")
    else:
        base_dir = os.path.join(os.path.expanduser("~"), ".auramotion")
    os.makedirs(base_dir, exist_ok=True)
    return os.path.join(base_dir, "config.json")


class SettingsManager:
    """Manages persistent AppSettings and CalibrationProfile on Windows 11."""
    def __init__(self, config_path: Optional[str] = None):
        raw_path = config_path or get_default_config_path()
        self.config_path = os.path.abspath(raw_path)
        self._lock = threading.Lock()

    def load(self) -> Tuple[AppSettings, CalibrationProfile]:
        """Loads settings and calibration profile from disk. Returns defaults if not found."""
        with self._lock:
            if not os.path.exists(self.config_path):
                return AppSettings(), CalibrationProfile()

            try:
                with open(self.config_path, "r", encoding="utf-8") as f:
                    data = json.load(f)

                settings_dict = data.get("settings", {})
                profile_dict = data.get("calibration_profile", {})

                settings = AppSettings.from_dict(settings_dict)
                profile = CalibrationProfile.from_dict(profile_dict)
                return settings, profile
            except Exception as e:
                # Corrupted or unreadable file: backup and return defaults
                try:
                    corrupt_backup = self.config_path + ".bak"
                    if os.path.exists(self.config_path):
                        os.replace(self.config_path, corrupt_backup)
                except Exception:
                    pass
                return AppSettings(), CalibrationProfile()

    def save(self, settings: AppSettings, profile: CalibrationProfile) -> bool:
        """Atomically saves settings and calibration profile to disk."""
        with self._lock:
            try:
                data = {
                    "version": "1.0",
                    "settings": settings.to_dict(),
                    "calibration_profile": profile.to_dict(),
                }
                parent_dir = os.path.dirname(self.config_path)
                if parent_dir:
                    os.makedirs(parent_dir, exist_ok=True)

                tmp_path = self.config_path + ".tmp"
                with open(tmp_path, "w", encoding="utf-8") as f:
                    json.dump(data, f, indent=2)

                os.replace(tmp_path, self.config_path)
                return True
            except Exception as e:
                return False
