# client/objects/walls_display.py
# External libraries
from pyglet.graphics import Batch, Group
from pyglet.shapes import Rectangle

# Internal libraries
from client.display.batch_object import BatchObject
from common.states.state_walls import StateWalls
from client.config import WALL_COLOR, WALL_OPACITY


class DisplayWalls(BatchObject):
    """
    Pure visual representation of WallsState.
    Only handles rendering - no game logic.
    """

    def __init__(self, batch: Batch, grid_unit: int, world_width: int,
                 world_height: int, walls_config_file: str | None = None,
                 group_order: int = 2, color:
                 tuple[int, int, int] = WALL_COLOR, opacity: int = WALL_OPACITY
                 ):
        """
        Constructor
        """
        super().__init__(batch)

        # Create empty state (all walls = 0)
        self.state = StateWalls(grid_unit, world_width, world_height)

        self.group_order = Group(group_order)
        self.color = color
        self.opacity = opacity

        # Visual representations: {(cx, cy): Rectangle}
        self.visuals: dict[tuple[int, int], Rectangle] = {}

        if walls_config_file:
            self.load_from_file(walls_config_file)

    def sync_from_bytes(self, packed_data: bytes):
        """
        Apply updates (sent as a packet via network) and sync visuals.
        Call this when receiving wall updates from server.
        """
        # Apply changes of what got changed
        changes = self.state.apply_packed_changes(packed_data)

        if not changes:
            return

        added_cells, removed_cells = changes

        for (cx, cy) in added_cells:
            self.add_wall_visual(cx, cy)

        for (cx, cy) in removed_cells:
            self.remove_wall_visual(cx, cy)

    def load_from_file(self, filepath: str):
        """
        Load walls from file and create visuals.
        Call this for initial map loading.
        """
        # Load into state (uses state's method)
        self.state.load_from_file(filepath, track_change=False)

        # Create visuals for all loaded walls
        for (cx, cy) in self.state.get_wall_cells():
            self.add_wall_visual(cx, cy)

    def add_wall_visual(self, cx: int, cy: int):
        """ Create visual for wall at grid cell. """
        if (cx, cy) in self.visuals:
            return

        # Use state's method to convert cell to pixels
        x, y = self.state.to_px(cx, cy)

        rect = self.register_sub_object(
            Rectangle(
                x, y,
                self.state.grid_unit,
                self.state.grid_unit,
                color=self.color,
                batch=self.batch,
                group=self.group_order
            )
        )
        rect.opacity = self.opacity
        self.visuals[(cx, cy)] = rect

    def remove_wall_visual(self, cx: int, cy: int):
        """ Remove visual for wall at grid cell. """
        rect = self.visuals.pop((cx, cy), None)
        if rect:
            rect.delete()
            if rect in self.sub_objects:
                self.sub_objects.remove(rect)

    def delete(self):
        """ Remove all wall visuals and cleanup resources. """
        self.visuals.clear()
        super().delete()
