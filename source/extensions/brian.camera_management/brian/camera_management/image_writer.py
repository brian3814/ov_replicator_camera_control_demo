"""Custom image writer with configurable file naming."""

import os
from datetime import datetime

import numpy as np
from PIL import Image
from omni.replicator.core import AnnotatorRegistry, Writer


class ImageWriter(Writer):
    """Writer that saves RGB frames as images with custom naming.

    Allows configurable filename format including camera name, timestamp,
    and frame number.
    """

    def __init__(
        self,
        output_dir: str,
        camera_name: str,
        image_format: str = "png"
    ):
        """Initialize the image writer.

        Args:
            output_dir: Output directory for image files.
            camera_name: Camera name to include in filenames.
            image_format: Image format (png, jpg). Defaults to png.
        """
        super().__init__()
        self._output_dir = output_dir
        self._camera_name = camera_name
        self._image_format = image_format.lower()
        self._frame_count = 0
        self._capture_start_time = datetime.now().strftime("%Y%m%d_%H%M%S")

        # Ensure output directory exists
        os.makedirs(self._output_dir, exist_ok=True)

        # RGB annotator to get frame data
        self.annotators = [AnnotatorRegistry.get_annotator("rgb")]

    def write(self, data: dict):
        """Save frame as image file.

        Args:
            data: Dictionary containing annotator outputs, including "rgb" key.
        """
        try:
            # Get RGB data from annotator
            rgb_data = data.get("rgb")
            if rgb_data is None:
                print("[brian.camera_management] No RGB data in frame")
                return

            frame = np.array(rgb_data)

            # Convert RGBA to RGB if needed
            if len(frame.shape) == 3 and frame.shape[2] == 4:
                frame = frame[:, :, :3]

            # Build filename: CameraName_StartTime_FrameNumber.format
            filename = f"{self._camera_name}_{self._capture_start_time}_{self._frame_count:06d}.{self._image_format}"
            filepath = os.path.join(self._output_dir, filename)

            # Save image
            img = Image.fromarray(frame)
            if self._image_format == "jpg" or self._image_format == "jpeg":
                img.save(filepath, quality=95)
            else:
                img.save(filepath)

            self._frame_count += 1

        except Exception as e:
            print(f"[brian.camera_management] Error saving image: {e}")

    def on_final_frame(self):
        """Called when capture ends. Log summary."""
        if self._frame_count > 0:
            print(f"[brian.camera_management] ImageWriter: Saved {self._frame_count} images to {self._output_dir}")

    @property
    def output_dir(self) -> str:
        """Return the output directory."""
        return self._output_dir

    @property
    def frame_count(self) -> int:
        """Return the number of frames captured."""
        return self._frame_count
