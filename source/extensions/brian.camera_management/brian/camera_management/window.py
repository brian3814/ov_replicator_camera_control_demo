"""Main window for the Camera Management extension."""

import asyncio
import os
from typing import Callable, List, Optional

import omni.kit.app
import omni.ui as ui
from omni.kit.window.filepicker import FilePickerDialog

from .controllers import CaptureController, PreviewController
from .models import CameraSettings, CaptureStatus, GlobalSettings
from .styles import COLORS, get_window_style
from .widgets import (
    CameraPanelCallbacks,
    CameraPanelWidget,
    LogPanelWidget,
    StatusBarWidget,
)

__all__ = ["CameraManagementWindow"]


class CameraManagementWindow(ui.Window):
    """Main window for camera capture management.

    Provides UI for adding cameras, configuring capture settings,
    and controlling the capture process.
    """

    # Minimum window dimensions
    MIN_WIDTH = 400
    MIN_HEIGHT = 300

    def __init__(
        self,
        title: str,
        on_visibility_changed: Optional[Callable[[bool], None]] = None,
        **kwargs
    ):
        """Initialize the camera management window.

        Args:
            title: Window title.
            on_visibility_changed: Optional callback when visibility changes.
            **kwargs: Additional arguments passed to ui.Window.
        """
        super().__init__(title, **kwargs)

        self._on_visibility_changed_callback = on_visibility_changed

        # Apply styles
        self.frame.style = get_window_style()

        # Enforce minimum window size
        self.set_width_changed_fn(self._on_width_changed)
        self.set_height_changed_fn(self._on_height_changed)

        # Initialize controllers
        self._preview_controller = PreviewController(
            on_preview_changed=self._on_preview_state_changed
        )
        self._capture_controller = CaptureController(
            on_capture_complete=self._on_capture_complete,
            on_status_changed=self._on_status_changed
        )

        # Initialize state
        self._global_settings = GlobalSettings()
        self._camera_list: List[CameraSettings] = []

        # Set default output folder
        self._global_settings.output_folder = os.path.join(
            os.path.expanduser("~"), "Documents", "CameraCaptures"
        )

        # UI widget references
        self._camera_panels_container: Optional[ui.VStack] = None
        self._output_folder_field: Optional[ui.StringField] = None
        self._start_button: Optional[ui.Button] = None
        self._stop_button: Optional[ui.Button] = None
        self._status_widget: Optional[StatusBarWidget] = None
        self._log_widget: Optional[LogPanelWidget] = None

        # Set the build function for deferred UI construction
        self.frame.set_build_fn(self._build_fn)

    def destroy(self):
        """Cleanup resources when window is destroyed."""
        # Exit preview if active
        self._preview_controller.cleanup()
        self._capture_controller.cleanup()
        super().destroy()

    def _build_fn(self):
        """Build the window UI.

        Called by omni.ui when the window becomes visible.
        """
        with ui.ScrollingFrame():
            with ui.VStack(height=0, spacing=10):
                self._build_title()
                self._build_output_settings()
                self._build_capture_controls()
                self._build_camera_list()
                self._build_log_section()

    def _build_title(self):
        """Build the window title."""
        ui.Label(
            "Camera Capture Settings",
            style={"font_size": 20, "color": COLORS["accent"]},
            alignment=ui.Alignment.CENTER,
            height=30
        )

    def _build_collapsable_header(self, collapsed: bool, title: str):
        """Build a custom title for CollapsableFrame.

        Args:
            collapsed: Whether the frame is currently collapsed.
            title: The title text to display.
        """
        with ui.VStack(height=0):
            ui.Spacer(height=8)
            with ui.HStack():
                ui.Label(title, name="collapsable_name")
                if collapsed:
                    image_name = "collapsable_opened"
                else:
                    image_name = "collapsable_closed"
                ui.Image(name=image_name, width=20, height=20)
            ui.Spacer(height=8)
            ui.Line(style_type_name_override="HeaderLine")

    def _build_output_settings(self):
        """Build the output folder selection row."""
        with ui.VStack(height=30):
            with ui.HStack(spacing=5):
                ui.Label("Output Folder:", width=80)
                self._output_folder_field = ui.StringField()
                self._output_folder_field.model.set_value(self._global_settings.output_folder)
                self._output_folder_field.model.add_value_changed_fn(self._on_output_folder_changed)
                ui.Button(
                    "Change Folder",
                    width=100,
                    clicked_fn=self._on_change_folder
                )

    def _build_capture_controls(self):
        """Build the Start/Stop capture buttons."""

        with ui.VStack():
            # Status bar
            self._status_widget = StatusBarWidget(self._global_settings.status)
            self._status_widget.build()

            ui.Spacer(height=5)

            with ui.HStack(height=35, spacing=10):
                self._start_button = ui.Button(
                    "Start Capture",
                    clicked_fn=self._on_start_capture,
                    style={"background_color": COLORS["primary"]}
                )
                self._stop_button = ui.Button(
                    "Stop Capture",
                    clicked_fn=self._on_stop_capture,
                    style={"background_color": COLORS["background"]}
                )

            with ui.HStack(height=30, spacing=10):
                ui.Button(
                    "Add Camera",
                    clicked_fn=self._on_add_camera,
                    style={"background_color": COLORS["background"]}
                )
                ui.Button(
                    "Clear All",
                    clicked_fn=self._on_clear_all,
                    style={"background_color": COLORS["background"]}
                )

    def _build_camera_list(self):
        """Build the container for camera panels."""
        with ui.CollapsableFrame(
            "Camera List",
            name="group",
            collapsed=False,
            build_header_fn=lambda collapsed, title: self._build_collapsable_header(collapsed, title)
        ):
            self._camera_panels_container = ui.VStack(spacing=5)

    def _build_log_section(self):
        """Build the log section."""
        with ui.CollapsableFrame(
            "Log Output",
            name="group",
            collapsed=False,
            build_header_fn=lambda collapsed, title: self._build_collapsable_header(collapsed, title)
        ):
            with ui.VStack(height=0, spacing=5):
                self._log_widget = LogPanelWidget(max_entries=10, height=150)
                self._log_widget.build()

    def _rebuild_camera_panels(self):
        """Rebuild all camera panels (deferred to next frame)."""
        async def _do_rebuild():
            await omni.kit.app.get_app().next_update_async()
            if not self._camera_panels_container:
                return

            # Clear existing panels
            self._camera_panels_container.clear()

            # Get cameras in use (excluding current selection in each panel)
            all_cameras = self._capture_controller.scan_scene_cameras()

            # Rebuild panels
            with self._camera_panels_container:
                for i, cam_settings in enumerate(self._camera_list):
                    # Get cameras in use by OTHER panels
                    cameras_in_use = {
                        cam.prim_path for j, cam in enumerate(self._camera_list) if j != i
                    }

                    callbacks = CameraPanelCallbacks(
                        on_remove=self._on_remove_camera,
                        on_preview=self._on_preview_camera,
                        on_settings_changed=self._on_camera_settings_changed,
                        on_mode_changed=self._on_capture_mode_changed
                    )

                    panel = CameraPanelWidget(
                        index=i,
                        settings=cam_settings,
                        all_cameras=all_cameras,
                        cameras_in_use=cameras_in_use,
                        is_previewing=self._preview_controller.is_previewing_index(i),
                        callbacks=callbacks
                    )
                    panel.build()

        asyncio.ensure_future(_do_rebuild())

    # Event handlers

    def _on_add_camera(self):
        """Handle Add Camera button click."""
        all_cameras = self._capture_controller.scan_scene_cameras()

        if not all_cameras:
            self._add_log("No cameras found in scene")
            return

        # Find first available camera not already added
        added_paths = {cam.prim_path for cam in self._camera_list}
        available = [c for c in all_cameras if c not in added_paths]

        if not available:
            self._add_log("All cameras already added")
            return

        # Add with first available camera
        new_settings = CameraSettings(
            prim_path=available[0],
            display_name=available[0].split("/")[-1]
        )
        self._camera_list.append(new_settings)
        self._rebuild_camera_panels()
        self._add_log(f"Added camera: {new_settings.display_name}")

    def _on_remove_camera(self, index: int):
        """Handle camera removal.

        Args:
            index: Index of the camera to remove.
        """
        if 0 <= index < len(self._camera_list):
            # Notify preview controller
            self._preview_controller.on_camera_removed(index)

            removed = self._camera_list.pop(index)
            self._rebuild_camera_panels()
            self._add_log(f"Removed camera: {removed.display_name}")

    def _on_clear_all(self):
        """Handle Clear All button click."""
        # Exit preview if active
        self._preview_controller.cleanup()
        self._camera_list.clear()
        self._rebuild_camera_panels()
        self._add_log("Cleared all cameras")

    def _on_preview_camera(self, index: int):
        """Handle camera preview toggle.

        Args:
            index: Index of the camera to preview.
        """
        if index >= len(self._camera_list):
            return

        cam = self._camera_list[index]
        is_now_previewing = self._preview_controller.toggle_preview(index, cam.prim_path)

        if is_now_previewing:
            self._add_log(f"Preview: {cam.display_name}")
        else:
            self._add_log("Exited preview")

    def _on_preview_state_changed(self, preview_index: Optional[int]):
        """Handle preview state changes.

        Args:
            preview_index: Index of camera being previewed, or None.
        """
        self._rebuild_camera_panels()

    def _on_camera_settings_changed(self, index: int, settings: CameraSettings):
        """Handle camera settings changes.

        Args:
            index: Index of the camera.
            settings: Updated settings.
        """
        if 0 <= index < len(self._camera_list):
            self._camera_list[index] = settings

    def _on_capture_mode_changed(self, index: int):
        """Handle capture mode change (rebuild UI to show/hide FPS).

        Args:
            index: Index of the camera.
        """
        self._rebuild_camera_panels()

    def _on_change_folder(self):
        """Handle Change Folder button click."""
        def on_folder_selected(filename: str, dirname: str):
            self._global_settings.output_folder = dirname
            if self._output_folder_field:
                self._output_folder_field.model.set_value(dirname)
            dialog.hide()

        def on_cancel(filename: str, dirname: str):
            dialog.hide()

        def on_filter_item(item) -> bool:
            """Only show folders, not files."""
            if not item or item.is_folder:
                return True
            return False

        dialog = FilePickerDialog(
            "Select Output Folder",
            apply_button_label="Confirm",
            click_apply_handler=on_folder_selected,
            click_cancel_handler=on_cancel,
            item_filter_fn=on_filter_item,
            allow_multi_selection=False
        )
        dialog.show()

    def _on_output_folder_changed(self, model):
        """Handle output folder text field change.

        Args:
            model: The field's value model.
        """
        self._global_settings.output_folder = model.get_value_as_string()

    def _on_start_capture(self):
        """Handle Start Capture button click."""
        if not self._camera_list:
            self._add_log("No cameras configured")
            return

        if not self._global_settings.output_folder:
            self._add_log("Output folder not specified")
            return

        success = self._capture_controller.start(
            self._camera_list,
            self._global_settings.output_folder
        )

        if success:
            self._add_log("Capture started")
        else:
            self._add_log("Failed to start capture")

    def _on_stop_capture(self):
        """Handle Stop Capture button click."""
        self._capture_controller.stop()
        self._add_log("Capture stopped")

    def _on_capture_complete(self, camera_name: str, file_path: str):
        """Handle capture completion callback.

        Args:
            camera_name: Name of the camera that captured.
            file_path: Path to the captured file.
        """
        self._add_log(f"Captured {camera_name} -> {os.path.basename(file_path)}")

    def _on_status_changed(self, status: CaptureStatus):
        """Handle status change from capture controller.

        Args:
            status: The new capture status.
        """
        self._global_settings.status = status
        if self._status_widget:
            self._status_widget.set_status(status)
        self._update_button_states()

    def _update_button_states(self):
        """Update button visual states based on capture status."""
        is_capturing = self._capture_controller.is_capturing

        if self._start_button:
            if is_capturing:
                self._start_button.style = {"background_color": COLORS["background"]}
            else:
                self._start_button.style = {"background_color": COLORS["primary"]}

        if self._stop_button:
            if is_capturing:
                self._stop_button.style = {"background_color": COLORS["danger"]}
            else:
                self._stop_button.style = {"background_color": COLORS["background"]}

    def _on_width_changed(self, width: float):
        """Enforce minimum width constraint.

        Args:
            width: The new window width.
        """
        if width < self.MIN_WIDTH:
            self.width = self.MIN_WIDTH

    def _on_height_changed(self, height: float):
        """Enforce minimum height constraint.

        Args:
            height: The new window height.
        """
        if height < self.MIN_HEIGHT:
            self.height = self.MIN_HEIGHT

    def _add_log(self, message: str):
        """Add a log entry.

        Args:
            message: The message to log.
        """
        if self._log_widget:
            self._log_widget.add_entry(message)
