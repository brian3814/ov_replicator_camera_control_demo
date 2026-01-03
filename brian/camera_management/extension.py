import asyncio
from functools import partial
from typing import Optional

import omni.ext
import omni.kit.app
import omni.ui as ui

from .window import CameraManagementWindow


class CameraManagementExtension(omni.ext.IExt):
    """Extension for managing multiple cameras and capturing images."""

    WINDOW_NAME = "Camera Capture Tool"
    MENU_PATH = f"Window/{WINDOW_NAME}"

    def on_startup(self):
        print("[brian.camera_management] Extension startup")

        self._window: Optional[CameraManagementWindow] = None
        self._menu = None

        ui.Workspace.set_show_window_fn(
            CameraManagementExtension.WINDOW_NAME,
            partial(self._show_window, None)
        )

        try:
            import omni.kit.ui
            editor_menu = omni.kit.ui.get_editor_menu()
            if editor_menu:
                self._menu = editor_menu.add_item(
                    CameraManagementExtension.MENU_PATH,
                    self._show_window,
                    toggle=True,
                    value=True
                )
        except (ImportError, AttributeError):
            # Editor menu not available (e.g., in headless mode)
            pass

        # Show the window on startup
        ui.Workspace.show_window(CameraManagementExtension.WINDOW_NAME)

    def on_shutdown(self):
        """Called when the extension is unloaded."""
        print("[brian.camera_management] Extension shutdown")

        self._menu = None

        if self._window:
            self._window.destroy()
            self._window = None

        # Deregister the window factory
        ui.Workspace.set_show_window_fn(CameraManagementExtension.WINDOW_NAME, None)

    def _show_window(self, menu, value: bool):
        """Show or hide the window.

        Args:
            menu: The menu item (unused).
            value: True to show, False to hide.
        """
        if value:
            self._window = CameraManagementWindow(
                CameraManagementExtension.WINDOW_NAME,
                width=500,
                height=600
            )
            self._window.set_visibility_changed_fn(self._on_visibility_changed)
        elif self._window:
            self._window.visible = False

    def _on_visibility_changed(self, visible: bool) -> None:
        """Handle window visibility changes.

        Args:
            visible: Whether the window is now visible.
        """
        self._set_menu(visible)

        if not visible:
            # Destroy the window asynchronously when hidden
            asyncio.ensure_future(self._destroy_window_async())

    def _set_menu(self, value: bool):
        """Update the menu toggle state.

        Args:
            value: The new toggle state.
        """
        try:
            import omni.kit.ui
            editor_menu = omni.kit.ui.get_editor_menu()
            if editor_menu:
                editor_menu.set_value(CameraManagementExtension.MENU_PATH, value)
        except (ImportError, AttributeError):
            pass

    async def _destroy_window_async(self):
        """Destroy the window asynchronously.

        Waits one frame before destruction due to framework timing requirements.
        """
        await omni.kit.app.get_app().next_update_async()
        if self._window:
            self._window.destroy()
            self._window = None
