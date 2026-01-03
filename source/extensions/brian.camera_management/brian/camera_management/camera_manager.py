import asyncio
import os
from datetime import datetime
from typing import List, Dict, Optional, Callable, Any

import omni.usd
import omni.kit.app
import omni.replicator.core as rep
from pxr import UsdGeom

from .models import CameraSettings, CaptureStatus, CaptureMode
from .video_writer import VideoWriter


class CameraManager:
    """Manages cameras and image capture using omni.replicator."""

    def __init__(self, on_capture_callback: Optional[Callable[[str, str], None]] = None):
        """
        Initialize the camera manager.

        Args:
            on_capture_callback: Callback function(camera_name, file_path) called after each capture.
        """
        self._render_products: Dict[str, Any] = {}
        self._writers: Dict[str, Any] = {}
        self._update_subscription = None
        self._frame_count: int = 0
        self._active_cameras: List[CameraSettings] = []
        self._output_folder: str = ""
        self._on_capture_callback = on_capture_callback
        self._is_capturing: bool = False

    def scan_scene_cameras(self) -> List[str]:
        """
        Traverse USD stage and return all Camera prim paths.

        Returns:
            List of camera prim paths found in the scene.
        """
        context = omni.usd.get_context()
        stage = context.get_stage()
        if not stage:
            return []

        camera_prims = []
        for prim in stage.Traverse():
            if prim.IsA(UsdGeom.Camera):
                camera_prims.append(str(prim.GetPath()))

        return camera_prims

    def create_render_product(self, camera_settings: CameraSettings) -> bool:
        """
        Create render product for a camera using omni.replicator.

        Args:
            camera_settings: Settings for the camera to create render product for.

        Returns:
            True if successful, False otherwise.
        """
        try:
            render_product = rep.create.render_product(
                camera_settings.prim_path,
                (camera_settings.width, camera_settings.height)
            )
            self._render_products[camera_settings.prim_path] = render_product
            return True
        except Exception as e:
            print(f"[brian.camera_management] Error creating render product: {e}")
            return False

    def _setup_writer(self, camera_settings: CameraSettings, output_folder: str) -> bool:
        """
        Set up writer for a camera (BasicWriter for images, VideoWriter for video).

        Args:
            camera_settings: Settings for the camera.
            output_folder: Base output folder path.

        Returns:
            True if successful, False otherwise.
        """
        try:
            camera_name = camera_settings.prim_path.split("/")[-1]
            camera_output = os.path.join(output_folder, camera_name)
            os.makedirs(camera_output, exist_ok=True)

            if camera_settings.capture_mode == CaptureMode.VIDEO:
                # Video mode - use custom VideoWriter
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                video_path = os.path.join(camera_output, f"{camera_name}_{timestamp}.mp4")
                writer = VideoWriter(
                    video_filepath=video_path,
                    fps=camera_settings.fps,
                    width=camera_settings.width,
                    height=camera_settings.height
                )
            else:
                # Image mode - use BasicWriter
                writer = rep.WriterRegistry.get("BasicWriter")
                writer.initialize(
                    output_dir=camera_output,
                    rgb=camera_settings.output_rgb,
                    frame_padding=6
                )

            render_product = self._render_products.get(camera_settings.prim_path)
            if render_product:
                writer.attach([render_product])
                self._writers[camera_settings.prim_path] = writer
                return True
            return False
        except Exception as e:
            print(f"[brian.camera_management] Error setting up writer: {e}")
            return False

    def start_capture(self, cameras: List[CameraSettings], output_folder: str) -> bool:
        """
        Start capture loop for all enabled cameras.

        Args:
            cameras: List of camera settings to capture from.
            output_folder: Output folder path for captured images.

        Returns:
            True if capture started successfully, False otherwise.
        """
        if self._is_capturing:
            print("[brian.camera_management] Capture already in progress")
            return False

        if not output_folder:
            print("[brian.camera_management] Output folder not specified")
            return False

        self._output_folder = output_folder
        self._active_cameras = [cam for cam in cameras if cam.enabled]

        if not self._active_cameras:
            print("[brian.camera_management] No enabled cameras to capture")
            return False

        # Create output folder with timestamp
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        self._output_folder = os.path.join(output_folder, f"capture_{timestamp}")
        os.makedirs(self._output_folder, exist_ok=True)

        # Set up render products and writers for all enabled cameras
        for cam in self._active_cameras:
            cam.frame_counter = 0
            if not self.create_render_product(cam):
                self.stop_capture()
                return False
            if not self._setup_writer(cam, self._output_folder):
                self.stop_capture()
                return False

        # Subscribe to update events
        update_stream = omni.kit.app.get_app().get_update_event_stream()
        self._update_subscription = update_stream.create_subscription_to_pop(
            self._on_update,
            name="CameraCapture_Update"
        )
        self._frame_count = 0
        self._is_capturing = True

        print(f"[brian.camera_management] Started capture for {len(self._active_cameras)} cameras")
        return True

    def _on_update(self, event) -> None:
        """Frame update callback - check intervals and capture."""
        if not self._is_capturing:
            return

        self._frame_count += 1

        for camera in self._active_cameras:
            if not camera.enabled:
                continue

            camera.frame_counter += 1
            if camera.frame_counter >= camera.interval_frames:
                camera.frame_counter = 0
                self._trigger_capture(camera)

    def _trigger_capture(self, camera: CameraSettings) -> None:
        """
        Trigger a single frame capture.

        Args:
            camera: Camera settings for the camera to capture from.
        """
        async def _do_capture():
            try:
                # Step the orchestrator to capture (async version for Kit)
                await rep.orchestrator.step_async()

                # Construct expected output path
                camera_name = camera.prim_path.split("/")[-1]
                # BasicWriter uses frame number in filename
                output_path = os.path.join(
                    self._output_folder,
                    camera_name,
                    f"rgb_{self._frame_count:06d}.png"
                )
                camera.last_capture_path = output_path

                if self._on_capture_callback:
                    self._on_capture_callback(camera.display_name, output_path)

            except Exception as e:
                print(f"[brian.camera_management] Capture error for {camera.display_name}: {e}")

        asyncio.ensure_future(_do_capture())

    def stop_capture(self) -> None:
        """Stop capture and clean up resources."""
        self._is_capturing = False

        # Unsubscribe from updates
        if self._update_subscription:
            self._update_subscription = None

        # Finalize and detach writers
        for prim_path, writer in self._writers.items():
            try:
                # Call on_final_frame for VideoWriter to finalize encoding
                if hasattr(writer, 'on_final_frame'):
                    writer.on_final_frame()
                writer.detach()
            except Exception as e:
                print(f"[brian.camera_management] Error cleaning up writer: {e}")

        self._writers.clear()
        self._render_products.clear()
        self._active_cameras.clear()

        print("[brian.camera_management] Capture stopped")

    @property
    def is_capturing(self) -> bool:
        """Return whether capture is currently active."""
        return self._is_capturing

    def cleanup(self) -> None:
        """Release all resources."""
        self.stop_capture()
