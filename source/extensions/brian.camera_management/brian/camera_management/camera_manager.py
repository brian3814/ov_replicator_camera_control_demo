import asyncio
import os
from datetime import datetime
from typing import List, Dict, Optional, Callable, Any

import omni.usd
import omni.kit.app
import omni.replicator.core as rep
from pxr import UsdGeom

from .models import CameraSettings, CaptureStatus, CaptureMode
from .image_writer import ImageWriter
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

        # Time-based FPS capture tracking
        self._elapsed_time: Dict[str, float] = {}  # prim_path -> accumulated time
        self._measured_app_fps: float = 60.0  # Measured app frame rate
        self._fps_sample_count: int = 0
        self._fps_sample_time: float = 0.0

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
                # Image mode - use custom ImageWriter
                writer = ImageWriter(
                    output_dir=camera_output,
                    camera_name=camera_name,
                    image_format="png"
                )

            render_product = self._render_products.get(camera_settings.prim_path)
            self._writers[camera_settings.prim_path] = writer

            if render_product and camera_settings.enabled:
                writer.attach([render_product])
            return True

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
        self._active_cameras = list(cameras)  # Create a copy to avoid clearing original

        if not any(cam.enabled for cam in self._active_cameras):
            print("[brian.camera_management] No enabled cameras to capture")
            return False

        # Create output folder with timestamp
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        self._output_folder = os.path.join(output_folder, f"capture_{timestamp}")
        os.makedirs(self._output_folder, exist_ok=True)

        # Set up render products and writers for ALL cameras (enabled check is in _on_update)
        for cam in self._active_cameras:
            cam.frame_counter = 0
            self._elapsed_time[cam.prim_path] = 0.0  # Initialize time tracking
            if not self.create_render_product(cam):
                self.stop_capture()
                return False
            if not self._setup_writer(cam, self._output_folder):
                self.stop_capture()
                return False

        # Reset FPS measurement
        self._fps_sample_count = 0
        self._fps_sample_time = 0.0

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
        """Frame update callback - use time-based capture for accurate FPS."""
        if not self._is_capturing:
            return

        self._frame_count += 1

        # Get delta time from event payload
        dt = event.payload.get("dt", 1.0 / 60.0)  # Fallback to 60fps

        # Measure app FPS (sample over 1 second)
        self._fps_sample_count += 1
        self._fps_sample_time += dt
        if self._fps_sample_time >= 1.0:
            self._measured_app_fps = self._fps_sample_count / self._fps_sample_time
            self._fps_sample_count = 0
            self._fps_sample_time = 0.0

        for camera in self._active_cameras:
            if not camera.enabled:
                continue

            # Accumulate elapsed time for this camera
            self._elapsed_time[camera.prim_path] += dt

            # Calculate capture interval from FPS (e.g., 30 FPS = 0.0333s interval)
            capture_interval = 1.0 / camera.fps

            # Capture when enough time has passed
            if self._elapsed_time[camera.prim_path] >= capture_interval:
                self._elapsed_time[camera.prim_path] -= capture_interval
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

            except Exception as e:
                print(f"[brian.camera_management] Capture error for {camera.display_name}: {e}")

        asyncio.ensure_future(_do_capture())

    def stop_capture(self) -> None:
        """Stop capture and clean up resources."""
        self._is_capturing = False

        # Unsubscribe from updates
        if self._update_subscription:
            self._update_subscription = None

        # Finalize writers and extract last written paths
        for prim_path, writer in self._writers.items():
            try:
                # Call on_final_frame for VideoWriter to finalize encoding
                if hasattr(writer, 'on_final_frame'):
                    writer.on_final_frame()

                # Update camera's last_capture_path from writer's actual written path
                if hasattr(writer, 'last_written_path') and writer.last_written_path:
                    for cam in self._active_cameras:
                        if cam.prim_path == prim_path:
                            cam.last_capture_path = writer.last_written_path
                            break

                writer.detach()
            except Exception as e:
                print(f"[brian.camera_management] Error cleaning up writer: {e}")

        self._writers.clear()
        self._render_products.clear()
        self._active_cameras.clear()
        self._elapsed_time.clear()

        print("[brian.camera_management] Capture stopped")

    @property
    def is_capturing(self) -> bool:
        """Return whether capture is currently active."""
        return self._is_capturing

    @property
    def measured_app_fps(self) -> float:
        """Return the measured application frame rate."""
        return self._measured_app_fps

    def get_fps_warnings(self) -> List[str]:
        """Return warnings for cameras whose FPS exceeds app FPS.

        Returns:
            List of warning messages for cameras that are FPS-capped.
        """
        warnings = []
        for cam in self._active_cameras:
            if cam.enabled and cam.fps > self._measured_app_fps:
                warnings.append(
                    f"{cam.display_name}: Target {cam.fps} FPS capped by app ({self._measured_app_fps:.0f} FPS)"
                )
        return warnings

    def update_camera_enabled(self, prim_path: str, enabled: bool) -> None:
        """Update writer attachment based on camera enabled state.

        Args:
            prim_path: The camera's prim path.
            enabled: Whether the camera should be capturing.
        """
        writer = self._writers.get(prim_path)
        render_product = self._render_products.get(prim_path)
        print(writer, render_product, enabled)
        if not writer or not render_product:
            return

        if enabled:
            print(f'Camera {prim_path} writer attached')
            # Reattach writer to resume capturing
            writer.attach([render_product])
        else:
            print(f'Camera {prim_path} writer detached')
            # Detach writer to stop capturing
            writer.detach()

    def cleanup(self) -> None:
        """Release all resources."""
        self.stop_capture()
