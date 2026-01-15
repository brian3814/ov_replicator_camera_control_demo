import asyncio
import os
import time
from datetime import datetime
from typing import List, Dict, Optional, Callable, Any

import omni.usd
import omni.kit.app
import omni.replicator.core as rep
from pxr import UsdGeom

from .models import CameraSettings, CaptureStatus, CaptureMode
from .image_writer import ImageWriter
from .video_writer import VideoWriter
from .usd_camera_utils import UsdCameraUtils


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

        # Prevent overlapping step_async calls which can cause frame drops
        self._step_pending: bool = False

        # Capture statistics for actual FPS calculation
        self._capture_start_time: float = 0.0
        self._camera_frame_counts: Dict[str, int] = {}  # prim_path -> frames captured
        self._total_capture_time: float = 0.0  # Total elapsed capture time
        self._fps_drop_warnings: List[str] = []  # FPS drop events during capture

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
            # Apply camera optical properties to USD before creating render product
            UsdCameraUtils.apply_settings_to_usd(cam.prim_path, cam)
            if not self.create_render_product(cam):
                self.stop_capture()
                return False
            if not self._setup_writer(cam, self._output_folder):
                self.stop_capture()
                return False

        # Reset FPS measurement and capture state
        self._fps_sample_count = 0
        self._fps_sample_time = 0.0
        self._step_pending = False

        # Initialize capture statistics
        self._capture_start_time = time.time()
        self._camera_frame_counts = {cam.prim_path: 0 for cam in self._active_cameras}
        self._total_capture_time = 0.0
        self._fps_drop_warnings = []

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

        # Track total capture time
        self._total_capture_time += dt

        # Measure app FPS (sample over 1 second)
        self._fps_sample_count += 1
        self._fps_sample_time += dt
        if self._fps_sample_time >= 1.0:
            self._measured_app_fps = self._fps_sample_count / self._fps_sample_time
            self._fps_sample_count = 0
            self._fps_sample_time = 0.0

            # Check for FPS drops and log warning (once per second max)
            self._check_fps_drops()

        for camera in self._active_cameras:
            if not camera.enabled:
                continue

            # Accumulate elapsed time for this camera
            self._elapsed_time[camera.prim_path] += dt

            # Calculate capture interval from FPS (e.g., 30 FPS = 0.0333s interval)
            capture_interval = 1.0 / camera.fps

            # Capture when enough time has passed (and no step is pending)
            if self._elapsed_time[camera.prim_path] >= capture_interval:
                if not self._step_pending:
                    self._elapsed_time[camera.prim_path] -= capture_interval
                    self._trigger_capture(camera)
                    # Track frame count for actual FPS calculation
                    self._camera_frame_counts[camera.prim_path] = \
                        self._camera_frame_counts.get(camera.prim_path, 0) + 1
                # If step is pending, don't subtract time - we'll capture on next frame

    def _check_fps_drops(self) -> None:
        """Check if any camera's target FPS exceeds measured app FPS and log warning."""
        for cam in self._active_cameras:
            if cam.enabled and cam.fps > self._measured_app_fps:
                warning = (
                    f"FPS drop: {cam.display_name} target {cam.fps} FPS, "
                    f"app running at {self._measured_app_fps:.1f} FPS"
                )
                # Only log if this is a new warning (avoid spam)
                if warning not in self._fps_drop_warnings:
                    self._fps_drop_warnings.append(warning)
                    print(f"[brian.camera_management] Warning: {warning}")

    def _trigger_capture(self, camera: CameraSettings) -> None:
        """
        Trigger a single frame capture.

        Args:
            camera: Camera settings for the camera to capture from.
        """
        self._step_pending = True

        async def _do_capture():
            try:
                # Step the orchestrator to capture with timeout to prevent freeze
                await asyncio.wait_for(rep.orchestrator.step_async(), timeout=5.0)

                # Get the actual written path from the writer for callback
                writer = self._writers.get(camera.prim_path)
                if writer and hasattr(writer, 'last_written_path') and writer.last_written_path:
                    if self._on_capture_callback:
                        self._on_capture_callback(camera.display_name, writer.last_written_path)

            except asyncio.TimeoutError:
                print(f"[brian.camera_management] Capture timeout for {camera.display_name}")
            except Exception as e:
                print(f"[brian.camera_management] Capture error for {camera.display_name}: {e}")
            finally:
                self._step_pending = False

        asyncio.ensure_future(_do_capture())

    def stop_capture(self) -> None:
        """Stop capture and clean up resources."""
        self._is_capturing = False

        # Calculate total capture duration
        capture_duration = self._total_capture_time if self._total_capture_time > 0 else 0.001

        # Unsubscribe from updates
        if self._update_subscription:
            self._update_subscription.unsubscribe()
            self._update_subscription = None

        # Log capture summary and update VideoWriter FPS
        self._log_capture_summary(capture_duration)

        # Finalize writers and extract last written paths
        for prim_path, writer in self._writers.items():
            try:
                # For VideoWriter, update FPS to actual captured rate before encoding
                if isinstance(writer, VideoWriter):
                    actual_frames = self._camera_frame_counts.get(prim_path, 0)
                    if actual_frames > 0 and capture_duration > 0:
                        actual_fps = actual_frames / capture_duration
                        writer.set_fps(actual_fps)

                # Call on_final_frame for VideoWriter to finalize encoding
                if hasattr(writer, 'on_final_frame'):
                    writer.on_final_frame()

                # Update camera's last_capture_path from writer's actual written path
                if hasattr(writer, 'last_written_path') and writer.last_written_path:
                    for cam in self._active_cameras:
                        if cam.prim_path == prim_path:
                            cam.last_capture_path = writer.last_written_path
                            break
            except Exception as e:
                print(f"[brian.camera_management] Error finalizing writer: {e}")
            finally:
                # Always detach writer to prevent resource leaks
                try:
                    writer.detach()
                except Exception as e:
                    print(f"[brian.camera_management] Error detaching writer: {e}")

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

    def _log_capture_summary(self, capture_duration: float) -> None:
        """Log capture summary with actual vs target frame counts.

        Args:
            capture_duration: Total capture duration in seconds.
        """
        print(f"[brian.camera_management] === Capture Summary ===")
        print(f"[brian.camera_management] Duration: {capture_duration:.2f}s")

        for cam in self._active_cameras:
            if not cam.enabled:
                continue

            actual_frames = self._camera_frame_counts.get(cam.prim_path, 0)
            expected_frames = int(capture_duration * cam.fps)
            actual_fps = actual_frames / capture_duration if capture_duration > 0 else 0

            status = "OK" if actual_frames >= expected_frames * 0.95 else "DROPPED"
            print(
                f"[brian.camera_management] {cam.display_name}: "
                f"{actual_frames}/{expected_frames} frames "
                f"(actual: {actual_fps:.1f} FPS, target: {cam.fps} FPS) [{status}]"
            )

        if self._fps_drop_warnings:
            print(f"[brian.camera_management] FPS warnings during capture: {len(self._fps_drop_warnings)}")

    def update_camera_enabled(self, prim_path: str, enabled: bool) -> None:
        """Update writer attachment based on camera enabled state.

        Args:
            prim_path: The camera's prim path.
            enabled: Whether the camera should be capturing.
        """
        writer = self._writers.get(prim_path)
        render_product = self._render_products.get(prim_path)
        if not writer or not render_product:
            return

        if enabled:
            # Reattach writer to resume capturing
            writer.attach([render_product])
        else:
            # Detach writer to stop capturing
            writer.detach()

    def cleanup(self) -> None:
        """Release all resources."""
        self.stop_capture()
