import asyncio
import os
import tempfile
import shutil
from typing import Optional, Callable

import numpy as np
from PIL import Image
from omni.replicator.core import AnnotatorRegistry, Writer

# Install imageio at runtime if needed
IMAGEIO_AVAILABLE = False
imageio_module = None

def _setup_imageio():
    """Setup imageio with video encoding backend."""
    global IMAGEIO_AVAILABLE, imageio_module

    def try_import():
        global imageio_module
        try:
            import imageio
            imageio_module = imageio
            return True
        except ImportError:
            return False

    def try_install_ffmpeg_backend():
        """Try to install imageio-ffmpeg for video encoding support."""
        try:
            import omni.kit.pipapi
            omni.kit.pipapi.install("imageio-ffmpeg")
            print("[brian.camera_management] Installed imageio-ffmpeg backend")
            return True
        except Exception as e:
            print(f"[brian.camera_management] Could not install imageio-ffmpeg: {e}")
            return False

    # Try importing imageio
    if try_import():
        IMAGEIO_AVAILABLE = True
        # Try to ensure ffmpeg backend is available
        try_install_ffmpeg_backend()
        return

    # Try installing imageio
    try:
        import omni.kit.pipapi
        omni.kit.pipapi.install("imageio")
        if try_import():
            IMAGEIO_AVAILABLE = True
            try_install_ffmpeg_backend()
            return
    except Exception as e:
        print(f"[brian.camera_management] Failed to setup imageio: {e}")

    IMAGEIO_AVAILABLE = False

_setup_imageio()


class VideoWriter(Writer):
    """Writer that saves frames to temp files and converts to video on completion.

    This approach supports long captures by saving frames to disk instead of memory,
    and uses imageio[pyav] for cross-platform video encoding without system dependencies.
    """

    def __init__(
        self,
        video_filepath: str,
        fps: int = 30,
        width: int = 640,
        height: int = 480,
        on_encoding_complete: Optional[Callable[[str], None]] = None
    ):
        """
        Initialize the video writer.

        Args:
            video_filepath: Output path for the video file.
            fps: Frames per second for the output video.
            width: Video width in pixels.
            height: Video height in pixels.
            on_encoding_complete: Optional callback called when video encoding finishes.
        """
        super().__init__()  # Required: Initialize parent Writer class
        self._video_filepath = video_filepath
        self._fps = fps
        self._width = width
        self._height = height
        self._frame_count = 0
        self._last_written_path: Optional[str] = None
        self._on_encoding_complete = on_encoding_complete
        self._encoding_in_progress = False

        # Create temp directory for frames
        self._temp_dir = tempfile.mkdtemp(prefix="video_capture_")

        # RGB annotator to get frame data
        self.annotators = [AnnotatorRegistry.get_annotator("rgb")]

    def write(self, data: dict):
        """
        Save frame to temp file.

        Args:
            data: Dictionary containing annotator outputs, including "rgb" key.
        """
        if not IMAGEIO_AVAILABLE:
            if self._frame_count == 0:
                print("[brian.camera_management] imageio not available - video capture disabled")
            return

        try:
            # Get RGB data from annotator
            rgb_data = data["rgb"]
            frame = np.array(rgb_data)

            # Convert RGBA to RGB if needed
            if len(frame.shape) == 3 and frame.shape[2] == 4:
                frame = frame[:, :, :3]

            # Resize if needed
            if frame.shape[1] != self._width or frame.shape[0] != self._height:
                img = Image.fromarray(frame)
                img = img.resize((self._width, self._height), Image.LANCZOS)
                frame = np.array(img)

            # Save frame as PNG to temp directory
            frame_path = os.path.join(self._temp_dir, f"frame_{self._frame_count:06d}.png")
            Image.fromarray(frame).save(frame_path)
            self._frame_count += 1

        except Exception as e:
            print(f"[brian.camera_management] Error saving frame: {e}")

    def on_final_frame(self):
        """Start async video encoding. Returns immediately to avoid blocking UI."""
        if self._frame_count == 0:
            self._cleanup()
            return

        if not IMAGEIO_AVAILABLE:
            print("[brian.camera_management] imageio not available - cannot create video")
            self._cleanup()
            return

        # Set expected path immediately so stop_capture() can read it
        # (will be updated to .gif path if MP4 encoding fails)
        self._last_written_path = self._video_filepath

        # Start async encoding to avoid blocking UI
        self._encoding_in_progress = True
        asyncio.ensure_future(self._encode_video_async())

    async def _encode_video_async(self):
        """Encode video frames asynchronously to prevent UI freeze."""
        try:
            # Get sorted frame files
            frame_files = sorted([
                os.path.join(self._temp_dir, f)
                for f in os.listdir(self._temp_dir)
                if f.endswith('.png')
            ])

            if not frame_files:
                print("[brian.camera_management] No frames to encode")
                return

            print(f"[brian.camera_management] Encoding {len(frame_files)} frames to video (async)...")

            # Try MP4 encoding with ffmpeg backend
            video_created = False
            try:
                writer = imageio_module.get_writer(
                    self._video_filepath,
                    fps=self._fps,
                    codec='libx264',
                    pixelformat='yuv420p'
                )
                for i, frame_file in enumerate(frame_files):
                    frame = imageio_module.imread(frame_file)
                    # Ensure RGB (not RGBA)
                    if len(frame.shape) == 3 and frame.shape[2] == 4:
                        frame = frame[:, :, :3]
                    writer.append_data(frame)

                    # Yield control every 10 frames to keep UI responsive
                    if i % 10 == 0:
                        await asyncio.sleep(0)

                writer.close()
                video_created = True
                self._last_written_path = self._video_filepath
                print(f"[brian.camera_management] Video saved: {self._video_filepath} ({self._frame_count} frames)")
            except Exception as mp4_error:
                print(f"[brian.camera_management] MP4 encoding failed: {mp4_error}")

            # Fallback to GIF if MP4 failed
            if not video_created:
                gif_path = self._video_filepath.rsplit('.', 1)[0] + '.gif'
                try:
                    print("[brian.camera_management] Falling back to GIF format...")
                    frames = []
                    for i, f in enumerate(frame_files):
                        frame = imageio_module.imread(f)
                        # Convert RGBA to RGB
                        if len(frame.shape) == 3 and frame.shape[2] == 4:
                            frame = frame[:, :, :3]
                        frames.append(frame)
                        # Yield control periodically
                        if i % 10 == 0:
                            await asyncio.sleep(0)

                    imageio_module.mimsave(gif_path, frames, fps=self._fps)
                    self._last_written_path = gif_path
                    print(f"[brian.camera_management] GIF saved: {gif_path} ({self._frame_count} frames)")
                except Exception as gif_error:
                    print(f"[brian.camera_management] GIF encoding also failed: {gif_error}")

            # Notify completion if callback provided
            if self._on_encoding_complete and self._last_written_path:
                self._on_encoding_complete(self._last_written_path)

        except Exception as e:
            print(f"[brian.camera_management] Error creating video: {e}")
        finally:
            self._encoding_in_progress = False
            self._cleanup()

    def _cleanup(self):
        """Remove temp directory and files."""
        if self._temp_dir and os.path.exists(self._temp_dir):
            try:
                shutil.rmtree(self._temp_dir, ignore_errors=True)
            except Exception as e:
                print(f"[brian.camera_management] Error cleaning up temp files: {e}")
            self._temp_dir = None

    @property
    def video_filepath(self) -> str:
        """Return the output video file path."""
        return self._video_filepath

    @property
    def frame_count(self) -> int:
        """Return the number of frames captured."""
        return self._frame_count

    @property
    def last_written_path(self) -> Optional[str]:
        """Return path to the last successfully written file."""
        return self._last_written_path

    @property
    def is_encoding(self) -> bool:
        """Return whether video encoding is currently in progress."""
        return self._encoding_in_progress
