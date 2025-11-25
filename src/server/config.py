"""
Server-side configuration parameters.

Organized into two categories:
1. TUNABLE - Safe to modify for gameplay balance and difficulty tuning
2. CRITICAL - Game logic constants; do not modify
"""

import math

# Available AI strategies
from server.strategy.random_strategy import RandomStrategy
from server.strategy.aggressive_survival_strategy import AggressiveSurvivalStrategy
from server.strategy.koth_strategy import KOTHStrategy
from server.strategy.ctf_strategy import CTFStrategy
from server.strategy.ctf_base_defender_strategy import CTFBaseDefenderStrategy


# ============================================================================
# TUNABLE PARAMETERS - Adjust for gameplay balance and difficulty
# ============================================================================

# Agent properties
DEFAULT_AGENT_HEALTH = 100.0
DEFAULT_AGENT_DAMAGE = 25.0  # Increased from 20.0 for faster kills
DEFAULT_AGENT_SPEED = 80.0  # Increased from 50.0 for faster movement

# Weapon mechanics
DEFAULT_SHOOT_DURATION = 0.8  # Reduced from 1.0 for faster shooting
BULLET_SPEED = 150.0  # Increased from 100.0 for faster bullets
BULLET_SPAWN_OFFSET_RATIO = 1.2

# Magazine / reload
DEFAULT_MAGAZINE_SIZE = 8  # Increased from 6
DEFAULT_RELOAD_DURATION = 1.5  # Reduced from 2.0 for faster reloads

# Agent behavior
AGENT_GUN_ROTATION_SPEED = 2.0 * math.pi / 3.0  # Faster gun rotation (was /5.0)
DETECTION_INTERVAL = 2  # Reduced from 5 for more frequent enemy detection

# Game setup - SURVIVAL MODE (3 agents per team)
TEAM_A_SPAWNS = [
    (160.0, 120.0, AggressiveSurvivalStrategy),
    (160.0, 600.0, AggressiveSurvivalStrategy),
    (320.0, 360.0, AggressiveSurvivalStrategy),
]

TEAM_B_SPAWNS = [
    (1120.0, 100.0, AggressiveSurvivalStrategy),
    (1120.0, 650.0, AggressiveSurvivalStrategy),
    (960.0, 360.0, AggressiveSurvivalStrategy),
]

# Game setup - KOTH MODE (3 agents per team)
TEAM_A_SPAWNS_KOTH = [
    (200.0, 200.0, KOTHStrategy),
    (200.0, 520.0, KOTHStrategy),
    (400.0, 360.0, KOTHStrategy),
]

TEAM_B_SPAWNS_KOTH = [
    (1080.0, 200.0, KOTHStrategy),
    (1080.0, 520.0, KOTHStrategy),
    (880.0, 360.0, KOTHStrategy),
]

# Game setup - CTF MODE (4 agents per team: 3 attackers + 1 base defender)
TEAM_A_SPAWNS_CTF = [
    (150.0, 280.0, CTFStrategy),
    (150.0, 440.0, CTFStrategy),
    (250.0, 240.0, CTFStrategy),
    (100.0, 360.0, CTFBaseDefenderStrategy),  # Base Defender - near flag
]

TEAM_B_SPAWNS_CTF = [
    (1150.0, 280.0, CTFStrategy),
    (1100.0, 440.0, CTFStrategy),
    (1000.0, 240.0, CTFStrategy),
    (1150.0, 360.0, CTFBaseDefenderStrategy),  # Base Defender - near flag (safe from walls)
]

REQUIRED_CLIENTS_TO_START = 1  # Changed to 1 so you can test alone


# ============================================================================
# CRITICAL PARAMETERS - Game logic constants; do not modify
# ============================================================================

# Internal sentinel values (protocol and game logic)
NO_SHOOT = -1.0  # Indicates weapon is loaded and ready to fire


# ============================================================================
# Note: Network configuration (NETWORK_HOST, NETWORK_PORT,
# MESSAGE_TYPE_*) is defined in common.config to ensure client-server sync
# ============================================================================