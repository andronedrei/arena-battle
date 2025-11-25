"""
Capture the Flag game mode configuration.

Defines flag positions, capture zones, scoring rules, and win conditions.
"""

# ============================================================================
# CTF FLAG POSITIONS
# ============================================================================

# Team A flag base (left side of map)
CTF_FLAG_TEAM_A_BASE_X = 100
CTF_FLAG_TEAM_A_BASE_Y = 360

# Team B flag base (right side of map)
CTF_FLAG_TEAM_B_BASE_X = 1180
CTF_FLAG_TEAM_B_BASE_Y = 360

# Flag capture radius (how close agent must be to pick up flag)
CTF_FLAG_PICKUP_RADIUS = 30

# Flag return radius (how close flag must be to base to be returned/captured)
# Increased to 150 for easier flag capture/return near base
CTF_FLAG_RETURN_RADIUS = 150


# ============================================================================
# CTF SCORING RULES
# ============================================================================

# Points awarded per flag capture
CTF_POINTS_PER_CAPTURE = 1

# Flag drop behavior
CTF_FLAG_DROPS_ON_DEATH = True  # If True, flag drops when carrier dies
CTF_FLAG_AUTO_RETURN_TIME = 30.0  # Seconds before dropped flag auto-returns (0 = never)


# ============================================================================
# CTF WIN CONDITIONS
# ============================================================================

# Maximum captures to win the game (set to 1 for first capture wins)
CTF_MAX_CAPTURES = 1

# Maximum game duration in seconds (0 = no time limit)
CTF_MAX_DURATION = 300.0  # 5 minutes

# Minimum agents per team at game start
CTF_MIN_AGENTS_PER_TEAM = 2


# ============================================================================
# CTF VISUAL CONFIGURATION (Client-side)
# ============================================================================

# Flag colors (matches team colors from client/config.py)
CTF_FLAG_TEAM_A_COLOR = (100, 200, 255)  # Blue
CTF_FLAG_TEAM_B_COLOR = (255, 100, 100)  # Red

# Flag opacity
CTF_FLAG_OPACITY = 255

# Capture zone visualization
CTF_CAPTURE_ZONE_COLOR = (255, 215, 0)  # Gold/auriu
CTF_CAPTURE_ZONE_OPACITY = 120  # Increased for better visibility


# ============================================================================
# NETWORK MESSAGE TYPES
# ============================================================================

# Message type for CTF game state updates (defined in common/config.py)
# MSG_TYPE_CTF_STATE = 0x13
