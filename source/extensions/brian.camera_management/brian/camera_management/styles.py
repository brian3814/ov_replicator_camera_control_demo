"""Centralized UI styles for the Camera Management extension."""

__all__ = [
    "COLORS",
    "SPACING",
    "LABEL_WIDTH",
    "get_window_style",
]

# Color palette
COLORS = {
    "primary": 0xFF2E8B57,           # Green - for primary actions
    "primary_hover": 0xFF3DA066,     # Lighter green for hover
    "danger": 0xFF8B2E2E,            # Red - for destructive/stop actions
    "danger_hover": 0xFFA03A3A,      # Lighter red for hover
    "background": 0xFF404040,        # Standard button/panel background
    "background_dark": 0xFF2A2A2A,   # Darker background for panels
    "background_darker": 0xFF1A1A1A, # Darkest background for log area
    "text": 0xFFCCCCCC,              # Standard text color
    "text_muted": 0xFF888888,        # Muted/secondary text
    "accent": 0xFF00CC88,            # Accent color for titles
    "status_capturing": 0xFF00FF00,  # Bright green for capturing status
    "status_error": 0xFFFF0000,      # Red for error status
    "status_stopped": 0xFFCCCCCC,    # Gray for stopped status
    "warning": 0xFFFF6666,           # Warning color (e.g., "no cameras")
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
        "Label::title": {
            "font_size": 20,
            "color": COLORS["accent"],
        },
        "Label::section_header": {
            "font_size": 14,
            "color": COLORS["text"],
        },
        "Label::status": {
            "color": COLORS["text"],
        },
        "Label::status_capturing": {
            "color": COLORS["status_capturing"],
        },
        "Label::status_error": {
            "color": COLORS["status_error"],
        },
        "Label::status_stopped": {
            "color": COLORS["status_stopped"],
        },
        "Label::warning": {
            "color": COLORS["warning"],
        },
        "Label::log": {
            "font_size": 12,
            "color": COLORS["text"],
        },

        # Button styles
        "Button": {
            "background_color": COLORS["background"],
        },
        "Button:hovered": {
            "background_color": 0xFF505050,
        },
        "Button::primary": {
            "background_color": COLORS["primary"],
        },
        "Button::primary:hovered": {
            "background_color": COLORS["primary_hover"],
        },
        "Button::danger": {
            "background_color": COLORS["danger"],
        },
        "Button::danger:hovered": {
            "background_color": COLORS["danger_hover"],
        },
        "Button::disabled": {
            "background_color": COLORS["background"],
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
        "FloatField": {
            "background_color": COLORS["background_darker"],
        },
        "StringField": {
            "background_color": COLORS["background_darker"],
        },

        # Slider styles
        "IntSlider": {
            "background_color": COLORS["background_darker"],
        },
        "FloatSlider": {
            "background_color": COLORS["background_darker"],
        },

        # ComboBox styles
        "ComboBox": {
            "background_color": COLORS["background_darker"],
        },

        # CheckBox styles
        "CheckBox": {
            "background_color": COLORS["background_darker"],
        },

        # Log panel specific
        "ScrollingFrame::log": {
            "background_color": COLORS["background_darker"],
        },

        # Custom collapsable header styles
        "Label::collapsable_name": {
            "font_size": 14,
            "color": COLORS["text"],
        },
        "Image::collapsable_opened": {
            "color": COLORS["text"],
        },
        "Image::collapsable_opened:hovered": {
            "color": COLORS["accent"],
        },
        "Image::collapsable_closed": {
            "color": COLORS["text"],
        },
        "Image::collapsable_closed:hovered": {
            "color": COLORS["accent"],
        },
        "HeaderLine": {
            "color": 0x338F8F8F,
        },
    }
