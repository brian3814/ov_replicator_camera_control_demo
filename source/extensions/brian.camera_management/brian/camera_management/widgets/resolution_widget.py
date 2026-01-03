# SPDX-FileCopyrightText: Copyright (c) 2024 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: LicenseRef-NvidiaProprietary
#
# NVIDIA CORPORATION, its affiliates and licensors retain all intellectual
# property and proprietary rights in and to this material, related
# documentation and any modifications thereto. Any use, reproduction,
# disclosure or distribution of this material and related documentation
# without an express license agreement from NVIDIA CORPORATION or
# its affiliates is strictly prohibited.

"""Resolution widget with synchronized slider and input field."""

from typing import Callable, Optional

import omni.ui as ui

from ..styles import SPACING

__all__ = ["ResolutionWidget"]


class ResolutionWidget:
    """A widget with synchronized slider and integer field for resolution input.

    The slider and field are kept in sync - changing one updates the other.
    This eliminates code duplication for width/height controls.
    """

    def __init__(
        self,
        label: str,
        min_val: int = 64,
        max_val: int = 4096,
        initial: int = 640,
        label_width: int = 50,
        field_width: int = 80,
        on_change: Optional[Callable[[int], None]] = None,
    ):
        """Initialize the resolution widget.

        Args:
            label: Label text to display.
            min_val: Minimum allowed value.
            max_val: Maximum allowed value.
            initial: Initial value.
            label_width: Width of the label in pixels.
            field_width: Width of the input field in pixels.
            on_change: Callback when value changes. Called with the new value.
        """
        self._label = label
        self._min_val = min_val
        self._max_val = max_val
        self._value = initial
        self._label_width = label_width
        self._field_width = field_width
        self._on_change = on_change

        # UI references
        self._slider: Optional[ui.IntSlider] = None
        self._field: Optional[ui.IntField] = None

        # Prevent recursive updates
        self._updating = False

    @property
    def value(self) -> int:
        """Get the current value.

        Returns:
            The current resolution value.
        """
        return self._value

    def set_value(self, value: int):
        """Set the value programmatically.

        Args:
            value: The new value to set.
        """
        value = max(self._min_val, min(self._max_val, value))
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
            ui.Label(self._label, width=self._label_width)

            self._slider = ui.IntSlider(min=self._min_val, max=self._max_val)
            self._slider.model.set_value(self._value)

            self._field = ui.IntField(width=self._field_width)
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
        value = model.as_int
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
        value = model.get_value_as_int()

        # Clamp to valid range
        value = max(self._min_val, min(self._max_val, value))
        self._value = value

        # Sync to slider
        if self._slider:
            self._slider.model.set_value(value)

        # Notify listener
        if self._on_change:
            self._on_change(value)

        self._updating = False
