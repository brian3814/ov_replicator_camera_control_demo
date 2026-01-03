# SPDX-FileCopyrightText: Copyright (c) 2024 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: LicenseRef-NvidiaProprietary
#
# NVIDIA CORPORATION, its affiliates and licensors retain all intellectual
# property and proprietary rights in and to this material, related
# documentation and any modifications thereto. Any use, reproduction,
# disclosure or distribution of this material and related documentation
# without an express license agreement from NVIDIA CORPORATION or
# its affiliates is strictly prohibited.

"""Capture controller for orchestrating camera capture operations."""

import os
from datetime import datetime
from typing import Callable, List, Optional

from ..camera_manager import CameraManager
from ..models import CameraSettings, CaptureStatus

__all__ = ["CaptureController"]


class CaptureController:
    """Controller for managing capture operations.

    Orchestrates the capture workflow by bridging the UI layer
    with the CameraManager business logic.
    """

    def __init__(
        self,
        on_capture_complete: Optional[Callable[[str, str], None]] = None,
        on_status_changed: Optional[Callable[[CaptureStatus], None]] = None,
    ):
        """Initialize the capture controller.

        Args:
            on_capture_complete: Callback when a capture is completed.
                                Called with (camera_name, file_path).
            on_status_changed: Callback when capture status changes.
                              Called with the new CaptureStatus.
        """
        self._on_capture_complete = on_capture_complete
        self._on_status_changed = on_status_changed
        self._camera_manager = CameraManager(on_capture_callback=self._handle_capture_complete
        )
        self._status = CaptureStatus.STOPPED

    @property
    def status(self) -> CaptureStatus:
        """Get the current capture status.

        Returns:
            The current CaptureStatus.
        """
        return self._status

    @property
    def is_capturing(self) -> bool:
        """Check if capture is currently active.

        Returns:
            True if capturing, False otherwise.
        """
        return self._camera_manager.is_capturing

    def scan_scene_cameras(self) -> List[str]:
        """Scan the scene for available cameras.

        Returns:
            List of camera prim paths found in the scene.
        """
        return self._camera_manager.scan_scene_cameras()

    def get_fps_warnings(self) -> List[str]:
        """Get warnings for cameras whose FPS exceeds app FPS.

        Returns:
            List of warning messages for FPS-capped cameras.
        """
        return self._camera_manager.get_fps_warnings()

    @property
    def measured_app_fps(self) -> float:
        """Get the measured application frame rate.

        Returns:
            The measured app FPS.
        """
        return self._camera_manager.measured_app_fps

    def start(self, cameras: List[CameraSettings], output_folder: str) -> bool:
        """Start capture for the specified cameras.

        Args:
            cameras: List of camera settings to capture.
            output_folder: Base folder for output files.

        Returns:
            True if capture started successfully, False otherwise.
        """
        if not cameras:
            return False

        if not output_folder:
            return False

        # Create output folder if it doesn't exist
        try:
            os.makedirs(output_folder, exist_ok=True)
        except OSError as e:
            print(f"[brian.camera_management] Failed to create output folder: {e}")
            self._set_status(CaptureStatus.ERROR)
            return False

        # Start capture
        success = self._camera_manager.start_capture(cameras, output_folder)

        if success:
            self._set_status(CaptureStatus.CAPTURING)
        else:
            self._set_status(CaptureStatus.ERROR)

        return success

    def stop(self):
        """Stop the current capture operation."""
        self._camera_manager.stop_capture()
        self._set_status(CaptureStatus.STOPPED)

    def _set_status(self, status: CaptureStatus):
        """Update the capture status and notify listeners.

        Args:
            status: The new capture status.
        """
        self._status = status
        if self._on_status_changed:
            self._on_status_changed(status)

    def _handle_capture_complete(self, camera_name: str, file_path: str):
        """Handle a capture completion from the camera manager.

        Args:
            camera_name: Name of the camera that captured.
            file_path: Path to the captured file.
        """
        if self._on_capture_complete:
            self._on_capture_complete(camera_name, file_path)

    def create_timestamped_folder(self, base_folder: str, prefix: str = "capture") -> str:
        """Create a timestamped subfolder for captures.

        Args:
            base_folder: The base output folder.
            prefix: Prefix for the folder name.

        Returns:
            Path to the created folder.
        """
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        folder_name = f"{prefix}_{timestamp}"
        folder_path = os.path.join(base_folder, folder_name)

        try:
            os.makedirs(folder_path, exist_ok=True)
        except OSError as e:
            print(f"[brian.camera_management] Failed to create folder: {e}")
            return base_folder

        return folder_path

    def update_camera_enabled(self, prim_path: str, enabled: bool) -> None:
        """Update camera enabled state during capture.

        Args:
            prim_path: The camera's prim path.
            enabled: Whether the camera should be capturing.
        """
        self._camera_manager.update_camera_enabled(prim_path, enabled)

    def cleanup(self):
        """Cleanup resources.

        Should be called when the extension shuts down.
        """
        self._camera_manager.cleanup()
