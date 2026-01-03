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
    output_rgb: bool = True
    last_capture_path: Optional[str] = None
    frame_counter: int = 0
    capture_mode: CaptureMode = CaptureMode.IMAGE

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
            "output_rgb": self.output_rgb,
            "last_capture_path": self.last_capture_path,
            "capture_mode": self.capture_mode.name,
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
            output_rgb=data.get("output_rgb", True),
            last_capture_path=data.get("last_capture_path"),
            capture_mode=capture_mode,
        )


@dataclass
class GlobalSettings:
    """Global capture settings."""
    output_folder: str = ""
    status: CaptureStatus = field(default=CaptureStatus.STOPPED)
