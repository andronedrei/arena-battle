# Internal libraries
from common.config import WALL_CONFIG
from server.network.network_manager import NetworkManagerUnified
from common.logger import setup_logging, get_logger

# Initialize logging early for the server
setup_logging("arena-server")
logger = get_logger(__name__)


def main() -> None:
    """
    Initialize and start unified game server.
    
    Server waits for clients to select game mode from menu,
    then initializes the appropriate game manager (Survival or KOTH).

    Flow:
    1. Create NetworkManagerUnified (handles both modes)
    2. Wait for first client to select mode
    3. Initialize appropriate GameManager
    4. Run network loop (blocking)
    """
    logger.info("Starting unified server (Survival + KOTH)")
    net_mgr = NetworkManagerUnified(WALL_CONFIG)
    net_mgr.run()


if __name__ == "__main__":
    main()