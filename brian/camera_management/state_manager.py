"""State manager for persisting extension state."""

import json
import os
from typing import Any, Dict, List, Optional

import omni.kit.app

from .models import CameraSettings

__all__ = ["StateManager"]

# State file schema version for future migrations
STATE_VERSION = 1


class StateManager:
    """Manages saving and loading extension state to/from disk.

    State is persisted to a JSON file in the Omniverse extension data folder.
    """

    STATE_FILENAME = "camera_state.json"

    def __init__(self):
        """Initialize the state manager."""
        self._state_file_path: Optional[str] = None

    def _get_state_file_path(self) -> str:
        """Get the path to the state file.

        Returns:
            Path to the state JSON file in the extension data folder.
        """
        if self._state_file_path:
            return self._state_file_path

        # Get extension data folder from Omniverse
        app = omni.kit.app.get_app()
        ext_manager = app.get_extension_manager()

        # Get the extension's data path (user-writable location)
        # Use get_extension_id_by_module to get the full versioned extension ID
        ext_id = ext_manager.get_extension_id_by_module("brian.camera_management")
        ext_path = ext_manager.get_extension_path(ext_id) if ext_id else None

        if ext_path:
            # Use a data subfolder within the extension path
            data_folder = os.path.join(ext_path, "data")
        else:
            # Fallback to user documents
            data_folder = os.path.join(
                os.path.expanduser("~"),
                "Documents",
                "CameraCaptures",
                ".state"
            )

        os.makedirs(data_folder, exist_ok=True)
        self._state_file_path = os.path.join(data_folder, self.STATE_FILENAME)
        return self._state_file_path

    def save_state(
        self,
        output_folder: str,
        cameras: List[CameraSettings]
    ) -> bool:
        """Save the current state to disk.

        Args:
            output_folder: The configured output folder path.
            cameras: List of camera settings to save.

        Returns:
            True if save was successful, False otherwise.
        """
        # Filter out OmniverseKit built-in cameras
        user_cameras = [
            cam for cam in cameras
            if "OmniverseKit" not in cam.prim_path
        ]

        state = {
            "version": STATE_VERSION,
            "output_folder": output_folder,
            "cameras": [cam.to_dict() for cam in user_cameras],
        }

        try:
            state_path = self._get_state_file_path()
            with open(state_path, "w", encoding="utf-8") as f:
                json.dump(state, f, indent=2)
            return True
        except Exception as e:
            print(f"[brian.camera_management] Error saving state: {e}")
            return False

    def load_state(self) -> Optional[Dict[str, Any]]:
        """Load state from disk.

        Returns:
            Dictionary with 'output_folder' and 'cameras' keys, or None if
            no state file exists or loading failed.
        """
        try:
            state_path = self._get_state_file_path()

            if not os.path.exists(state_path):
                return None

            with open(state_path, "r", encoding="utf-8") as f:
                state = json.load(f)

            # Validate version
            version = state.get("version", 0)
            if version > STATE_VERSION:
                print(f"[brian.camera_management] State file version {version} "
                      f"is newer than supported {STATE_VERSION}")
                return None

            # Parse cameras
            cameras = []
            for cam_data in state.get("cameras", []):
                try:
                    cameras.append(CameraSettings.from_dict(cam_data))
                except Exception as e:
                    print(f"[brian.camera_management] Error parsing camera: {e}")
                    continue

            return {
                "output_folder": state.get("output_folder", ""),
                "cameras": cameras,
            }

        except json.JSONDecodeError as e:
            print(f"[brian.camera_management] Error parsing state file: {e}")
            return None
        except Exception as e:
            print(f"[brian.camera_management] Error loading state: {e}")
            return None

    def clear_state(self) -> bool:
        """Delete the state file.

        Returns:
            True if deletion was successful or file didn't exist, False otherwise.
        """
        try:
            state_path = self._get_state_file_path()
            if os.path.exists(state_path):
                os.remove(state_path)
            return True
        except Exception as e:
            print(f"[brian.camera_management] Error clearing state: {e}")
            return False
