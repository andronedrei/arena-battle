# Internal libraries
from common.config import WALL_CONFIG
from server.gameplay.game_manager import GameManager
from server.network.network_manager import NetworkManager


def main() -> None:
    """
    Initialize and start game server.

    Flow:
    1. Create GameManager (initializes world state internally)
    2. Create NetworkManager (initializes WebSocket server)
    3. Run network loop (blocking)
    """
    game_mgr = GameManager(WALL_CONFIG)
    net_mgr = NetworkManager(game_mgr)
    net_mgr.run()


if __name__ == "__main__":
    main()
