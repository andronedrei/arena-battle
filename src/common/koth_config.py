"""
King of the Hill game mode configuration.

Defines the hill zone, scoring rules, and win conditions.
"""

# ============================================================================
# KOTH ZONE CONFIGURATION
# ============================================================================

# Hill zone position and size (in pixels)
KOTH_ZONE_CENTER_X = 640  # Center of 1280 wide screen
KOTH_ZONE_CENTER_Y = 360  # Center of 720 high screen
KOTH_ZONE_RADIUS = 100    # Radius of the circular hill zone

# Alternative: Rectangular zone
KOTH_ZONE_RECT_X = 540      # Top-left X
KOTH_ZONE_RECT_Y = 260      # Top-left Y
KOTH_ZONE_RECT_WIDTH = 200  # Width
KOTH_ZONE_RECT_HEIGHT = 200 # Height

# Zone shape: "circle" or "rectangle"
KOTH_ZONE_SHAPE = "circle"


# ============================================================================
# KOTH SCORING RULES
# ============================================================================

# Points awarded per second of zone control
KOTH_POINTS_PER_SECOND = 10.0

# Time interval for point accumulation (in seconds)
# Points are awarded every KOTH_SCORING_INTERVAL
KOTH_SCORING_INTERVAL = 0.5  # Award points twice per second

# Contested zone behavior
# If True, no points are awarded when multiple teams are in zone
# If False, team with more agents gets points
KOTH_CONTESTED_BLOCKS_SCORING = True


# ============================================================================
# KOTH WIN CONDITIONS
# ============================================================================

# Maximum points to win the game
KOTH_MAX_POINTS = 1000

# Maximum game duration in seconds (0 = no time limit)
KOTH_MAX_DURATION = 180.0  # 3 minutes

# Minimum agents per team at game start
KOTH_MIN_AGENTS_PER_TEAM = 2


# ============================================================================
# KOTH VISUAL CONFIGURATION (Client-side)
# ============================================================================

# Hill zone colors
KOTH_ZONE_NEUTRAL_COLOR = (150, 150, 150)  # Gray when neutral
KOTH_ZONE_TEAM_A_COLOR = (100, 200, 255)   # Blue when Team A controls
KOTH_ZONE_TEAM_B_COLOR = (255, 100, 100)   # Red when Team B controls
KOTH_ZONE_CONTESTED_COLOR = (255, 255, 100)  # Yellow when contested

# Zone opacity
KOTH_ZONE_OPACITY = 100

# Zone border
KOTH_ZONE_BORDER_WIDTH = 3
KOTH_ZONE_BORDER_COLOR = (255, 255, 255)


# ============================================================================
# NETWORK MESSAGE TYPES
# ============================================================================

# Message type for KOTH game state updates
MSG_TYPE_KOTH_STATE = 0x10