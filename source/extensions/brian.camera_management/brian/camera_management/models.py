from dataclasses import dataclass, field
from typing import Any, Dict, Optional
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
    fps: int = 30
    enabled: bool = True
    last_capture_path: Optional[str] = None
    frame_counter: int = 0
    capture_mode: CaptureMode = CaptureMode.IMAGE
    # Camera optical properties
    focal_length: float = 24.0  # mm
    focus_distance: float = 400.0  # cm
    exposure: float = 0.0  # EV (exposure compensation)
    fov: float = 73.7  # degrees (calculated from 24mm focal length on 36mm sensor)

    def to_dict(self) -> Dict[str, Any]:
        """Serialize camera settings to a dictionary.

        Returns:
            Dictionary representation of the camera settings.
        """
        return {
            "prim_path": self.prim_path,
            "display_name": self.display_name,
            "width": self.width,
            "height": self.height,
            "fps": self.fps,
            "enabled": self.enabled,
            "last_capture_path": self.last_capture_path,
            "capture_mode": self.capture_mode.name,
            "focal_length": self.focal_length,
            "focus_distance": self.focus_distance,
            "exposure": self.exposure,
            "fov": self.fov,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "CameraSettings":
        """Create CameraSettings from a dictionary.

        Args:
            data: Dictionary containing camera settings.

        Returns:
            CameraSettings instance.
        """
        capture_mode = CaptureMode[data.get("capture_mode", "IMAGE")]
        return cls(
            prim_path=data["prim_path"],
            display_name=data["display_name"],
            width=data.get("width", 640),
            height=data.get("height", 480),
            fps=data.get("fps", 30),
            enabled=data.get("enabled", True),
            last_capture_path=data.get("last_capture_path"),
            capture_mode=capture_mode,
            focal_length=data.get("focal_length", 24.0),
            focus_distance=data.get("focus_distance", 400.0),
            exposure=data.get("exposure", 0.0),
            fov=data.get("fov", 73.7),
        )


@dataclass
class GlobalSettings:
    """Global capture settings."""
    output_folder: str = ""
    status: CaptureStatus = field(default=CaptureStatus.STOPPED)
