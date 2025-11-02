"""
Game server entry point.
Initializes world state and starts network/game managers.
"""

from server.gameplay.game_manager import GameManager
from server.network.network_manager import NetworkManager
from common.states.state_walls import StateWalls
from common.config import (
    WALL_CONFIG,
    LOGICAL_SCREEN_WIDTH,
    LOGICAL_SCREEN_HEIGHT,
    GRID_UNIT
)


def main():
    """
    Initialize and start game server.
    
    Flow:
    1. Load wall configuration from file
    2. Create GameManager (simulation logic)
    3. Create NetworkManager (WebSocket server)
    4. Run network loop (blocking)
    """
    print("[SERVER] Initializing...")
    
    # Create shared world state (walls)
    walls = StateWalls(
        grid_unit=GRID_UNIT,
        world_width=LOGICAL_SCREEN_WIDTH,
        world_height=LOGICAL_SCREEN_HEIGHT
    )
    walls.load_from_file(WALL_CONFIG)
    
    # Create game and network managers
    game_mgr = GameManager(walls)
    net_mgr = NetworkManager(game_mgr)
    
    # Start server (blocking call)
    net_mgr.run()


if __name__ == "__main__":
    main()
