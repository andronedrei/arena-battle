'''
CAN MODIFY FOR NOW (PROBABLY)
'''

WALL_CONFIG = "common/wall_configs/walls_config1.txt"

LOGICAL_SCREEN_WIDTH = 1280
LOGICAL_SCREEN_HEIGHT = 720
GRID_UNIT = 5
FPS = 10

# === FOV CONSTANTS ===
FOV_RATIO = 50.0  # FOV radius = entity.radius * FOV_RATIO
FOV_OPENING = 3.14159 / 3  # 60 degrees in radians (use math.pi in imports)
FOV_NUM_RAYS = 50  # Number of rays to cast (more = smoother)
FOV_OPACITY = 80  # Semi-transparent FOV visualization (client only)

# === RAY CASTING ===
RAY_STEP_DIVISOR = 2  # step_size = grid_unit / RAY_STEP_SIZE_RATIO

DEFAULT_ENTITY_RADIUS = 2
