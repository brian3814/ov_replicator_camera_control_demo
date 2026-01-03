# SPDX-FileCopyrightText: Copyright (c) 2024 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: LicenseRef-NvidiaProprietary
#
# NVIDIA CORPORATION, its affiliates and licensors retain all intellectual
# property and proprietary rights in and to this material, related
# documentation and any modifications thereto. Any use, reproduction,
# disclosure or distribution of this material and related documentation
# without an express license agreement from NVIDIA CORPORATION or
# its affiliates is strictly prohibited.

"""Preview controller for managing viewport camera switching."""

from typing import Callable, Optional

from omni.kit.viewport.utility import get_active_viewport

__all__ = ["PreviewController"]


class PreviewController:
    """Controller for managing camera preview in the viewport.

    Handles switching the viewport camera for preview and restoring
    the original camera when preview is exited.
    """

    def __init__(self, on_preview_changed: Optional[Callable[[Optional[int]], None]] = None):
        """Initialize the preview controller.

        Args:
            on_preview_changed: Optional callback when preview state changes.
                               Called with the new preview index or None.
        """
        self._preview_active_index: Optional[int] = None
        self._original_camera_path: Optional[str] = None
        self._on_preview_changed = on_preview_changed

    @property
    def preview_active_index(self) -> Optional[int]:
        """Get the index of the currently previewing camera.

        Returns:
            The index of the camera being previewed, or None if not previewing.
        """
        return self._preview_active_index

    @property
    def is_previewing(self) -> bool:
        """Check if any camera is currently being previewed.

        Returns:
            True if a camera is being previewed, False otherwise.
        """
        return self._preview_active_index is not None

    def is_previewing_index(self, index: int) -> bool:
        """Check if a specific camera index is being previewed.

        Args:
            index: The camera index to check.

        Returns:
            True if the specified camera is being previewed.
        """
        return self._preview_active_index == index

    def toggle_preview(self, index: int, camera_path: str) -> bool:
        """Toggle preview for a camera.

        If the camera is already being previewed, exit preview.
        Otherwise, start preview for the camera.

        Args:
            index: The index of the camera in the list.
            camera_path: The USD prim path of the camera.

        Returns:
            True if preview is now active for this camera, False otherwise.
        """
        if self._preview_active_index == index:
            self.exit_preview()
            return False
        else:
            return self.start_preview(index, camera_path)

    def start_preview(self, index: int, camera_path: str) -> bool:
        """Start preview for a camera.

        Switches the viewport to show the specified camera's view.

        Args:
            index: The index of the camera in the list.
            camera_path: The USD prim path of the camera.

        Returns:
            True if preview started successfully, False otherwise.
        """
        # Exit any existing preview first
        if self._preview_active_index is not None:
            self._restore_camera()

        try:
            viewport = get_active_viewport()
            if viewport is None:
                return False

            # Save current viewport camera
            self._original_camera_path = viewport.camera_path

            # Set viewport to the preview camera
            viewport.camera_path = camera_path

            self._preview_active_index = index

            if self._on_preview_changed:
                self._on_preview_changed(index)

            return True

        except Exception as e:
            print(f"[brian.camera_management] Preview error: {e}")
            return False

    def exit_preview(self) -> bool:
        """Exit preview and restore the original camera.

        Returns:
            True if preview was exited successfully, False if not previewing.
        """
        if self._preview_active_index is None:
            return False

        self._restore_camera()
        self._preview_active_index = None
        self._original_camera_path = None

        if self._on_preview_changed:
            self._on_preview_changed(None)

        return True

    def _restore_camera(self):
        """Restore the original viewport camera."""
        try:
            if self._original_camera_path:
                viewport = get_active_viewport()
                if viewport:
                    viewport.camera_path = self._original_camera_path
        except Exception as e:
            print(f"[brian.camera_management] Error restoring camera: {e}")

    def on_camera_removed(self, removed_index: int):
        """Handle a camera being removed from the list.

        Adjusts the preview index if necessary.

        Args:
            removed_index: The index of the camera that was removed.
        """
        if self._preview_active_index is None:
            return

        if self._preview_active_index == removed_index:
            # The previewed camera was removed, exit preview
            self.exit_preview()
        elif self._preview_active_index > removed_index:
            # Adjust preview index since a camera before it was removed
            self._preview_active_index -= 1

    def cleanup(self):
        """Cleanup resources and restore original camera.

        Should be called when the extension shuts down.
        """
        if self._preview_active_index is not None:
            self.exit_preview()
