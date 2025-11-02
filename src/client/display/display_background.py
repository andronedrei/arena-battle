# External libraries
from pyglet.image import load
from pyglet.sprite import Sprite
from pyglet.graphics import Batch, Group
from pyglet.shapes import Line
from typing import Tuple

# Internal libraries
from client.display.batch_object import BatchObject
from common.config import LOGICAL_SCREEN_WIDTH, LOGICAL_SCREEN_HEIGHT
from common.config import GRID_UNIT
from client.config import GRID_COLOR, GRID_OPACITY, BACKGROUND_FILE


class DisplayBackground(BatchObject):
    """
    Renders a background image and a grid into the provided Batch,
    using Groups for layering order in rendering
    """

    def __init__(
        self,
        batch: Batch,
        background_file: str = BACKGROUND_FILE,
        logical_width: int = LOGICAL_SCREEN_WIDTH,
        logical_height: int = LOGICAL_SCREEN_HEIGHT,
        grid_unit: int = GRID_UNIT,
        grid_color: Tuple[int, int, int] = GRID_COLOR,
        grid_opacity: int = GRID_OPACITY,
        show_grid: bool = True,
        first_group_order: int = 0,  # bg img at 0, grids at group order 1
    ):
        super().__init__(batch)
        self.logical_w = logical_width
        self.logical_h = logical_height
        self.cell_size = grid_unit
        self.grid_color = grid_color
        self.grid_alpha = grid_opacity

        self.bg_sprite = None
        self.grid_lines: list[Line] = []

        # Draw order: background first, then grid
        self.bg_group = Group(first_group_order)
        self.grid_group = Group(first_group_order + 1)

        self.set_background(background_file)
        if show_grid:
            self.build_grid()

    def set_background(self, path: str):
        """ Load/replace background Sprite and scale to logical size """
        if self.bg_sprite:
            self.bg_sprite.delete()
            # Remove from tracked sub-objects
            if self.bg_sprite in self._sub_objects:
                self._sub_objects.remove(self.bg_sprite)

        img = load(path)
        self.bg_sprite = self.register_sub_object(
            Sprite(
                img, x=0, y=0,
                batch=self.batch,
                group=self.bg_group
            )
        )
        self.bg_sprite.scale_x = self.logical_w / img.width
        self.bg_sprite.scale_y = self.logical_h / img.height

    def build_grid(self):
        """ Create a spaced grid using pyglet.shapes.Line objects """
        # Clear any existing lines
        for ln in self.grid_lines:
            ln.delete()
            # Remove from tracked sub-objects
            if ln in self._sub_objects:
                self._sub_objects.remove(ln)
        self.grid_lines.clear()

        cols = int(self.logical_w // self.cell_size)
        rows = int(self.logical_h // self.cell_size)

        # Vertical lines
        for c in range(cols + 1):
            x = c * self.cell_size
            ln = self.register_sub_object(
                Line(
                    x, 0, x, self.logical_h,
                    color=self.grid_color,
                    batch=self.batch,
                    group=self.grid_group
                )
            )
            ln.opacity = self.grid_alpha
            self.grid_lines.append(ln)

        # Horizontal lines
        for r in range(rows + 1):
            y = r * self.cell_size
            ln = self.register_sub_object(
                Line(
                    0, y, self.logical_w, y,
                    color=self.grid_color,
                    batch=self.batch,
                    group=self.grid_group
                )
            )
            ln.opacity = self.grid_alpha
            self.grid_lines.append(ln)

    def toggle_grid(self, visible: bool):
        """ Show or hide grid lines """
        for ln in self.grid_lines:
            ln.visible = visible

    def delete(self):
        """ Cleanup background and grid resources from the batch """
        self.bg_sprite = None
        self.grid_lines.clear()
        super().delete()  # Auto-cleans all registered sub-objects
