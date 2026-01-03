"""Camera panel widget for individual camera settings."""

import os
import subprocess
import sys
from dataclasses import dataclass
from typing import Callable, List, Optional, Set

import omni.ui as ui

from ..models import CameraSettings, CaptureMode
from ..styles import COLORS, SPACING
from ..usd_camera_utils import UsdCameraUtils
from .resolution_widget import ResolutionWidget
from .camera_property_widget import CameraPropertyWidget

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
        self._status_label: Optional[ui.Label] = None
        self._last_capture_label: Optional[ui.Label] = None

        # Camera property widgets
        self._focal_length_widget: Optional[CameraPropertyWidget] = None
        self._focus_distance_widget: Optional[CameraPropertyWidget] = None
        self._exposure_widget: Optional[CameraPropertyWidget] = None
        self._fov_widget: Optional[CameraPropertyWidget] = None

        # Capture state tracking
        self._is_capturing: bool = False

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
                self._build_status_row()
                self._build_last_capture_row()
                self._build_fps_row()
                self._build_resolution_controls()
                self._build_camera_properties()
                self._build_preview_button()
                self._build_capture_mode()

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
                self._update_status_display()
                self._notify_settings_changed()

            enabled_combo.model.add_item_changed_fn(on_enabled_changed)

    def _build_status_row(self):
        """Build the capture status row."""
        with ui.HStack(height=25, spacing=SPACING):
            ui.Label("Status:", width=100)
            self._status_label = ui.Label("Idle", style={"color": COLORS["text_muted"]})

    def set_capture_status(self, is_capturing: bool):
        """Update the capture status display.

        Args:
            is_capturing: Whether capture is currently active.
        """
        self._is_capturing = is_capturing
        self._update_status_display()

    def _update_status_display(self):
        """Update the status label based on current capture and enabled state."""
        if self._status_label:
            if self._is_capturing and self._settings.enabled:
                self._status_label.text = "Capturing"
                self._status_label.style = {"color": COLORS["status_capturing"]}
            else:
                self._status_label.text = "Idle"
                self._status_label.style = {"color": COLORS["text_muted"]}

    def _build_last_capture_row(self):
        """Build the last captured file path row."""
        with ui.HStack(height=25, spacing=SPACING):
            ui.Label("Last Captured:", width=70)
            path_text = self._settings.last_capture_path or ""
            self._last_capture_label = ui.Label(
                path_text,
                elided_text=True,
                style={"color": COLORS["text_muted"]}
            )
            ui.Button(
                "Open",
                width=50,
                clicked_fn=self._open_last_capture
            )

    def _open_last_capture(self):
        """Open the last captured file in the system default application."""
        last_captured_path = self._settings.last_capture_path
        print(f'Opening last captured file from {self._settings.prim_path}: {last_captured_path}')

        if last_captured_path and os.path.exists(last_captured_path):
            if os.name == "nt":  # Windows
                os.startfile(last_captured_path)
            elif os.name == "posix":  # macOS/Linux
                subprocess.run(["open" if sys.platform == "darwin" else "xdg-open", last_captured_path])

    def update_last_capture_path(self, path: Optional[str] = None):
        """Update the last captured file path display.

        Args:
            path: The path to display. If None, uses settings.last_capture_path.
        """
        if path is not None:
            self._settings.last_capture_path = path
        if self._last_capture_label:
            self._last_capture_label.text = self._settings.last_capture_path or ""

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

    def _build_camera_properties(self):
        """Build camera optical property controls in a collapsible section."""
        with ui.CollapsableFrame("Camera Properties", collapsed=True):
            with ui.VStack(spacing=SPACING):
                # FOV control (linked to focal length)
                self._fov_widget = CameraPropertyWidget(
                    label="FOV",
                    min_val=10.0,
                    max_val=120.0,
                    initial=self._settings.fov,
                    step=1.0,
                    precision=1,
                    unit="deg",
                    on_change=self._on_fov_changed
                )
                self._fov_widget.build()

                # Focal Length control (linked to FOV)
                self._focal_length_widget = CameraPropertyWidget(
                    label="Focal Length",
                    min_val=10.0,
                    max_val=300.0,
                    initial=self._settings.focal_length,
                    step=1.0,
                    precision=1,
                    unit="mm",
                    on_change=self._on_focal_length_changed
                )
                self._focal_length_widget.build()

                # Focus Distance control
                self._focus_distance_widget = CameraPropertyWidget(
                    label="Focus Distance",
                    min_val=10.0,
                    max_val=10000.0,
                    initial=self._settings.focus_distance,
                    step=10.0,
                    precision=0,
                    unit="cm",
                    on_change=self._on_focus_distance_changed
                )
                self._focus_distance_widget.build()

                # Exposure control
                self._exposure_widget = CameraPropertyWidget(
                    label="Exposure",
                    min_val=-10.0,
                    max_val=10.0,
                    initial=self._settings.exposure,
                    step=0.1,
                    precision=1,
                    unit="EV",
                    on_change=self._on_exposure_changed
                )
                self._exposure_widget.build()

                # Sync from USD button
                ui.Button(
                    "Sync from Scene",
                    height=25,
                    clicked_fn=self._sync_from_usd,
                    tooltip="Load current camera values from USD scene"
                )

    def _on_fov_changed(self, value: float):
        """Handle FOV change - calculate focal length and update USD.

        Args:
            value: The new FOV in degrees.
        """
        self._settings.fov = value
        # Calculate corresponding focal length
        focal_length = UsdCameraUtils.calculate_focal_length(value)
        self._settings.focal_length = focal_length
        # Update USD
        UsdCameraUtils.set_focal_length(self._settings.prim_path, focal_length)
        # Update focal length widget display
        if self._focal_length_widget:
            self._focal_length_widget.set_value(focal_length)
        self._notify_settings_changed()

    def _on_focal_length_changed(self, value: float):
        """Handle focal length change - update USD and sync FOV.

        Args:
            value: The new focal length in mm.
        """
        self._settings.focal_length = value
        UsdCameraUtils.set_focal_length(self._settings.prim_path, value)
        # Calculate corresponding FOV and update widget
        fov = UsdCameraUtils.calculate_fov(value)
        self._settings.fov = fov
        if self._fov_widget:
            self._fov_widget.set_value(fov)
        self._notify_settings_changed()

    def _on_focus_distance_changed(self, value: float):
        """Handle focus distance change - update USD immediately.

        Args:
            value: The new focus distance in cm.
        """
        self._settings.focus_distance = value
        UsdCameraUtils.set_focus_distance(self._settings.prim_path, value)
        self._notify_settings_changed()

    def _on_exposure_changed(self, value: float):
        """Handle exposure change - update USD immediately.

        Args:
            value: The new exposure value in EV.
        """
        self._settings.exposure = value
        UsdCameraUtils.set_exposure(self._settings.prim_path, value)
        self._notify_settings_changed()

    def _sync_from_usd(self):
        """Sync widget values from current USD camera properties."""
        if UsdCameraUtils.sync_settings_from_usd(self._settings.prim_path, self._settings):
            # Update widget displays
            if self._fov_widget:
                self._fov_widget.set_value(self._settings.fov)
            if self._focal_length_widget:
                self._focal_length_widget.set_value(self._settings.focal_length)
            if self._focus_distance_widget:
                self._focus_distance_widget.set_value(self._settings.focus_distance)
            if self._exposure_widget:
                self._exposure_widget.set_value(self._settings.exposure)
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


    def _notify_settings_changed(self):
        """Notify that settings have changed."""
        self._callbacks.on_settings_changed(self._index, self._settings)
