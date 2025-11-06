# External libraries
from pyglet.clock import schedule_interval, unschedule
from pyglet.event import EVENT_HANDLED
from pyglet.gl import glViewport
from pyglet.math import Mat4
from pyglet.window import Window


# Internal libraries
from client.config import Z_FAR, Z_NEAR
from client.scenes.scene_manager import SceneManager
from common.config import (
    NETWORK_UPDATE_RATE,
    LOGICAL_SCREEN_HEIGHT,
    LOGICAL_SCREEN_WIDTH
)


class LogicalWindow(Window):
    """
    Window with logical coordinate space projected onto a viewport.

    Handles window-level concerns: input transformation, viewport management,
    and event dispatching to the scene manager. Maintains aspect ratio
    preservation and supports high-DPI displays.
    """

    def __init__(
        self,
        width: int = LOGICAL_SCREEN_WIDTH,
        height: int = LOGICAL_SCREEN_HEIGHT,
        **kwargs,
    ) -> None:
        """
        Initialize the window with logical coordinate space.

        Args:
            width: Physical window width in pixels.
            height: Physical window height in pixels.
            **kwargs: Additional arguments passed to pyglet.Window.
        """
        super().__init__(width, height, resizable=True, **kwargs)

        self.logical_width = LOGICAL_SCREEN_WIDTH
        self.logical_height = LOGICAL_SCREEN_HEIGHT
        self.scene_manager = SceneManager()

        # Viewport transformation data
        self.viewport_x: float = 0
        self.viewport_y: float = 0
        self.viewport_scale: float = 1.0
        self.projection = Mat4()

        # Schedule update loop
        schedule_interval(self.update, 1 / NETWORK_UPDATE_RATE)  # compute FPS

        # Initialize projection matrix
        self.on_resize(self.width, self.height)

    # Viewport management

    def on_resize(self, width: int, height: int) -> int:
        """
        Recalculate viewport with aspect ratio preservation.

        Handles window resizing while maintaining the logical aspect ratio.
        Accounts for high-DPI displays where framebuffer size differs from
        window size due to pixel scaling.

        Args:
            width: New window width in pixels.
            height: New window height in pixels.

        Returns:
            EVENT_HANDLED to indicate the event was processed.
        """
        # Get framebuffer size for high-DPI display support
        fb_w, fb_h = self.get_framebuffer_size()

        window_aspect = width / height
        logical_aspect = self.logical_width / self.logical_height

        if window_aspect > logical_aspect:
            # Window wider than logical (vertical letterboxing)
            scale = fb_h / self.logical_height
            vp_w = int(round(self.logical_width * scale))
            vp_h = fb_h
            vp_x = (fb_w - vp_w) // 2
            vp_y = 0
        else:
            # Window taller than logical (horizontal letterboxing)
            scale = fb_w / self.logical_width
            vp_w = fb_w
            vp_h = int(round(self.logical_height * scale))
            vp_x = 0
            vp_y = (fb_h - vp_h) // 2

        glViewport(vp_x, vp_y, vp_w, vp_h)

        # Store transformation data for coordinate conversion
        pixel_ratio = fb_w / width if width > 0 else 1.0
        self.viewport_x = vp_x / pixel_ratio
        self.viewport_y = vp_y / pixel_ratio
        self.viewport_scale = scale / pixel_ratio

        # Create fixed logical projection matrix
        self.projection = Mat4.orthogonal_projection(
            0, self.logical_width, 0, self.logical_height, Z_NEAR, Z_FAR
        )
        return EVENT_HANDLED

    # Coordinate transformation

    def screen_to_logical(
        self, screen_x: float, screen_y: float
    ) -> tuple[float, float]:
        """
        Convert screen coordinates to logical game space.

        Accounts for viewport offset, scaling, and high-DPI displays.

        Args:
            screen_x: X coordinate in screen space.
            screen_y: Y coordinate in screen space.

        Returns:
            Tuple of (logical_x, logical_y) in game coordinate space.
        """
        logical_x = (screen_x - self.viewport_x) / self.viewport_scale
        logical_y = (screen_y - self.viewport_y) / self.viewport_scale
        return logical_x, logical_y

    # Input handling

    def on_mouse_press(
        self, x: float, y: float, button: int, modifiers: int
    ) -> None:
        """
        Handle mouse press input and delegate to current scene.

        Transforms screen coordinates to logical space before dispatching.

        Args:
            x: X coordinate in screen space.
            y: Y coordinate in screen space.
            button: Mouse button identifier.
            modifiers: Keyboard modifier flags.
        """
        if self.scene_manager.cur_scene_instance:
            logical_x, logical_y = self.screen_to_logical(x, y)
            self.scene_manager.cur_scene_instance.helper_mouse_press(
                logical_x, logical_y, button, modifiers
            )

    # Update and rendering

    def update(self, dt: float) -> None:
        """
        Update the current scene.

        Args:
            dt: Delta time since last update in seconds.
        """
        if self.scene_manager.cur_scene_instance:
            self.scene_manager.cur_scene_instance.helper_update(dt)

    def on_draw(self) -> None:
        """Clear window and render the current scene batch."""
        self.clear()
        if self.scene_manager.cur_scene_instance:
            self.scene_manager.cur_scene_instance.batch.draw()

    # Lifecycle

    def on_close(self) -> None:
        """
        Handle window closing and cleanup.

        Stops the update loop and leaves the current scene.
        """
        unschedule(self.update)

        if self.scene_manager.cur_scene_instance:
            self.scene_manager.cur_scene_instance.helper_leave()

        super().on_close()
