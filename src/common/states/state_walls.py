from enum import IntEnum
import struct


# Network protocol constants
MAX_WALL_CHANGES = 65535  # Maximum changes in single packet (uint16)
MAX_CELL_COORDINATE = 65535  # Maximum cell coordinate value (uint16)
WALL_CHANGE_PACKED_SIZE = 5  # Bytes per change: 1 (op) + 2 (cx) + 2 (cy)


class WallOperation(IntEnum):
    """ Wall change operations for network transmission. """
    ADD = 1
    REMOVE = 2


class StateWalls:
    """
    Pure wall data and logic with network transmission support.
    Manages grid-based wall cells for collision detection and rendering.
    """

    def __init__(self, grid_unit: int, world_width: int, world_height: int):
        """Constructor"""
        self.grid_unit = grid_unit
        self.world_width = world_width
        self.world_height = world_height
        self.cells: set[tuple[int, int]] = set()

        # Buffer for storing changes that will be sent over network
        self.change_buffer: list[tuple[WallOperation, int, int]] = []

    # === COORDINATE CONVERSION (GRID CELLS <=> PIXELS) ===

    def to_cell(self, px: float, py: float) -> tuple[int, int]:
        """ Convert pixel coordinates to grid cell indices. """
        return int(px // self.grid_unit), int(py // self.grid_unit)

    def to_px(self, cx: int, cy: int) -> tuple[int, int]:
        """ Convert grid cell indices to pixel coordinates (bottom-left). """
        return cx * self.grid_unit, cy * self.grid_unit

    def is_valid_cell(self, cx: int, cy: int) -> bool:
        """ Check if cell coordinates are within grid bounds. """
        max_x = int(self.world_width // self.grid_unit)
        max_y = int(self.world_height // self.grid_unit)
        return 0 <= cx < max_x and 0 <= cy < max_y

    # === QUERY METHODS ===

    def has_wall(self, cx: int, cy: int) -> bool:
        """ Check if a wall exists at grid cell (cx, cy). """
        return (cx, cy) in self.cells

    def has_wall_at_pos(self, px: float, py: float) -> bool:
        """ Check if a wall exists at pixel coordinates. """
        cx, cy = self.to_cell(px, py)
        return self.has_wall(cx, cy)

    def get_wall_cells(self) -> set[tuple[int, int]]:
        """ Get a copy of all wall cell coordinates. """
        return self.cells.copy()

    def get_neighbors(self, cx: int, cy: int) -> list[tuple[int, int]]:
        """ Get all neighboring cells (4-directional) that have walls. """
        directions = [(0, 1), (1, 0), (0, -1), (-1, 0)]
        neighbors = []
        for dx, dy in directions:
            nx, ny = cx + dx, cy + dy
            if self.has_wall(nx, ny):
                neighbors.append((nx, ny))
        return neighbors

    # === STATE MODIFYING METHODS ===

    def add_wall(self, cx: int, cy: int, track_change: bool = True):
        """
        Add a wall at grid cell (cx, cy).
        If track_change True, add the change to buffer
        for network transmission.
        """
        if not self.is_valid_cell(cx, cy):
            return

        if (cx, cy) not in self.cells:
            self.cells.add((cx, cy))
            if track_change:
                self.change_buffer.append((WallOperation.ADD, cx, cy))

    def remove_wall(self, cx: int, cy: int, track_change: bool = True):
        """
        Remove a wall at grid cell (cx, cy).
        If track_change True, add the change to buffer
        for network transmission.
        """
        if (cx, cy) in self.cells:
            self.cells.discard((cx, cy))
            if track_change:
                self.change_buffer.append((WallOperation.REMOVE, cx, cy))

    def add_rect(self, cx: int, cy: int, w_cells: int, h_cells: int,
                 track_change: bool = True):
        """ Add a rectangular block of walls starting at (cx, cy). """
        for gx in range(cx, cx + w_cells):
            for gy in range(cy, cy + h_cells):
                self.add_wall(gx, gy, track_change)

    def clear_area(self, cx: int, cy: int, w_cells: int, h_cells: int,
                   track_change: bool = True):
        """ Remove all walls in a rectangular area. """
        for gx in range(cx, cx + w_cells):
            for gy in range(cy, cy + h_cells):
                self.remove_wall(gx, gy, track_change)

    def clear(self, track_change: bool = False):
        """
        Remove all walls.
        If track_change True, track each removal (warning: can be very large!)
        """
        if track_change:
            for cx, cy in list(self.cells):
                self.remove_wall(cx, cy, track_change=True)
        else:
            self.cells.clear()

    # === NETWORK TRANSMISSION ===

    def has_changes(self) -> bool:
        """ Check if there are pending changes in buffer. """
        return len(self.change_buffer) > 0

    def pack_changes(self) -> bytes | None:
        """
        Pack buffered changes into binary format for network transmission.
        Does NOT clear buffer.

        Format:
        [2 bytes: count (uint16)]
        [WALL_CHANGE_PACKED_SIZE bytes per change]

        Returns:
            Packed binary data or None if no changes
        """
        if not self.change_buffer:
            return None

        num_changes = len(self.change_buffer)
        if num_changes > MAX_WALL_CHANGES:
            raise ValueError(
                f"Too many changes: {num_changes} (max {MAX_WALL_CHANGES})"
            )

        data = bytearray()
        data.extend(struct.pack('!H', num_changes))

        for operation, cx, cy in self.change_buffer:
            data.append(operation)
            data.extend(struct.pack('!HH', cx, cy))

        return bytes(data)

    def clear_buffer(self):
        """ Clear the change buffer without packing. """
        self.change_buffer.clear()

    def unpack_changes(self, packed_data: bytes) -> tuple[set, set]:
        """
        Apply packed changes received from network and return what changed.
        Modifies this state instance.

        Args:
            packed_data: Binary data containing packed changes

        Returns:
            Tuple of (added_cells, removed_cells)

        Raises:
            ValueError: If packet format is invalid
        """
        if not packed_data:
            return (set(), set())

        if len(packed_data) < 2:
            raise ValueError("Packet too small")

        offset = 0
        num_changes = struct.unpack('!H', packed_data[offset:offset+2])[0]
        offset += 2

        # Validate packet size
        expected_size = 2 + (num_changes * WALL_CHANGE_PACKED_SIZE)
        if len(packed_data) != expected_size:
            raise ValueError(
                f"Invalid pckt size: expected {expected_size}, "
                + "got {len(packed_data)}"
            )

        added_cells = set()
        removed_cells = set()

        for _ in range(num_changes):
            operation = WallOperation(packed_data[offset])
            offset += 1

            cx, cy = struct.unpack('!HH', packed_data[offset:offset+4])
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

    # === FILE I/O ===

    def load_from_data(self, grid_lines: list[str],
                       track_change: bool = False):
        """
        Load walls from a list of strings where '1' = wall, '0' = empty.
        grid_lines[0] is the TOP row (high Y), last row is bottom (Y=0).
        """
        self.clear(track_change=False)
        num_rows = len(grid_lines)
        for row_idx, line in enumerate(grid_lines):
            cy = num_rows - 1 - row_idx
            for cx, char in enumerate(line):
                if char == '1':
                    self.add_wall(cx, cy, track_change)

    def create_walls_data(self) -> list[str]:
        """
        Create a grid representation of current walls as list of strings.
        Each string is a row where '1' = wall, '0' = empty.
        First line is TOP row (high Y).

        Returns:
            List of strings representing walls
        """
        width_cells = int(self.world_width // self.grid_unit)
        height_cells = int(self.world_height // self.grid_unit)
        rows = []
        for row_idx in range(height_cells):
            cy = height_cells - 1 - row_idx
            row = ''.join('1' if (cx, cy) in self.cells else '0'
                          for cx in range(width_cells))
            rows.append(row)
        return rows

    def load_from_file(self, filepath: str, track_change: bool = False):
        """ Load wall configuration from a text file. """
        with open(filepath, 'r') as f:
            lines = [line.strip() for line in f if line.strip()]
        self.load_from_data(lines, track_change)

    def save_to_file(self, filepath: str):
        """ Save current wall configuration to a text file. """
        grid = self.create_walls_data()
        with open(filepath, 'w') as f:
            for row in grid:
                f.write(row + '\n')
