"""USD camera property utilities for reading and writing camera attributes."""

import math
from typing import Any, Dict, Optional, TYPE_CHECKING

import omni.usd
from pxr import UsdGeom

# Fixed sensor width for FOV calculations (35mm full-frame equivalent)
SENSOR_WIDTH = 36.0  # mm

if TYPE_CHECKING:
    from .models import CameraSettings

__all__ = ["UsdCameraUtils"]


class UsdCameraUtils:
    """Utility class for reading and writing USD camera properties."""

    @staticmethod
    def calculate_fov(focal_length: float, h_aperture: float = SENSOR_WIDTH) -> float:
        """Calculate field of view in degrees from focal length.

        Args:
            focal_length: Focal length in mm.
            h_aperture: Horizontal aperture (sensor width) in mm.

        Returns:
            Field of view in degrees.
        """
        if focal_length <= 0:
            return 90.0
        return math.degrees(2 * math.atan(h_aperture / (2 * focal_length)))

    @staticmethod
    def calculate_focal_length(fov: float, h_aperture: float = SENSOR_WIDTH) -> float:
        """Calculate focal length from field of view.

        Args:
            fov: Field of view in degrees.
            h_aperture: Horizontal aperture (sensor width) in mm.

        Returns:
            Focal length in mm.
        """
        if fov <= 0 or fov >= 180:
            return 24.0
        return h_aperture / (2 * math.tan(math.radians(fov / 2)))

    @staticmethod
    def get_camera_prim(prim_path: str) -> Optional[UsdGeom.Camera]:
        """Get a UsdGeom.Camera from a prim path.

        Args:
            prim_path: The USD prim path to the camera.

        Returns:
            UsdGeom.Camera if found, None otherwise.
        """
        context = omni.usd.get_context()
        stage = context.get_stage()
        if not stage:
            return None

        prim = stage.GetPrimAtPath(prim_path)
        if not prim or not prim.IsA(UsdGeom.Camera):
            return None

        return UsdGeom.Camera(prim)

    @staticmethod
    def get_camera_properties(prim_path: str) -> Dict[str, Any]:
        """Read current camera properties from USD.

        Args:
            prim_path: The USD prim path to the camera.

        Returns:
            Dictionary with camera properties, empty if camera not found.
        """
        camera = UsdCameraUtils.get_camera_prim(prim_path)
        if not camera:
            return {}

        focal_length = camera.GetFocalLengthAttr().Get() or 24.0
        return {
            "focal_length": focal_length,
            "focus_distance": camera.GetFocusDistanceAttr().Get() or 400.0,
            "exposure": camera.GetExposureAttr().Get() or 0.0,
            "fov": UsdCameraUtils.calculate_fov(focal_length),
        }

    @staticmethod
    def set_focal_length(prim_path: str, value: float) -> bool:
        """Set camera focal length in mm.

        Args:
            prim_path: The USD prim path to the camera.
            value: Focal length in millimeters.

        Returns:
            True if successful, False otherwise.
        """
        camera = UsdCameraUtils.get_camera_prim(prim_path)
        if not camera:
            return False
        camera.GetFocalLengthAttr().Set(value)
        return True

    @staticmethod
    def set_focus_distance(prim_path: str, value: float) -> bool:
        """Set camera focus distance in scene units (cm).

        Args:
            prim_path: The USD prim path to the camera.
            value: Focus distance in centimeters.

        Returns:
            True if successful, False otherwise.
        """
        camera = UsdCameraUtils.get_camera_prim(prim_path)
        if not camera:
            return False
        camera.GetFocusDistanceAttr().Set(value)
        return True

    @staticmethod
    def set_exposure(prim_path: str, value: float) -> bool:
        """Set camera exposure compensation in EV.

        Args:
            prim_path: The USD prim path to the camera.
            value: Exposure value (EV).

        Returns:
            True if successful, False otherwise.
        """
        camera = UsdCameraUtils.get_camera_prim(prim_path)
        if not camera:
            return False
        camera.GetExposureAttr().Set(value)
        return True

    @staticmethod
    def sync_settings_from_usd(prim_path: str, settings: "CameraSettings") -> bool:
        """Sync CameraSettings from current USD camera values.

        Args:
            prim_path: The USD prim path to the camera.
            settings: CameraSettings instance to update.

        Returns:
            True if successful, False otherwise.
        """
        props = UsdCameraUtils.get_camera_properties(prim_path)
        if not props:
            return False

        settings.focal_length = props.get("focal_length", settings.focal_length)
        settings.focus_distance = props.get("focus_distance", settings.focus_distance)
        settings.exposure = props.get("exposure", settings.exposure)
        settings.fov = props.get("fov", settings.fov)
        return True

    @staticmethod
    def apply_settings_to_usd(prim_path: str, settings: "CameraSettings") -> bool:
        """Apply CameraSettings to USD camera prim.

        Args:
            prim_path: The USD prim path to the camera.
            settings: CameraSettings instance with values to apply.

        Returns:
            True if successful, False otherwise.
        """
        camera = UsdCameraUtils.get_camera_prim(prim_path)
        if not camera:
            return False

        camera.GetFocalLengthAttr().Set(settings.focal_length)
        camera.GetFocusDistanceAttr().Set(settings.focus_distance)
        camera.GetExposureAttr().Set(settings.exposure)
        return True
