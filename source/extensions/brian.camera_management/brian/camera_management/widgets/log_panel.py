# SPDX-FileCopyrightText: Copyright (c) 2024 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: LicenseRef-NvidiaProprietary
#
# NVIDIA CORPORATION, its affiliates and licensors retain all intellectual
# property and proprietary rights in and to this material, related
# documentation and any modifications thereto. Any use, reproduction,
# disclosure or distribution of this material and related documentation
# without an express license agreement from NVIDIA CORPORATION or
# its affiliates is strictly prohibited.

"""Log panel widget for displaying capture log entries."""

from datetime import datetime
from typing import List, Optional

import omni.ui as ui

from ..styles import COLORS

__all__ = ["LogPanelWidget"]


class LogPanelWidget:
    """Widget for displaying a scrolling log of capture events."""

    def __init__(self, max_entries: int = 10, height: int = 150):
        """Initialize the log panel widget.

        Args:
            max_entries: Maximum number of log entries to display.
            height: Height of the log panel in pixels.
        """
        self._max_entries = max_entries
        self._height = height
        self._entries: List[str] = []
        self._label: Optional[ui.Label] = None

    @property
    def entries(self) -> List[str]:
        """Get the current log entries.

        Returns:
            List of log entry strings.
        """
        return self._entries.copy()

    @property
    def latest(self) -> Optional[str]:
        """Get the most recent log entry.

        Returns:
            The latest log entry, or None if empty.
        """
        return self._entries[-1] if self._entries else None

    def add_entry(self, message: str):
        """Add a new log entry with timestamp.

        Args:
            message: The message to log.
        """
        timestamp = datetime.now().strftime("%H:%M:%S")
        entry = f"[{timestamp}] {message}"
        self._entries.append(entry)

        # Keep only the last N entries
        if len(self._entries) > self._max_entries:
            self._entries = self._entries[-self._max_entries:]

        self._update_display()

    def clear(self):
        """Clear all log entries."""
        self._entries.clear()
        self._update_display()

    def build(self) -> ui.VStack:
        """Build the log panel UI.

        Returns:
            The VStack container with the log panel.
        """
        with ui.VStack(spacing=5) as container:
            with ui.ScrollingFrame(
                height=self._height,
                horizontal_scrollbar_policy=ui.ScrollBarPolicy.SCROLLBAR_ALWAYS_OFF,
                vertical_scrollbar_policy=ui.ScrollBarPolicy.SCROLLBAR_AS_NEEDED,
                style={"background_color": COLORS["background_darker"]}
            ):
                self._label = ui.Label(
                    self._get_display_text(),
                    word_wrap=True,
                    alignment=ui.Alignment.LEFT_TOP,
                    style={"font_size": 12}
                )

        return container

    def _update_display(self):
        """Update the log display with current entries."""
        if self._label:
            self._label.text = self._get_display_text()

    def _get_display_text(self) -> str:
        """Get the formatted display text for all entries.

        Returns:
            Newline-separated log entries.
        """
        return "\n".join(self._entries)
