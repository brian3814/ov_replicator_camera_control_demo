"""Widgets package for camera management UI components."""

from .resolution_widget import ResolutionWidget
from .status_bar import StatusBarWidget
from .log_panel import LogPanelWidget
from .camera_panel import CameraPanelWidget, CameraPanelCallbacks
from .camera_property_widget import CameraPropertyWidget

__all__ = [
    "ResolutionWidget",
    "StatusBarWidget",
    "LogPanelWidget",
    "CameraPanelWidget",
    "CameraPanelCallbacks",
    "CameraPropertyWidget",
]
