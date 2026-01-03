"""Camera property widget with synchronized slider and float field."""

from typing import Callable, Optional

import omni.ui as ui

from ..styles import SPACING

__all__ = ["CameraPropertyWidget"]


class CameraPropertyWidget:
    """A widget with synchronized slider and float field for camera properties.

    The slider and field are kept in sync - changing one updates the other.
    Similar to ResolutionWidget but handles float values with configurable precision.
    """

    def __init__(
        self,
        label: str,
        min_val: float,
        max_val: float,
        initial: float,
        step: float = 0.1,
        precision: int = 2,
        unit: str = "",
        label_width: int = 110,
        field_width: int = 70,
        on_change: Optional[Callable[[float], None]] = None,
    ):
        """Initialize the camera property widget.

        Args:
            label: Label text to display.
            min_val: Minimum allowed value.
            max_val: Maximum allowed value.
            initial: Initial value.
            step: Increment step for slider.
            precision: Decimal places for rounding.
            unit: Unit label (e.g., "mm", "cm").
            label_width: Width of the label in pixels.
            field_width: Width of the input field in pixels.
            on_change: Callback when value changes. Called with the new value.
        """
        self._label = label
        self._min_val = min_val
        self._max_val = max_val
        self._value = initial
        self._step = step
        self._precision = precision
        self._unit = unit
        self._label_width = label_width
        self._field_width = field_width
        self._on_change = on_change

        # UI references
        self._slider: Optional[ui.FloatSlider] = None
        self._field: Optional[ui.FloatField] = None

        # Prevent recursive updates
        self._updating = False

    @property
    def value(self) -> float:
        """Get the current value.

        Returns:
            The current property value.
        """
        return self._value

    def set_value(self, value: float):
        """Set the value programmatically without triggering callback.

        Args:
            value: The new value to set.
        """
        value = max(self._min_val, min(self._max_val, value))
        value = round(value, self._precision)
        self._value = value

        if self._updating:
            return

        self._updating = True
        if self._slider:
            self._slider.model.set_value(value)
        if self._field:
            self._field.model.set_value(value)
        self._updating = False

    def build(self) -> ui.HStack:
        """Build the widget UI.

        Returns:
            The HStack container with the widget.
        """
        with ui.HStack(height=25, spacing=SPACING) as container:
            # Label with optional unit
            label_text = f"{self._label}:" if not self._unit else f"{self._label} ({self._unit}):"
            ui.Label(label_text, width=self._label_width)

            # Float slider
            self._slider = ui.FloatSlider(
                min=self._min_val,
                max=self._max_val,
                step=self._step
            )
            self._slider.model.set_value(self._value)

            # Float field
            self._field = ui.FloatField(width=self._field_width)
            self._field.model.set_value(self._value)

            # Connect slider changes
            self._slider.model.add_value_changed_fn(self._on_slider_changed)

            # Connect field changes
            self._field.model.add_value_changed_fn(self._on_field_changed)

        return container

    def _on_slider_changed(self, model):
        """Handle slider value changes.

        Args:
            model: The slider's value model.
        """
        if self._updating:
            return

        self._updating = True
        value = round(model.as_float, self._precision)
        self._value = value

        # Sync to field
        if self._field:
            self._field.model.set_value(value)

        # Notify listener
        if self._on_change:
            self._on_change(value)

        self._updating = False

    def _on_field_changed(self, model):
        """Handle field value changes.

        Args:
            model: The field's value model.
        """
        if self._updating:
            return

        self._updating = True
        value = model.get_value_as_float()

        # Clamp to valid range
        value = max(self._min_val, min(self._max_val, value))
        value = round(value, self._precision)
        self._value = value

        # Sync to slider
        if self._slider:
            self._slider.model.set_value(value)

        # Notify listener
        if self._on_change:
            self._on_change(value)

        self._updating = False
