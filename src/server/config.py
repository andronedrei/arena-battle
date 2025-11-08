"""
Server-side configuration parameters.

Organized into two categories:
1. TUNABLE - Safe to modify for gameplay balance and difficulty tuning
2. CRITICAL - Game logic constants; do not modify
"""

import math

# Available AI strategies
from server.strategy.random_strategy import RandomStrategy


# ============================================================================
# TUNABLE PARAMETERS - Adjust for gameplay balance and difficulty
# ============================================================================

# Agent properties
DEFAULT_AGENT_HEALTH = 100.0
DEFAULT_AGENT_DAMAGE = 20.0
DEFAULT_AGENT_SPEED = 50.0

# Weapon mechanics
DEFAULT_SHOOT_DURATION = 1.0  # Cooldown between shots (seconds)
BULLET_SPEED = 100.0  # Pixels per second
BULLET_SPAWN_OFFSET_RATIO = 1.2  # Ratio compared to r

# Magazine / reload
DEFAULT_MAGAZINE_SIZE = 6  # Bullets per magazine
DEFAULT_RELOAD_DURATION = 2.0  # Seconds to reload a magazine

# Agent behavior
AGENT_GUN_ROTATION_SPEED = 2.0 * math.pi / 5.0  # Radians per second
DETECTION_INTERVAL = 5  # Frames between enemy detection scans

# Game setup
# Format: (x, y, strategy_class)
# Each tuple defines spawn position and AI strategy for that agent
TEAM_A_SPAWNS = [
    (160.0, 120.0, RandomStrategy),
    (160.0, 600.0, RandomStrategy),
    (320.0, 480.0, RandomStrategy),
]

TEAM_B_SPAWNS = [
    (1120.0, 100.0, RandomStrategy),
    (1120.0, 650.0, RandomStrategy),
    (960.0, 480.0, RandomStrategy),
]

REQUIRED_CLIENTS_TO_START = 2  # Minimum players to begin game


# ============================================================================
# CRITICAL PARAMETERS - Game logic constants; do not modify
# ============================================================================

# Internal sentinel values (protocol and game logic)
NO_SHOOT = -1.0  # Indicates weapon is loaded and ready to fire


# ============================================================================
# Note: Network configuration (NETWORK_HOST, NETWORK_PORT,
# MESSAGE_TYPE_*) is defined in common.config to ensure client-server sync
# ============================================================================
