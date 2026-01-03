from dataclasses import dataclass, field
from typing import Optional
from enum import Enum


class CaptureStatus(Enum):
    """Status of the capture process."""
    STOPPED = "Stopped"
    CAPTURING = "Capturing"
    ERROR = "Error"


class CaptureMode(Enum):
    """Capture output mode."""
    IMAGE = "Image Sequence"
    VIDEO = "Video"


@dataclass
class CameraSettings:
    """Settings for a single camera in the capture list."""
    prim_path: str
    display_name: str
    width: int = 640
    height: int = 480
    interval_frames: int = 60
    enabled: bool = True
    output_rgb: bool = True
    last_capture_path: Optional[str] = None
    frame_counter: int = 0
    capture_mode: CaptureMode = CaptureMode.IMAGE
    fps: int = 30  # For video mode


@dataclass
class GlobalSettings:
    """Global capture settings."""
    output_folder: str = ""
    status: CaptureStatus = field(default=CaptureStatus.STOPPED)
