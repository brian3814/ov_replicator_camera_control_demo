"""Centralized UI styles for the Camera Management extension."""

import pathlib

import omni.kit.app
from omni.ui import color as cl
from omni.ui import url


__all__ = [
    "COLORS",
    "SPACING",
    "LABEL_WIDTH",
    "get_window_style",
]

# Get extension folder path for icon URLs
EXTENSION_FOLDER_PATH = pathlib.Path(
    omni.kit.app.get_app().get_extension_manager().get_extension_path_by_module(__name__)
)

# Define custom color and URL constants for CollapsableFrame icons
cl.camera_mgmt_text = cl("#CCCCCC")
url.camera_mgmt_icon_closed = f"{EXTENSION_FOLDER_PATH}/data/closed.svg"
url.camera_mgmt_icon_opened = f"{EXTENSION_FOLDER_PATH}/data/opened.svg"

# Color palette
COLORS = {
    "primary": 0xFF2E8B57,
    "danger": 0xFF8B2E2E,
    "background": 0xFF404040,
    "background_dark": 0xFF2A2A2A,
    "background_darker": 0xFF1A1A1A,
    "text": 0xFFCCCCCC,
    "text_muted": 0xFF888888,
    "status_capturing": 0xFF00FF00,
    "status_error": 0xFFFF0000,
    "status_stopped": 0xFFCCCCCC,
    "warning": 0xFFFF6666,
}

# Layout constants
SPACING = 5
LABEL_WIDTH = 120


def get_window_style() -> dict:
    """Get the main window style dictionary.

    Returns:
        Style dictionary for omni.ui widgets.
    """
    return {
        # Window and frame styles
        "Window": {
            "background_color": COLORS["background_darker"]
        },
        "ScrollingFrame": {
            "background_color": 0x00000000,  # Transparent
        },

        # Label styles
        "Label": {
            "color": COLORS["text"],
        },

        # Button styles
        "Button": {
            "background_color": COLORS["background"],
        },
        "Button:hovered": {
            "background_color": 0xFF505050,
        },

        # CollapsableFrame styles
        "CollapsableFrame": {
            "background_color": 0x0,
            "secondary_color": 0x0,
        },
        "CollapsableFrame:hovered": {
            "background_color": 0x0,
            "secondary_color": 0x0,
        },
        "CollapsableFrame::group": {
            "background_color": 0x0,
            "secondary_color": 0x0,
            "margin_height": 2,
        },

        # Input field styles
        "IntField": {
            "background_color": COLORS["background_darker"],
        },
        "StringField": {
            "background_color": COLORS["background_darker"],
        },

        # Slider styles
        "IntSlider": {
            "background_color": COLORS["background"],
        },

        # ComboBox styles
        "ComboBox": {
            "background_color": COLORS["background_darker"],
        },

        # CheckBox styles
        "CheckBox": {
            "background_color": COLORS["background_darker"],
        },

        # Custom collapsable header styles
        "Image::collapsable_opened": {"color": cl.camera_mgmt_text, "image_url": url.camera_mgmt_icon_opened},
        "Image::collapsable_closed": {"color": cl.camera_mgmt_text, "image_url": url.camera_mgmt_icon_closed},

        "HeaderLine": {
            "color": 0x338F8F8F,
        },
    }
