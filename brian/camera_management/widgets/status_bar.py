# SPDX-FileCopyrightText: Copyright (c) 2024 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: LicenseRef-NvidiaProprietary
#
# NVIDIA CORPORATION, its affiliates and licensors retain all intellectual
# property and proprietary rights in and to this material, related
# documentation and any modifications thereto. Any use, reproduction,
# disclosure or distribution of this material and related documentation
# without an express license agreement from NVIDIA CORPORATION or
# its affiliates is strictly prohibited.

"""Status bar widget for displaying capture status."""

from typing import Optional

import omni.ui as ui

from ..models import CaptureStatus
from ..styles import COLORS

__all__ = ["StatusBarWidget"]


class StatusBarWidget:
    """Widget for displaying capture status with color-coded indicators."""

    def __init__(self, initial_status: CaptureStatus = CaptureStatus.STOPPED):
        """Initialize the status bar widget.

        Args:
            initial_status: The initial status to display.
        """
        self._status = initial_status
        self._label: Optional[ui.Label] = None

    @property
    def status(self) -> CaptureStatus:
        """Get the current status.

        Returns:
            The current CaptureStatus.
        """
        return self._status

    def set_status(self, status: CaptureStatus):
        """Update the displayed status.

        Args:
            status: The new status to display.
        """
        self._status = status
        self._update_display()

    def build(self) -> ui.HStack:
        """Build the status bar UI.

        Returns:
            The HStack container with the status bar.
        """
        with ui.HStack(height=25) as container:
            ui.Label("Status:", width=50)
            self._label = ui.Label(
                self._status.value,
                style={"color": self._get_status_color()}
            )

        return container

    def _update_display(self):
        """Update the label text and color based on current status."""
        if self._label:
            self._label.text = self._status.value
            self._label.style = {"color": self._get_status_color()}

    def _get_status_color(self) -> int:
        """Get the color for the current status.

        Returns:
            The color as an integer ARGB value.
        """
        if self._status == CaptureStatus.CAPTURING:
            return COLORS["status_capturing"]
        elif self._status == CaptureStatus.ERROR:
            return COLORS["status_error"]
        else:
            return COLORS["status_stopped"]
