# External libraries
import struct
from enum import IntEnum


# Internal libraries
from common.config import (
    MAX_WALL_CHANGES,
    WALL_CHANGE_PACKED_SIZE,
)


class WallOperation(IntEnum):
    """Wall change operations for network transmission."""

    ADD = 1
    REMOVE = 2


class StateWalls:
    """
    Grid-based wall state with network transmission support.

    Manages wall cells for collision detection and rendering. Tracks
    changes in a buffer for efficient network transmission. Supports
    loading and saving wall configurations from files.
    """

    def __init__(
        self, grid_unit: int, world_width: int, world_height: int
    ) -> None:
        """
        Initialize walls state.

        Args:
            grid_unit: Size of each grid cell in pixels.
            world_width: Total world width in pixels.
            world_height: Total world height in pixels.
        """
        self.grid_unit = grid_unit
        self.world_width = world_width
        self.world_height = world_height
        self.cells: set[tuple[int, int]] = set()
        self.change_buffer: list[tuple[WallOperation, int, int]] = []

    # Coordinate conversion

    def to_cell(self, px: float, py: float) -> tuple[int, int]:
        """
        Convert pixel coordinates to grid cell indices.

        Args:
            px: X coordinate in pixels.
            py: Y coordinate in pixels.

        Returns:
            Tuple of (cell_x, cell_y).
        """
        return int(px // self.grid_unit), int(py // self.grid_unit)

    def to_px(self, cx: int, cy: int) -> tuple[int, int]:
        """
        Convert grid cell indices to pixel coordinates.

        Args:
            cx: Cell X index.
            cy: Cell Y index.

        Returns:
            Tuple of (pixel_x, pixel_y) for bottom-left corner.
        """
        return cx * self.grid_unit, cy * self.grid_unit

    def is_valid_cell(self, cx: int, cy: int) -> bool:
        """
        Check if cell coordinates are within grid bounds.

        Args:
            cx: Cell X index.
            cy: Cell Y index.

        Returns:
            True if cell is valid, False otherwise.
        """
        max_x = int(self.world_width // self.grid_unit)
        max_y = int(self.world_height // self.grid_unit)
        return 0 <= cx < max_x and 0 <= cy < max_y

    # Query methods

    def has_wall(self, cx: int, cy: int) -> bool:
        """
        Check if a wall exists at grid cell.

        Args:
            cx: Cell X index.
            cy: Cell Y index.

        Returns:
            True if wall exists, False otherwise.
        """
        return (cx, cy) in self.cells

    def has_wall_at_pos(self, px: float, py: float) -> bool:
        """
        Check if a wall exists at pixel coordinates.

        Args:
            px: X coordinate in pixels.
            py: Y coordinate in pixels.

        Returns:
            True if wall exists, False otherwise.
        """
        cx, cy = self.to_cell(px, py)
        return self.has_wall(cx, cy)

    def get_wall_cells(self) -> set[tuple[int, int]]:
        """
        Get a copy of all wall cell coordinates.

        Returns:
            Set of (cell_x, cell_y) tuples.
        """
        return self.cells.copy()

    def get_neighbors(
        self, cx: int, cy: int
    ) -> list[tuple[int, int]]:
        """
        Get neighboring cells with walls (4-directional).

        Args:
            cx: Cell X index.
            cy: Cell Y index.

        Returns:
            List of neighboring (cell_x, cell_y) tuples with walls.
        """
        directions = [(0, 1), (1, 0), (0, -1), (-1, 0)]
        neighbors = []
        for dx, dy in directions:
            nx, ny = cx + dx, cy + dy
            if self.has_wall(nx, ny):
                neighbors.append((nx, ny))
        return neighbors

    # State modification

    def add_wall(
        self, cx: int, cy: int, track_change: bool = True
    ) -> None:
        """
        Add a wall at grid cell.

        Args:
            cx: Cell X index.
            cy: Cell Y index.
            track_change: Whether to buffer change for transmission.
        """
        if not self.is_valid_cell(cx, cy):
            return

        if (cx, cy) not in self.cells:
            self.cells.add((cx, cy))
            if track_change:
                self.change_buffer.append((WallOperation.ADD, cx, cy))

    def remove_wall(
        self, cx: int, cy: int, track_change: bool = True
    ) -> None:
        """
        Remove a wall at grid cell.

        Args:
            cx: Cell X index.
            cy: Cell Y index.
            track_change: Whether to buffer change for transmission.
        """
        if (cx, cy) in self.cells:
            self.cells.discard((cx, cy))
            if track_change:
                self.change_buffer.append(
                    (WallOperation.REMOVE, cx, cy)
                )

    def add_rect(
        self,
        cx: int,
        cy: int,
        w_cells: int,
        h_cells: int,
        track_change: bool = True,
    ) -> None:
        """
        Add a rectangular block of walls.

        Args:
            cx: Starting cell X index.
            cy: Starting cell Y index.
            w_cells: Width in cells.
            h_cells: Height in cells.
            track_change: Whether to buffer changes for transmission.
        """
        for gx in range(cx, cx + w_cells):
            for gy in range(cy, cy + h_cells):
                self.add_wall(gx, gy, track_change)

    def clear_area(
        self,
        cx: int,
        cy: int,
        w_cells: int,
        h_cells: int,
        track_change: bool = True,
    ) -> None:
        """
        Remove all walls in a rectangular area.

        Args:
            cx: Starting cell X index.
            cy: Starting cell Y index.
            w_cells: Width in cells.
            h_cells: Height in cells.
            track_change: Whether to buffer changes for transmission.
        """
        for gx in range(cx, cx + w_cells):
            for gy in range(cy, cy + h_cells):
                self.remove_wall(gx, gy, track_change)

    def clear(self, track_change: bool = False) -> None:
        """
        Remove all walls.

        Args:
            track_change: Whether to buffer each removal. Warning: can
                generate large change buffers.
        """
        if track_change:
            for cx, cy in list(self.cells):
                self.remove_wall(cx, cy, track_change=True)
        else:
            self.cells.clear()

    # Network transmission

    def has_changes(self) -> bool:
        """
        Check if there are pending changes in buffer.

        Returns:
            True if buffer contains changes, False otherwise.
        """
        return len(self.change_buffer) > 0

    def pack_changes(self) -> bytes | None:
        """
        Pack buffered changes into binary format for transmission.

        Does NOT clear buffer. Format: [2 bytes: count] then
        [WALL_CHANGE_PACKED_SIZE bytes per change].

        Returns:
            Packed binary data or None if no changes.

        Raises:
            ValueError: If too many changes to fit in packet.
        """
        if not self.change_buffer:
            return None

        num_changes = len(self.change_buffer)
        if num_changes > MAX_WALL_CHANGES:
            raise ValueError(
                f"Too many changes: {num_changes} "
                f"(max {MAX_WALL_CHANGES})"
            )

        data = bytearray()
        data.extend(struct.pack("!H", num_changes))

        for operation, cx, cy in self.change_buffer:
            data.append(operation)
            data.extend(struct.pack("!HH", cx, cy))

        return bytes(data)

    def clear_buffer(self) -> None:
        """Clear the change buffer without packing."""
        self.change_buffer.clear()

    def unpack_changes(
        self, packed_data: bytes
    ) -> tuple[set[tuple[int, int]], set[tuple[int, int]]]:
        """
        Apply packed changes from network and return what changed.

        Args:
            packed_data: Binary data containing packed changes.

        Returns:
            Tuple of (added_cells, removed_cells) sets.

        Raises:
            ValueError: If packet format is invalid.
        """
        if not packed_data:
            return (set(), set())

        if len(packed_data) < 2:
            raise ValueError("Packet too small")

        offset = 0
        num_changes = struct.unpack("!H", packed_data[offset: offset + 2])[
            0
        ]
        offset += 2

        # Validate packet size
        expected_size = 2 + (num_changes * WALL_CHANGE_PACKED_SIZE)
        if len(packed_data) != expected_size:
            raise ValueError(
                f"Invalid packet size: expected {expected_size}, "
                f"got {len(packed_data)}"
            )

        added_cells: set[tuple[int, int]] = set()
        removed_cells: set[tuple[int, int]] = set()

        for _ in range(num_changes):
            operation = WallOperation(packed_data[offset])
            offset += 1

            cx, cy = struct.unpack("!HH", packed_data[offset: offset + 4])
            offset += 4

            # Validate coordinates
            if not self.is_valid_cell(cx, cy):
                raise ValueError(f"Invalid cell coordinates: ({cx}, {cy})")

            if operation == WallOperation.ADD:
                self.add_wall(cx, cy, track_change=False)
                added_cells.add((cx, cy))
            elif operation == WallOperation.REMOVE:
                self.remove_wall(cx, cy, track_change=False)
                removed_cells.add((cx, cy))

        return (added_cells, removed_cells)

    # File I/O

    def load_from_data(
        self, grid_lines: list[str], track_change: bool = False
    ) -> None:
        """
        Load walls from grid representation.

        grid_lines[0] is the TOP row (high Y), last row is bottom (Y=0).
        '1' represents a wall, '0' represents empty space.

        Args:
            grid_lines: List of strings representing grid rows.
            track_change: Whether to buffer changes for transmission.
        """
        self.clear(track_change=False)
        num_rows = len(grid_lines)
        for row_idx, line in enumerate(grid_lines):
            cy = num_rows - 1 - row_idx
            for cx, char in enumerate(line):
                if char == "1":
                    self.add_wall(cx, cy, track_change)

    def create_walls_data(self) -> list[str]:
        """
        Create grid representation of current walls.

        Each string is a row where '1' = wall, '0' = empty.
        First line is TOP row (high Y).

        Returns:
            List of strings representing walls.
        """
        width_cells = int(self.world_width // self.grid_unit)
        height_cells = int(self.world_height // self.grid_unit)
        rows = []
        for row_idx in range(height_cells):
            cy = height_cells - 1 - row_idx
            row = "".join(
                "1" if (cx, cy) in self.cells else "0"
                for cx in range(width_cells)
            )
            rows.append(row)
        return rows

    def load_from_file(
        self, filepath: str, track_change: bool = False
    ) -> None:
        """
        Load wall configuration from a text file.

        Args:
            filepath: Path to the configuration file.
            track_change: Whether to buffer changes for transmission.
        """
        with open(filepath, "r") as f:
            lines = [line.strip() for line in f if line.strip()]
        self.load_from_data(lines, track_change)

    def save_to_file(self, filepath: str) -> None:
        """
        Save current wall configuration to a text file.

        Args:
            filepath: Path where configuration will be saved.
        """
        grid = self.create_walls_data()
        with open(filepath, "w") as f:
            for row in grid:
                f.write(row + "\n")
