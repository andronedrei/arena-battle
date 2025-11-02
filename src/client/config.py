'''
File with parameters of the game.
'''

'''
CAN MODIFY FREELY WITHOUT EFFECTS (PROBABLY)
'''
GRID_COLOR = (0, 100, 0)
GRID_OPACITY = 30

WALL_COLOR = (255, 255, 255)
WALL_OPACITY = 255

TEAM_COLORS = {
    0: (200, 200, 200),   # NEUTRAL - Gray
    1: (100, 200, 255),   # TEAM_A - Blue
    2: (255, 100, 100),   # TEAM_B - Red
}
DEFAULT_COLOR = (255, 255, 255)

# === ENTITY VISUAL CONSTANTS ===
GUN_LENGTH_RATIO = 1.25  # Gun length = entity.radius * GUN_LENGTH_RATIO
GUN_WIDTH_RATIO = 0.2  # Gun width = entity.radius * GUN_WIDTH_RATIO
GUN_COLOR = (0, 0, 0)  # Red

'''
DO NOT MODIFY UNLESS YOU KNOW WHAT YOU DO, MIGHT ALTER BEHAVIOUR OF THE GAME
'''
BACKGROUND_FILE = "client/assets/background.png"  # relative to main script loc
WALLS_CONFIG_FILE = "common/wall_configs/walls_config1.txt"

