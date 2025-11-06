"""
Client configuration parameters.

Organized into two categories:
1. TUNABLE - Safe to experiment with different values
2. CRITICAL - May break game behavior if modified
"""


# ============================================================================
# TUNABLE PARAMETERS - Safe to modify for visual customization and tweaking
# ============================================================================

# Grid visualization
GRID_COLOR = (0, 100, 0)
GRID_OPACITY = 30

# Wall rendering
WALL_COLOR = (255, 255, 255)
WALL_OPACITY = 255

# Team colors
TEAM_COLORS = {
    0: (200, 200, 200),   # NEUTRAL - Gray
    1: (100, 200, 255),   # TEAM_A - Blue
    2: (255, 100, 100),   # TEAM_B - Red
}
DEFAULT_COLOR = (255, 255, 255)

# Entity visuals
GUN_LENGTH_RATIO = 1.2  # Gun length = entity.radius * GUN_LENGTH_RATIO
GUN_WIDTH_RATIO = 0.2   # Gun width = entity.radius * GUN_WIDTH_RATIO
GUN_COLOR = (0, 0, 0)   # Black
BULLET_COLOR = (0, 255, 0)  # Green

# Rendering layer offsets by team (prevents FOV flickering)
# Each team gets a unique base layer to avoid visual conflicts
TEAM_RENDER_ORDERS = {
    1: 2,  # TEAM_A - FOV at 2, Body at 3, Gun at 4
    2: 3,  # TEAM_B - FOV at 3, Body at 4, Gun at 5
}


# ============================================================================
# CRITICAL PARAMETERS - Do not modify unless you understand the consequences
# ============================================================================

# Asset files (must exist at specified paths)
BACKGROUND_FILE = "client/assets/background.png"

# Projection matrix bounds (controls rendering depth)
# Modify only if changing 3D depth layering
Z_NEAR = -255
Z_FAR = 255
