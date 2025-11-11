"""
Shared configuration between client and server.

Organized into two categories:
1. TUNABLE - Safe to modify for gameplay tweaking and customization
2. CRITICAL - Protocol/network constants; changes break client-server sync
"""

import math
from enum import IntEnum


class Direction(IntEnum):
    """Eight-directional movement."""

    NORTH = 0
    NORTH_EAST = 1
    EAST = 2
    SOUTH_EAST = 3
    SOUTH = 4
    SOUTH_WEST = 5
    WEST = 6
    NORTH_WEST = 7


# ============================================================================
# TUNABLE PARAMETERS - Safe to modify for balance and customization
# ============================================================================

# World geometry
LOGICAL_SCREEN_WIDTH = 1280
LOGICAL_SCREEN_HEIGHT = 720
GRID_UNIT = 5

# Timing
SIMULATION_TICK_RATE = 30  # Server simulation rate (Hz)
NETWORK_UPDATE_RATE = 15  # Network broadcast rate (Hz), also FPS in client

# Entity properties
DEFAULT_ENTITY_RADIUS = 20

# Vision system (field-of-view ray casting)
FOV_RATIO = 40.0  # FOV radius = entity.radius * FOV_RATIO
FOV_OPENING = math.pi / 3  # FOV cone angle in radians (60 degrees)
FOV_NUM_RAYS = 25  # Ray-cast samples (more = smoother detection)
FOV_OPACITY = 80  # FOV polygon transparency (0-255, client only)
RAY_STEP_DIVISOR = 2  # Ray casting precision (grid_unit / divisor)

# Asset files
WALL_CONFIG = "common/wall_configs/walls_config1.txt"


# ============================================================================
# CRITICAL PARAMETERS - Do not modify; breaks protocol synchronization
# ============================================================================

# Network message type codes (must match exactly between client and server)
MSG_TYPE_ENTITIES = 0x02
MSG_TYPE_WALLS = 0x03
MSG_TYPE_BULLETS = 0x04
MSG_TYPE_CLIENT_READY = 0x05
MSG_TYPE_START_GAME = 0x06

# Network configuration (server connection)
WEBSOCKET_ROUTE = "/ws"
NETWORK_HOST = "localhost"
NETWORK_PORT = 8765
NETWORK_SERVER_URI = f"ws://{NETWORK_HOST}:{NETWORK_PORT}{WEBSOCKET_ROUTE}"

# Protocol limits (must not exceed these values)
MAX_ENTITY_ID = 65535
MAX_ENTITIES_COUNT = 65535
MAX_BULLET_ID = 65535
MAX_BULLETS_COUNT = 65535
MAX_WALL_CHANGES = 65535
MAX_CELL_COORDINATE = 65535

# Note: Binary packet structure sizes (in bytes). If you change these,
# make sure client and server stay in sync.

# Entity packet layout changed to include health (float) and ammo (uint16).
# Format bytes: id:uint16 (2) + x:float (4) + y:float (4) + radius:float (4)
# + gun_angle:float (4) + team:uint8 (1) + health:float (4) + ammo:uint16 (2)
ENTITY_PACKED_SIZE = 25  # 2+4+4+4+4+1+4+2
BULLET_PACKED_SIZE = 17  # 2+4+4+4+2+1
WALL_CHANGE_PACKED_SIZE = 5  # 1+2+2

# Ammo sentinel value: if ammo equals this, treat as infinite on client UI.
AMMO_INFINITE = 65535
