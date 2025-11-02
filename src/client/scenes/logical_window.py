# External libraries
from pyglet.window import Window
from pyglet.clock import schedule_interval, unschedule
from pyglet.gl import glViewport
from pyglet.math import Mat4
from pyglet.event import EVENT_HANDLED


# Internal libraries
from common.config import LOGICAL_SCREEN_WIDTH, LOGICAL_SCREEN_HEIGHT, FPS
from client.scenes.scene_manager import SceneManager


class LogicalWindow(Window):
    """
    Window with logical coordinate space, projected onto a viewport.

    Handles window-level concerns (input transformation, viewport management,
    event dispatching) and delegates scene updates to SceneManager.
    """

    def __init__(self, width=LOGICAL_SCREEN_WIDTH,
                 height=LOGICAL_SCREEN_HEIGHT, **kwargs):
        """
        Constructor. Extra arguments can be passed as described
        in pyglet documentation.
        """
        super().__init__(width, height, resizable=True, **kwargs)

        self.logical_width = LOGICAL_SCREEN_WIDTH
        self.logical_height = LOGICAL_SCREEN_HEIGHT

        self.scene_manager = SceneManager()

        # Store viewport info for coordinate transformation
        self.viewport_x = 0
        self.viewport_y = 0
        self.viewport_scale = 1.0

        # Schedule the number of frames per second
        schedule_interval(self.update, 1 / FPS)

        # Initialize projection
        self.on_resize(self.width, self.height)

    def on_resize(self, width, height):
        """Handle window resize with aspect ratio preservation."""
        # Query framebuffer size for the actual GL viewport in pixels
        # This is needed for high-DPI displays (Retina/4K) where framebuffer
        # size differs from window size due to pixel scaling
        fb_w, fb_h = self.get_framebuffer_size()

        # Compare window aspect to logical aspect
        window_aspect = width / height
        logical_aspect = self.logical_width / self.logical_height

        if window_aspect > logical_aspect:
            # Window wider than logical - fit by h (vertical bars on sides)
            scale = fb_h / self.logical_height
            vp_w = int(round(self.logical_width * scale))
            vp_h = fb_h
            vp_x = (fb_w - vp_w) // 2
            vp_y = 0
        else:
            # Window taller than logical - fit by w (horiz bars top/bottom)
            scale = fb_w / self.logical_width
            vp_w = fb_w
            vp_h = int(round(self.logical_height * scale))
            vp_x = 0
            vp_y = (fb_h - vp_h) // 2

        glViewport(vp_x, vp_y, vp_w, vp_h)

        # Store for coordinate transformation
        # Convert from framebuffer to window coordinates
        pixel_ratio = fb_w / width if width > 0 else 1.0
        self.viewport_x = vp_x / pixel_ratio
        self.viewport_y = vp_y / pixel_ratio
        self.viewport_scale = scale / pixel_ratio

        # Keep a fixed logical 2D projection
        self.projection = Mat4.orthogonal_projection(
            0, self.logical_width, 0, self.logical_height, -255, 255
        )
        return EVENT_HANDLED

    def on_mouse_press(self, x, y, button, modifiers):
        """
        Transform screen coordinates to logical space and
        delegate to current scene.
        """
        if self.scene_manager.cur_scene_instance:
            logical_x, logical_y = self.screen_to_logical(x, y)
            self.scene_manager.cur_scene_instance.helper_mouse_press(
                logical_x, logical_y, button, modifiers
            )

    def screen_to_logical(self, sx, sy):
        """
        Transform screen coordinates to logical game space.
        Accounts for viewport offset and scaling, including high-DPI displays.
        """
        return (sx - self.viewport_x) / self.viewport_scale, \
               (sy - self.viewport_y) / self.viewport_scale

    def update(self, dt):
        """ Update current scene. """
        if self.scene_manager.cur_scene_instance:
            self.scene_manager.cur_scene_instance.helper_update(dt)

    def on_draw(self):
        """ Clear window and render current scene batch. """
        self.clear()
        if self.scene_manager.cur_scene_instance:
            self.scene_manager.cur_scene_instance.batch.draw()

    def on_close(self):
        """ Handle window closing (implicitly leaving the scene). """
        unschedule(self.update)  # Stop callbacks

        # Handle current scene instance leaving
        if self.scene_manager.cur_scene_instance:
            self.scene_manager.cur_scene_instance.helper_leave()

        # Handle window exit at pyglet level
        super().on_close()
