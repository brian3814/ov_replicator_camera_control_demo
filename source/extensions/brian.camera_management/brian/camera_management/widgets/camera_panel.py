# SPDX-FileCopyrightText: Copyright (c) 2024 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: LicenseRef-NvidiaProprietary
#
# NVIDIA CORPORATION, its affiliates and licensors retain all intellectual
# property and proprietary rights in and to this material, related
# documentation and any modifications thereto. Any use, reproduction,
# disclosure or distribution of this material and related documentation
# without an express license agreement from NVIDIA CORPORATION or
# its affiliates is strictly prohibited.

"""Camera panel widget for individual camera settings."""

from dataclasses import dataclass
from typing import Callable, List, Optional, Set

import omni.ui as ui

from ..models import CameraSettings, CaptureMode
from ..styles import COLORS, SPACING
from .resolution_widget import ResolutionWidget

__all__ = ["CameraPanelWidget", "CameraPanelCallbacks"]


@dataclass
class CameraPanelCallbacks:
    """Callbacks for camera panel events."""

    on_remove: Callable[[int], None]
    """Called when the remove button is clicked. Receives the panel index."""

    on_preview: Callable[[int], None]
    """Called when the preview button is clicked. Receives the panel index."""

    on_settings_changed: Callable[[int, CameraSettings], None]
    """Called when any setting changes. Receives the panel index and updated settings."""

    on_mode_changed: Callable[[int], None]
    """Called when capture mode changes. Receives the panel index."""


class CameraPanelWidget:
    """Widget for displaying and editing a single camera's settings.

    Encapsulates a CollapsableFrame with camera selection, resolution,
    fps, preview, capture mode, and output settings.
    """

    def __init__(
        self,
        index: int,
        settings: CameraSettings,
        all_cameras: List[str],
        cameras_in_use: Set[str],
        is_previewing: bool,
        callbacks: CameraPanelCallbacks,
    ):
        """Initialize the camera panel widget.

        Args:
            index: The index of this camera in the list.
            settings: The camera settings to display/edit.
            all_cameras: List of all available camera prim paths.
            cameras_in_use: Set of camera paths already in use by other panels.
            is_previewing: Whether this camera is currently being previewed.
            callbacks: Callback functions for panel events.
        """
        self._index = index
        self._settings = settings
        self._all_cameras = all_cameras
        self._cameras_in_use = cameras_in_use
        self._is_previewing = is_previewing
        self._callbacks = callbacks

        # Widget references
        self._frame: Optional[ui.CollapsableFrame] = None
        self._width_widget: Optional[ResolutionWidget] = None
        self._height_widget: Optional[ResolutionWidget] = None

    @property
    def settings(self) -> CameraSettings:
        """Get the current camera settings.

        Returns:
            The CameraSettings for this panel.
        """
        return self._settings

    def build(self) -> ui.CollapsableFrame:
        """Build the camera panel UI.

        Returns:
            The CollapsableFrame container for this camera.
        """
        self._frame = ui.CollapsableFrame(
            f"Camera_{self._index}",
            collapsed=False,
            style={"background_color": COLORS["background_dark"]}
        )

        with self._frame:
            with ui.VStack(spacing=SPACING, style={"margin": 5}):
                self._build_camera_selector()
                self._build_enabled_checkbox()
                self._build_fps_row()
                self._build_resolution_controls()
                self._build_preview_button()
                self._build_capture_mode()

                if self._settings.capture_mode != CaptureMode.VIDEO:
                    self._build_output_types()

        return self._frame

    def _build_enabled_checkbox(self):
        """Build the enabled checkbox row."""
        with ui.HStack(height=25, spacing=SPACING):
            ui.Label("Enabled:", width=100)
            enabled_combo = ui.ComboBox(
                0 if self._settings.enabled else 1,
                "True",
                "False"
            )

            def on_enabled_changed(model, item):
                selected = model.get_item_value_model().get_value_as_int()
                self._settings.enabled = (selected == 0)  # 0 = True, 1 = False
                self._notify_settings_changed()

            enabled_combo.model.add_item_changed_fn(on_enabled_changed)

    def _build_camera_selector(self):
        """Build the camera selection dropdown row."""
        with ui.HStack(height=25, spacing=SPACING):
            ui.Label("Camera:", width=70)

            if self._all_cameras:
                # Build dropdown with grayed-out items for cameras in use
                display_items = []
                selectable_indices = []
                current_index = 0

                for i, cam_path in enumerate(self._all_cameras):
                    cam_name = cam_path.split("/")[-1]
                    if cam_path in self._cameras_in_use:
                        display_items.append(f"{cam_name} (in use)")
                    else:
                        display_items.append(cam_name)
                        selectable_indices.append(i)

                    # Track current camera's index
                    if cam_path == self._settings.prim_path:
                        current_index = i

                combo = ui.ComboBox(current_index, *display_items)

                def on_camera_changed(model, item):
                    selected = model.get_item_value_model().get_value_as_int()
                    if selected in selectable_indices:
                        self._settings.prim_path = self._all_cameras[selected]
                        self._settings.display_name = self._all_cameras[selected].split("/")[-1]
                        self._notify_settings_changed()
                    else:
                        # Reset to current camera (reject selection of in-use camera)
                        try:
                            current_idx = self._all_cameras.index(self._settings.prim_path)
                            model.get_item_value_model().set_value(current_idx)
                        except ValueError:
                            pass

                combo.model.add_item_changed_fn(on_camera_changed)
            else:
                ui.Label("No cameras in scene", style={"color": COLORS["warning"]})

            ui.Button(
                "Remove",
                width=80,
                clicked_fn=lambda: self._callbacks.on_remove(self._index)
            )

    def _build_fps_row(self):
        """Build the FPS input row."""

        with ui.HStack(height=25, spacing=SPACING):
            ui.Label("FPS:", width=50)
            fps_field = ui.IntField(width=80)
            fps_field.model.set_value(self._settings.fps)

            def on_fps_changed(model):
                value = max(1, min(120, model.get_value_as_int()))
                self._settings.fps = value
                self._notify_settings_changed()

            fps_field.model.add_value_changed_fn(on_fps_changed)
    def _build_resolution_controls(self):
        """Build the width and height resolution controls."""
        # Width control
        self._width_widget = ResolutionWidget(
            label="Width:",
            min_val=64,
            max_val=4096,
            initial=self._settings.width,
            on_change=self._on_width_changed
        )
        self._width_widget.build()

        # Height control
        self._height_widget = ResolutionWidget(
            label="Height:",
            min_val=64,
            max_val=4096,
            initial=self._settings.height,
            on_change=self._on_height_changed
        )
        self._height_widget.build()

    def _on_width_changed(self, value: int):
        """Handle width value change.

        Args:
            value: The new width value.
        """
        self._settings.width = value
        self._notify_settings_changed()

    def _on_height_changed(self, value: int):
        """Handle height value change.

        Args:
            value: The new height value.
        """
        self._settings.height = value
        self._notify_settings_changed()

    def _build_preview_button(self):
        """Build the preview toggle button."""
        btn_text = "Exit Preview" if self._is_previewing else "Preview"
        btn_color = COLORS["danger"] if self._is_previewing else COLORS["primary"]

        ui.Button(
            btn_text,
            height=25,
            clicked_fn=lambda: self._callbacks.on_preview(self._index),
            style={"background_color": btn_color}
        )

    def _build_capture_mode(self):
        """Build the capture mode selector."""
        with ui.HStack(height=25, spacing=SPACING):
            ui.Label("Capture Mode:", width=100)
            mode_combo = ui.ComboBox(
                0 if self._settings.capture_mode == CaptureMode.IMAGE else 1,
                "Image Sequence",
                "Video"
            )

            def on_mode_changed(model, item):
                selected = model.get_item_value_model().get_value_as_int()
                self._settings.capture_mode = (
                    CaptureMode.IMAGE if selected == 0 else CaptureMode.VIDEO
                )
                self._notify_settings_changed()
                self._callbacks.on_mode_changed(self._index)

            mode_combo.model.add_item_changed_fn(on_mode_changed)

    def _build_fps_field(self):
        """Build the FPS input field (for video mode)."""
        with ui.HStack(height=25, spacing=SPACING):
            ui.Label("FPS:", width=50)
            fps_field = ui.IntField(width=80)
            fps_field.model.set_value(self._settings.fps)

            def on_fps_changed(model):
                value = max(1, min(120, model.get_value_as_int()))
                self._settings.fps = value
                self._notify_settings_changed()

            fps_field.model.add_value_changed_fn(on_fps_changed)

    def _build_output_types(self):
        """Build the output types selector (for image mode)."""
        with ui.CollapsableFrame("Image Output Types", collapsed=True):
            with ui.VStack(spacing=3):
                with ui.HStack(height=20):
                    rgb_checkbox = ui.CheckBox(width=20)
                    rgb_checkbox.model.set_value(self._settings.output_rgb)

                    def on_rgb_changed(model):
                        self._settings.output_rgb = model.get_value_as_bool()
                        self._notify_settings_changed()

                    rgb_checkbox.model.add_value_changed_fn(on_rgb_changed)
                    ui.Label("RGB", width=100)

    def _notify_settings_changed(self):
        """Notify that settings have changed."""
        self._callbacks.on_settings_changed(self._index, self._settings)
