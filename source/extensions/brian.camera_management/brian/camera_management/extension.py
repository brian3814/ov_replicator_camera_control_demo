# SPDX-FileCopyrightText: Copyright (c) 2024 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: LicenseRef-NvidiaProprietary
#
# NVIDIA CORPORATION, its affiliates and licensors retain all intellectual
# property and proprietary rights in and to this material, related
# documentation and any modifications thereto. Any use, reproduction,
# disclosure or distribution of this material and related documentation
# without an express license agreement from NVIDIA CORPORATION or
# its affiliates is strictly prohibited.

import asyncio
import os
from datetime import datetime
from typing import List, Optional

import omni.ext
import omni.kit.app
import omni.ui as ui
from omni.kit.window.filepicker import FilePickerDialog
from omni.kit.viewport.utility import get_active_viewport

from .models import CameraSettings, GlobalSettings, CaptureStatus
from .camera_manager import CameraManager


class CameraManagementExtension(omni.ext.IExt):
    """Extension for managing multiple cameras and capturing images."""

    def on_startup(self, ext_id: str):
        """Called when the extension is loaded."""
        print("[brian.camera_management] Extension startup")

        self._window: Optional[ui.Window] = None
        self._camera_manager = CameraManager(on_capture_callback=self._on_capture_complete)
        self._global_settings = GlobalSettings()
        self._camera_list: List[CameraSettings] = []

        # UI references
        self._camera_panels_container: Optional[ui.VStack] = None
        self._output_folder_field: Optional[ui.StringField] = None
        self._status_label: Optional[ui.Label] = None
        self._log_label: Optional[ui.Label] = None
        self._start_button: Optional[ui.Button] = None
        self._stop_button: Optional[ui.Button] = None

        # Log entries
        self._log_entries: List[str] = []
        self._max_log_entries = 10

        # Preview state
        self._preview_active_index: Optional[int] = None
        self._original_camera_path: Optional[str] = None

        # Set default output folder
        self._global_settings.output_folder = os.path.join(
            os.path.expanduser("~"), "Documents", "CameraCaptures"
        )

        self._build_ui()

    def on_shutdown(self):
        """Called when the extension is unloaded."""
        print("[brian.camera_management] Extension shutdown")
        # Exit preview if active
        if self._preview_active_index is not None:
            self._exit_preview()
        self._camera_manager.cleanup()
        if self._window:
            self._window.destroy()
            self._window = None

    def _build_ui(self):
        """Build the main window UI."""
        self._window = ui.Window("Camera Capture Tool", width=500, height=600)

        with self._window.frame:
            with ui.ScrollingFrame():
                with ui.VStack(spacing=10):
                    ui.Spacer(height=5)

                    # Title
                    ui.Label(
                        "Camera Capture Settings",
                        style={"font_size": 20, "color": 0xFF00CC88},
                        alignment=ui.Alignment.CENTER,
                        height=30
                    )

                    ui.Spacer(height=5)

                    # Add Camera / Clear All buttons
                    with ui.HStack(height=30, spacing=10):
                        ui.Button(
                            "Add Camera",
                            clicked_fn=self._on_add_camera,
                            style={"background_color": 0xFF404040}
                        )
                        ui.Button(
                            "Clear All",
                            clicked_fn=self._on_clear_all,
                            style={"background_color": 0xFF404040}
                        )

                    ui.Spacer(height=5)

                    # Output folder
                    with ui.HStack(height=25, spacing=5):
                        ui.Label("Output Folder:", width=80)
                        self._output_folder_field = ui.StringField()
                        self._output_folder_field.model.set_value(self._global_settings.output_folder)
                        self._output_folder_field.model.add_value_changed_fn(self._on_output_folder_changed)
                        ui.Button(
                            "Change Folder",
                            width=100,
                            clicked_fn=self._on_change_folder
                        )

                    ui.Spacer(height=5)

                    # Start / Stop buttons
                    with ui.HStack(height=35, spacing=10):
                        self._start_button = ui.Button(
                            "Start Capture",
                            clicked_fn=self._on_start_capture,
                            style={"background_color": 0xFF2E8B57}
                        )
                        self._stop_button = ui.Button(
                            "Stop Capture",
                            clicked_fn=self._on_stop_capture,
                            style={"background_color": 0xFF404040}
                        )

                    ui.Spacer(height=10)

                    # Camera panels container
                    self._camera_panels_container = ui.VStack(spacing=5)

                    ui.Spacer(height=10)

                    # Status section
                    with ui.VStack(spacing=5):
                        with ui.HStack(height=25):
                            ui.Label("Status:", width=50)
                            self._status_label = ui.Label(
                                self._global_settings.status.value,
                                style={"color": 0xFFCCCCCC}
                            )

                        ui.Spacer(height=5)

                        # Log display
                        ui.Label("Capture Log:", height=20)
                        with ui.ScrollingFrame(
                            height=150,
                            horizontal_scrollbar_policy=ui.ScrollBarPolicy.SCROLLBAR_ALWAYS_OFF,
                            vertical_scrollbar_policy=ui.ScrollBarPolicy.SCROLLBAR_AS_NEEDED,
                            style={"background_color": 0xFF1A1A1A}
                        ):
                            self._log_label = ui.Label(
                                "",
                                word_wrap=True,
                                alignment=ui.Alignment.LEFT_TOP,
                                style={"font_size": 12}
                            )

                    ui.Spacer(height=10)

    def _build_camera_panel(self, index: int, camera_settings: CameraSettings) -> ui.CollapsableFrame:
        """
        Build a collapsible camera settings panel.

        Args:
            index: Index of the camera in the list.
            camera_settings: Settings for this camera.

        Returns:
            The CollapsableFrame widget.
        """
        all_cameras = self._camera_manager.scan_scene_cameras()

        frame = ui.CollapsableFrame(
            f"Camera_{index}",
            collapsed=False,
            style={"background_color": 0xFF2A2A2A}
        )

        with frame:
            with ui.VStack(spacing=5, style={"margin": 5}):
                # Camera selector row
                with ui.HStack(height=25, spacing=5):
                    ui.Label("Camera:", width=70)

                    if all_cameras:
                        # Get cameras used by OTHER panels (not this one)
                        other_panel_cameras = {
                            cam.prim_path for i, cam in enumerate(self._camera_list) if i != index
                        }

                        # Build dropdown with grayed-out items for cameras in use
                        display_items = []
                        selectable_indices = []
                        current_index = 0

                        for i, cam_path in enumerate(all_cameras):
                            cam_name = cam_path.split("/")[-1]
                            if cam_path in other_panel_cameras:
                                display_items.append(f"{cam_name} (in use)")
                            else:
                                display_items.append(cam_name)
                                selectable_indices.append(i)

                            # Track current camera's index
                            if cam_path == camera_settings.prim_path:
                                current_index = i

                        combo = ui.ComboBox(current_index, *display_items)

                        def on_camera_changed(model, idx=index, cams=all_cameras, valid=selectable_indices):
                            selected = model.get_item_value_model().get_value_as_int()
                            if selected in valid:
                                self._camera_list[idx].prim_path = cams[selected]
                                self._camera_list[idx].display_name = cams[selected].split("/")[-1]
                            else:
                                # Reset to current camera (reject selection of in-use camera)
                                try:
                                    current_idx = cams.index(self._camera_list[idx].prim_path)
                                    model.get_item_value_model().set_value(current_idx)
                                except ValueError:
                                    pass

                        combo.model.add_item_changed_fn(on_camera_changed)
                    else:
                        ui.Label("No cameras in scene", style={"color": 0xFFFF6666})

                    ui.Button(
                        "Remove",
                        width=80,
                        clicked_fn=lambda idx=index: self._on_remove_camera(idx)
                    )

                # Interval row
                with ui.HStack(height=25, spacing=5):
                    ui.Label("Interval (Frames):", width=120)
                    interval_field = ui.IntField(width=80)
                    interval_field.model.set_value(camera_settings.interval_frames)

                    def on_interval_changed(model, idx=index):
                        self._camera_list[idx].interval_frames = model.get_value_as_int()

                    interval_field.model.add_value_changed_fn(on_interval_changed)

                # Width controls with synchronized slider and field
                with ui.HStack(height=25, spacing=5):
                    ui.Label("Width:", width=50)
                    width_slider = ui.IntSlider(min=64, max=4096)
                    width_slider.model.set_value(camera_settings.width)
                    width_field = ui.IntField(width=80)
                    width_field.model.set_value(camera_settings.width)

                    # Track if we're updating to prevent infinite loops
                    width_updating = [False]

                    def on_width_slider_changed(model, idx=index, field=width_field, updating=width_updating):
                        if updating[0]:
                            return
                        updating[0] = True
                        value = model.as_int
                        self._camera_list[idx].width = value
                        field.model.set_value(value)
                        updating[0] = False

                    def on_width_field_changed(model, idx=index, slider=width_slider, updating=width_updating):
                        if updating[0]:
                            return
                        updating[0] = True
                        value = model.get_value_as_int()
                        # Clamp to slider range
                        value = max(64, min(4096, value))
                        self._camera_list[idx].width = value
                        slider.model.set_value(value)
                        updating[0] = False

                    width_slider.model.add_value_changed_fn(on_width_slider_changed)
                    width_field.model.add_value_changed_fn(on_width_field_changed)

                # Height controls with synchronized slider and field
                with ui.HStack(height=25, spacing=5):
                    ui.Label("Height:", width=50)
                    height_slider = ui.IntSlider(min=64, max=4096)
                    height_slider.model.set_value(camera_settings.height)
                    height_field = ui.IntField(width=80)
                    height_field.model.set_value(camera_settings.height)

                    height_updating = [False]

                    def on_height_slider_changed(model, idx=index, field=height_field, updating=height_updating):
                        if updating[0]:
                            return
                        updating[0] = True
                        value = model.as_int
                        self._camera_list[idx].height = value
                        field.model.set_value(value)
                        updating[0] = False

                    def on_height_field_changed(model, idx=index, slider=height_slider, updating=height_updating):
                        if updating[0]:
                            return
                        updating[0] = True
                        value = model.get_value_as_int()
                        value = max(64, min(4096, value))
                        self._camera_list[idx].height = value
                        slider.model.set_value(value)
                        updating[0] = False

                    height_slider.model.add_value_changed_fn(on_height_slider_changed)
                    height_field.model.add_value_changed_fn(on_height_field_changed)

                # Preview button
                is_previewing = (self._preview_active_index == index)
                preview_btn_text = "Exit Preview" if is_previewing else "Preview"
                preview_btn_color = 0xFF8B2E2E if is_previewing else 0xFF2E8B57

                ui.Button(
                    preview_btn_text,
                    height=25,
                    clicked_fn=lambda idx=index: self._on_preview_camera(idx),
                    style={"background_color": preview_btn_color}
                )

                # Image output types (collapsible)
                with ui.CollapsableFrame("Image Output Types", collapsed=True):
                    with ui.VStack(spacing=3):
                        with ui.HStack(height=20):
                            rgb_checkbox = ui.CheckBox(width=20)
                            rgb_checkbox.model.set_value(camera_settings.output_rgb)

                            def on_rgb_changed(model, idx=index):
                                self._camera_list[idx].output_rgb = model.get_value_as_bool()

                            rgb_checkbox.model.add_value_changed_fn(on_rgb_changed)
                            ui.Label("RGB", width=100)

        return frame

    def _rebuild_camera_panels(self):
        """Rebuild all camera panels in the UI (deferred to next frame)."""
        async def _do_rebuild():
            await omni.kit.app.get_app().next_update_async()
            if not self._camera_panels_container:
                return
            # Clear existing panels
            self._camera_panels_container.clear()
            # Rebuild panels
            with self._camera_panels_container:
                for i, cam_settings in enumerate(self._camera_list):
                    self._build_camera_panel(i, cam_settings)
        asyncio.ensure_future(_do_rebuild())

    def _on_add_camera(self):
        """Add a new camera panel directly to the container."""
        all_cameras = self._camera_manager.scan_scene_cameras()

        if not all_cameras:
            self._add_log_entry("No cameras found in scene")
            return

        # Find first available camera not already added
        added_paths = {cam.prim_path for cam in self._camera_list}
        available = [c for c in all_cameras if c not in added_paths]

        if not available:
            self._add_log_entry("All cameras already added")
            return

        # Add with first available camera
        new_settings = CameraSettings(
            prim_path=available[0],
            display_name=available[0].split("/")[-1]
        )
        self._camera_list.append(new_settings)
        self._rebuild_camera_panels()
        self._add_log_entry(f"Added camera: {new_settings.display_name}")

    def _on_remove_camera(self, index: int):
        """Remove a camera from the capture list."""
        if 0 <= index < len(self._camera_list):
            # Exit preview if removing the previewed camera
            if self._preview_active_index == index:
                self._exit_preview()
            elif self._preview_active_index is not None and self._preview_active_index > index:
                # Adjust preview index if removing a camera before it
                self._preview_active_index -= 1

            removed = self._camera_list.pop(index)
            self._rebuild_camera_panels()
            self._add_log_entry(f"Removed camera: {removed.display_name}")

    def _on_clear_all(self):
        """Remove all cameras from the list."""
        # Exit preview if active
        if self._preview_active_index is not None:
            self._exit_preview()
        self._camera_list.clear()
        self._rebuild_camera_panels()
        self._add_log_entry("Cleared all cameras")

    def _on_preview_camera(self, index: int):
        """Toggle preview for a camera panel."""
        if self._preview_active_index == index:
            self._exit_preview()
        else:
            self._start_preview(index)

    def _start_preview(self, index: int):
        """Switch viewport to camera at configured resolution."""
        if index >= len(self._camera_list):
            return

        # Exit any existing preview first
        if self._preview_active_index is not None:
            self._exit_preview()

        try:
            viewport = get_active_viewport()
            if viewport is None:
                self._add_log_entry("No active viewport found")
                return

            # Save current viewport camera
            self._original_camera_path = viewport.camera_path

            # Set viewport to selected camera
            cam = self._camera_list[index]
            viewport.camera_path = cam.prim_path

            self._preview_active_index = index
            self._rebuild_camera_panels()
            self._add_log_entry(f"Preview: {cam.display_name}")

        except Exception as e:
            self._add_log_entry(f"Preview error: {e}")

    def _exit_preview(self):
        """Restore original camera."""
        try:
            if self._original_camera_path:
                viewport = get_active_viewport()
                if viewport:
                    viewport.camera_path = self._original_camera_path

            self._add_log_entry("Exited preview")

        except Exception as e:
            self._add_log_entry(f"Exit preview error: {e}")

        self._preview_active_index = None
        self._original_camera_path = None
        self._rebuild_camera_panels()

    def _on_change_folder(self):
        """Open folder picker dialog."""
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
        """Handle output folder text field change."""
        self._global_settings.output_folder = model.get_value_as_string()

    def _on_start_capture(self):
        """Start capturing from all enabled cameras."""
        if not self._camera_list:
            self._add_log_entry("No cameras configured")
            return

        if not self._global_settings.output_folder:
            self._add_log_entry("Output folder not specified")
            return

        success = self._camera_manager.start_capture(
            self._camera_list,
            self._global_settings.output_folder
        )

        if success:
            self._global_settings.status = CaptureStatus.CAPTURING
            self._update_status()
            self._add_log_entry("Capture started")
            self._update_button_states()
        else:
            self._global_settings.status = CaptureStatus.ERROR
            self._update_status()
            self._add_log_entry("Failed to start capture")

    def _on_stop_capture(self):
        """Stop all capture operations."""
        self._camera_manager.stop_capture()
        self._global_settings.status = CaptureStatus.STOPPED
        self._update_status()
        self._add_log_entry("Capture stopped")
        self._update_button_states()

    def _on_capture_complete(self, camera_name: str, file_path: str):
        """Callback when a capture is completed."""
        self._add_log_entry(f"Captured {camera_name} -> {os.path.basename(file_path)}")

    def _update_status(self):
        """Update the status label."""
        if self._status_label:
            status = self._global_settings.status
            self._status_label.text = status.value

            # Update color based on status
            if status == CaptureStatus.CAPTURING:
                self._status_label.style = {"color": 0xFF00FF00}
            elif status == CaptureStatus.ERROR:
                self._status_label.style = {"color": 0xFFFF0000}
            else:
                self._status_label.style = {"color": 0xFFCCCCCC}

    def _update_button_states(self):
        """Update button visual states based on capture status."""
        is_capturing = self._camera_manager.is_capturing

        if self._start_button:
            if is_capturing:
                self._start_button.style = {"background_color": 0xFF404040}
            else:
                self._start_button.style = {"background_color": 0xFF2E8B57}

        if self._stop_button:
            if is_capturing:
                self._stop_button.style = {"background_color": 0xFF8B2E2E}
            else:
                self._stop_button.style = {"background_color": 0xFF404040}

    def _add_log_entry(self, message: str):
        """Add an entry to the log display."""
        timestamp = datetime.now().strftime("%H:%M:%S")
        entry = f"[{timestamp}] {message}"
        self._log_entries.append(entry)

        # Keep only last N entries
        if len(self._log_entries) > self._max_log_entries:
            self._log_entries = self._log_entries[-self._max_log_entries:]

        # Update log label
        if self._log_label:
            self._log_label.text = "\n".join(self._log_entries)
