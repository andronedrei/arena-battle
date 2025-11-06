Arena Battle - Multiplayer AI Agent Combat Game
⚠️ CRITICAL NOTE: Performance Issue

Collision detection is currently checked twice per frame, resulting in significant performance overhead. This inefficiency will be addressed in a future optimization pass. For now, the game runs at reduced performance, particularly noticeable with many agents on screen. If performance is a concern during development, consider reducing agent count or FOV ray samples.
Project Overview

Arena Battle is a multiplayer real-time strategy game where AI agents from two teams compete in a shared arena. Teams coordinate movements, manage weapons, and detect enemies through a field-of-view (FOV) system. The project demonstrates client-server architecture, AI strategy patterns, and networked game state synchronization.

Key Features:

    6 agents (3 per team) with independent AI strategies

    Real-time FOV-based vision system with ray casting

    Network-synchronized game state

    Extensible strategy framework for custom AI behaviors

    8-directional movement and smooth gun rotation

    Health, damage, and weapon cooldown mechanics

Architecture Overview
Server-Side (server/)

    GameManager - Main simulation loop, entity updates, collision detection

    NetworkManager - WebSocket server, client synchronization, state broadcasting

    Agent - Entity with movement, vision, weapon systems

    Strategy - Abstract base class for AI behavior (RandomStrategy, HuntStrategy, etc.)

    Bullet - Projectile with lifetime, collision tracking

    Collision - Collision detection and resolution

Client-Side (client/)

    SceneGameplay - Main gameplay scene managing display objects

    DisplayEntity - Visual representation of agents with FOV polygon rendering

    DisplayBullet - Visual representation of projectiles

    DisplayWalls - Wall rendering and grid visualization

    NetworkClient - WebSocket connection to server

Shared (common/)

    StateEntity - Serializable agent state for network transmission

    StateBullet - Serializable bullet state

    StateWalls - Wall configuration and grid system

    config.py - Shared constants (Direction, FOV parameters, network config, protocol)

    direction.py - Direction enum (shared fundamental type)

Setup & Installation
Requirements

    Python 3.9+

    pyglet (rendering)

    quart (WebSocket server)

    aiofiles (async file operations)

Installation

# Clone repository
git clone <repo-url>
cd arena-battle

# Run setup script (creates venv and installs dependencies)
./setup.sh

Each client displays the shared game state with smooth rendering at 15 FPS.
Configuration
common/config.py - Shared Constants

    World geometry: LOGICAL_SCREEN_WIDTH, LOGICAL_SCREEN_HEIGHT, GRID_UNIT

    FOV system: FOV_RATIO, FOV_OPENING, FOV_NUM_RAYS, RAY_STEP_DIVISOR

    Network: MSG_TYPE_* constants, NETWORK_HOST, NETWORK_PORT, WEBSOCKET_ROUTE

    Direction enum: 8-directional movement vectors (NORTH, SOUTH, EAST, WEST, NORTH_EAST, SOUTH_EAST, SOUTH_WEST, NORTH_WEST)

server/config.py - Server Settings

    Agent stats: DEFAULT_AGENT_HEALTH, DEFAULT_AGENT_DAMAGE, DEFAULT_AGENT_SPEED

    Weapon mechanics: BULLET_SPEED, DEFAULT_SHOOT_DURATION, BULLET_SPAWN_OFFSET_RATIO

    Spawn positions: TEAM_A_SPAWNS, TEAM_B_SPAWNS (3 agents per team with per-agent strategy assignment)

    Behavior: AGENT_GUN_ROTATION_SPEED, DETECTION_INTERVAL

client/config.py - Client Settings

    Visual settings: Colors for teams, walls, grid, entities

    Rendering layers: TEAM_RENDER_ORDERS (prevents FOV flickering)

    Asset paths: Background image file, wall configuration file

Game Mechanics
Agent Systems

Movement:

    8-directional movement at configurable speed

    Collision detection with walls and other agents

    Blocking status available to strategies

Vision (FOV):

    Cone-shaped field of view defined by angle and opening

    Ray casting detects visible enemies (opposite team only)

    Automatic detection every DETECTION_INTERVAL frames

    Accessible via agent.detected_enemies set

Weapon:

    Point gun at target with smooth rotation

    Cooldown-based firing (load_bullet() triggers automatic shooting)

    Bullets spawn at gun muzzle with team/damage metadata

Health:

    Agents take damage on bullet collision

    Death occurs at 0 health

    Dead agents removed from game state

Network Protocol

Message Types:

    MSG_TYPE_ENTITIES (0x02) - Agent positions, health, gun angles

    MSG_TYPE_BULLETS (0x04) - Projectile positions, velocities

    MSG_TYPE_WALLS (0x03) - Wall changes (for future use)

Synchronization:

    Server broadcasts at BROADCAST_RATE Hz

    Client receives updates asynchronously

    Rendering interpolates between frames

Strategies

Custom AI strategies drive agent behavior. For detailed documentation on building strategies, see STRATEGY_GUIDE.md in the root directory.

Currently available strategies:

    RandomStrategy - Move randomly, attack detected enemies

    HuntStrategy - Actively pursue closest visible enemy

    DefensiveStrategy - Remain near spawn position, defend territory

To assign strategies to agents, modify TEAM_A_SPAWNS and TEAM_B_SPAWNS in server/config.py:

python
TEAM_A_SPAWNS = [
    (160.0, 120.0, "hunt"),
    (160.0, 360.0, "random"),
    (160.0, 600.0, "defensive"),
]

TEAM_B_SPAWNS = [
    (1120.0, 120.0, "defensive"),
    (1120.0, 360.0, "hunt"),
    (1120.0, 600.0, "random"),
]

Project Structure

arena-battle/
├── src/
│   ├── client/
│   │   ├── main.py
│   │   ├── config.py
│   │   ├── assets/
│   │   │   └── background.png
│   │   ├── display/
│   │   │   ├── batch_object.py
│   │   │   ├── display_background.py
│   │   │   ├── display_bullet.py
│   │   │   ├── display_entity.py
│   │   │   └── display_walls.py
│   │   ├── network/
│   │   │   └── client_network.py
│   │   └── scenes/
│   │       ├── scene.py
│   │       ├── scene_gameplay.py
│   │       ├── scene_manager.py
│   │       └── logical_window.py
│   ├── common/
│   │   ├── config.py
│   │   ├── states/
│   │   │   ├── state_entity.py
│   │   │   ├── state_bullet.py
│   │   │   └── state_walls.py
│   │   └── wall_configs/
│   │       └── walls_config1.txt
│   └── server/
│       ├── main.py
│       ├── config.py
│       ├── gameplay/
│       │   ├── game_manager.py
│       │   ├── agent.py
│       │   ├── bullet.py
│       │   └── collision.py
│       ├── network/
│       │   └── network_manager.py
│       └── strategy/
│           ├── base.py
│           └── random_strategy.py
├── tutorials/
│   └── STRATEGY_GUIDE.md
├── README.md
├── setup.sh
├── requirements.txt
├── setup.py
└── .gitignore


Each team renders at different depths to prevent FOV flickering:

    Team A: FOV (layer 2), Body (3), Gun (4)

    Team B: FOV (layer 3), Body (4), Gun (5)

FOV Visualization

    Semi-transparent polygon showing agent vision cone

    Ray casting determines polygon edges (walls block vision)

    Color matches team color for clarity

Performance Considerations

    Collision detection: Currently O(n²), checked twice per frame (inefficient)

    Ray casting: Configurable ray count via FOV_NUM_RAYS in common/config.py

    Network updates: Separate from simulation rate (configurable via BROADCAST_RATE)

    Agent count: Tested with 6 agents; scale appropriately

Future Improvements

    ✓ Optimize collision detection (single pass, spatial partitioning)

    ✓ Optimize other aspects of the game, this is very raw state

    ✓ Add more strategy types (tactical, pathfinding, formation)

    ✓ Implement a separate scene at start of game for choosing agents atributes based on score

    ✓ Add game events (captures, kills, objectives) or game modes (battle royale)

    ✓ Persistent game statistics and replays

