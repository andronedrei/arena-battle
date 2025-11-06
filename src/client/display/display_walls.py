# External libraries
from pyglet.graphics import Batch, Group
from pyglet.shapes import Rectangle


# Internal libraries
from client.config import WALL_COLOR, WALL_OPACITY
from client.display.batch_object import BatchObject
from common.states.state_walls import StateWalls


class DisplayWalls(BatchObject):
    """
    Visual representation of wall state.

    Manages rendering of grid-based walls using pyglet shapes.
    Syncs with StateWalls for game state changes.
    """

    def __init__(
        self,
        batch: Batch,
        grid_unit: int,
        world_width: int,
        world_height: int,
        walls_config_file: str | None = None,
        group_order: int = 2,
        color: tuple[int, int, int] = WALL_COLOR,
        opacity: int = WALL_OPACITY,
    ) -> None:
        """
        Initialize the walls display.

        Args:
            batch: Pyglet batch for rendering.
            grid_unit: Size of each grid cell in pixels.
            world_width: Total world width in pixels.
            world_height: Total world height in pixels.
            walls_config_file: Optional path to load walls from.
            group_order: Rendering order (z-depth).
            color: RGB color tuple for walls.
            opacity: Opacity value (0-255).
        """
        super().__init__(batch)

        self.state = StateWalls(grid_unit, world_width, world_height)
        self.group_order = Group(group_order)
        self.color = color
        self.opacity = opacity
        self.visuals: dict[tuple[int, int], Rectangle] = {}

        if walls_config_file:
            self.load_from_file(walls_config_file)

    # Loading

    def load_from_file(self, filepath: str) -> None:
        """
        Load walls from file and create visuals.

        Args:
            filepath: Path to the walls configuration file.
        """
        self.state.load_from_file(filepath, track_change=False)

        for cx, cy in self.state.get_wall_cells():
            self.add_wall_visual(cx, cy)

    # Synchronization

    def unpack_changes(self, packed_data: bytes) -> None:
        """
        Apply network updates and sync visuals with state.

        Args:
            packed_data: Serialized wall changes from server.
        """
        added_cells, removed_cells = self.state.unpack_changes(
            packed_data
        )

        for cx, cy in added_cells:
            self.add_wall_visual(cx, cy)

        for cx, cy in removed_cells:
            self.remove_wall_visual(cx, cy)

    # Visual management

    def add_wall_visual(self, cx: int, cy: int) -> None:
        """
        Create and register visual for a wall cell.

        Args:
            cx: Cell X index.
            cy: Cell Y index.
        """
        if (cx, cy) in self.visuals:
            return

        x, y = self.state.to_px(cx, cy)

        rect = self.register_sub_object(
            Rectangle(
                x,
                y,
                self.state.grid_unit,
                self.state.grid_unit,
                color=self.color,
                batch=self.batch,
                group=self.group_order,
            )
        )
        rect.opacity = self.opacity
        self.visuals[(cx, cy)] = rect

    def remove_wall_visual(self, cx: int, cy: int) -> None:
        """
        Remove visual for a wall cell.

        Args:
            cx: Cell X index.
            cy: Cell Y index.
        """
        rect = self.visuals.pop((cx, cy), None)
        if rect:
            rect.delete()
            if rect in self.sub_objects:
                self.sub_objects.remove(rect)

    # Cleanup

    def delete(self) -> None:
        """Clean up all wall visuals and resources."""
        self.visuals.clear()
        super().delete()
