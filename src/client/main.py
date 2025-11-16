# External libraries
from pyglet.app import run

# Internal libraries
from client.network.client_network import ClientNetwork
from client.scenes.logical_window import LogicalWindow
from client.scenes.scene_gameplay import SceneGameplay
from client.scenes.scene_gameplay_koth import SceneGameplayKOTH
from client.scenes.scene_menu import SceneMenu
from common.config import WALL_CONFIG
from common.logger import setup_logging, get_logger

# Initialize logging for the client
setup_logging("arena-client")
logger = get_logger(__name__)

# Global references
window_instance = None
network_instance = None


def main() -> None:
    """
    Initialize and run the game client.
    
    Client connects to unified server and waits for mode selection.
    """
    global window_instance, network_instance
    
    # Create window
    window = LogicalWindow()
    window_instance = window
    
    # Create scenes for both modes
    scene_gameplay = SceneGameplay(WALL_CONFIG)
    scene_gameplay_koth = SceneGameplayKOTH(WALL_CONFIG)
    scene_menu = SceneMenu()
    
    # Register all scenes
    window.scene_manager.add_scene("menu", scene_menu)
    window.scene_manager.add_scene("gameplay", scene_gameplay)
    window.scene_manager.add_scene("gameplay_koth", scene_gameplay_koth)
    
    # Start in menu
    try:
        window.scene_manager.switch_to("menu")
    except ValueError:
        return
    
    # Start unified network client
    # For now, use gameplay scene (server will handle mode switching)
    network = ClientNetwork(scene_gameplay)
    network_instance = network
    network.start()
    
    # Run application
    try:
        logger.info("Starting client application")
        run()
    finally:
        network.stop()


if __name__ == "__main__":
    main()