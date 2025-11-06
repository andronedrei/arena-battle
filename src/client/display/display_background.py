# External libraries
from pyglet.graphics import Batch, Group
from pyglet.image import load
from pyglet.shapes import Line
from pyglet.sprite import Sprite


# Internal libraries
from client.config import BACKGROUND_FILE, GRID_COLOR, GRID_OPACITY
from client.display.batch_object import BatchObject
from common.config import (
    GRID_UNIT,
    LOGICAL_SCREEN_HEIGHT,
    LOGICAL_SCREEN_WIDTH
)


class DisplayBackground(BatchObject):
    """
    Renders background image and grid overlay.

    Uses pyglet Groups for layer ordering: background image rendered
    first, then grid lines on top.
    """

    def __init__(
        self,
        batch: Batch,
        background_file: str = BACKGROUND_FILE,
        logical_width: int = LOGICAL_SCREEN_WIDTH,
        logical_height: int = LOGICAL_SCREEN_HEIGHT,
        grid_unit: int = GRID_UNIT,
        grid_color: tuple[int, int, int] = GRID_COLOR,
        grid_opacity: int = GRID_OPACITY,
        show_grid: bool = True,
        first_group_order: int = 0,
    ) -> None:
        """
        Initialize background display.

        Args:
            batch: Pyglet batch for rendering.
            background_file: Path to background image file.
            logical_width: World width in pixels.
            logical_height: World height in pixels.
            grid_unit: Grid cell size in pixels.
            grid_color: RGB color for grid lines.
            grid_opacity: Grid line opacity (0-255).
            show_grid: Whether to render the grid initially.
            first_group_order: Rendering order for background.
        """
        super().__init__(batch)
        self.logical_w = logical_width
        self.logical_h = logical_height
        self.cell_size = grid_unit
        self.grid_color = grid_color
        self.grid_alpha = grid_opacity

        self.bg_sprite: Sprite | None = None
        self.grid_lines: list[Line] = []

        self.bg_group = Group(first_group_order)
        self.grid_group = Group(first_group_order + 1)

        self.set_background(background_file)
        if show_grid:
            self.build_grid()

    # Background

    def set_background(self, path: str) -> None:
        """
        Load and set background image, scaled to logical dimensions.

        Args:
            path: Path to background image file.
        """
        if self.bg_sprite:
            self.bg_sprite.delete()
            if self.bg_sprite in self.sub_objects:
                self.sub_objects.remove(self.bg_sprite)

        img = load(path)
        self.bg_sprite = self.register_sub_object(
            Sprite(
                img,
                x=0,
                y=0,
                batch=self.batch,
                group=self.bg_group,
            )
        )
        self.bg_sprite.scale_x = self.logical_w / img.width
        self.bg_sprite.scale_y = self.logical_h / img.height

    # Grid

    def build_grid(self) -> None:
        """
        Create grid visualization from Line objects.

        Generates vertical and horizontal lines spaced by grid_unit.
        """
        # Clear existing grid
        for ln in self.grid_lines:
            ln.delete()
            if ln in self.sub_objects:
                self.sub_objects.remove(ln)
        self.grid_lines.clear()

        cols = int(self.logical_w // self.cell_size)
        rows = int(self.logical_h // self.cell_size)

        # Vertical lines
        for c in range(cols + 1):
            x = c * self.cell_size
            ln = self.register_sub_object(
                Line(
                    x,
                    0,
                    x,
                    self.logical_h,
                    color=self.grid_color,
                    batch=self.batch,
                    group=self.grid_group,
                )
            )
            ln.opacity = self.grid_alpha
            self.grid_lines.append(ln)

        # Horizontal lines
        for r in range(rows + 1):
            y = r * self.cell_size
            ln = self.register_sub_object(
                Line(
                    0,
                    y,
                    self.logical_w,
                    y,
                    color=self.grid_color,
                    batch=self.batch,
                    group=self.grid_group,
                )
            )
            ln.opacity = self.grid_alpha
            self.grid_lines.append(ln)

    def toggle_grid(self, visible: bool) -> None:
        """
        Show or hide grid lines.

        Args:
            visible: True to show grid, False to hide.
        """
        for ln in self.grid_lines:
            ln.visible = visible

    # Cleanup

    def delete(self) -> None:
        """Clean up background and grid resources."""
        self.bg_sprite = None
        self.grid_lines.clear()
        super().delete()
