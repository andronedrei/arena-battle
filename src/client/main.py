# External libraries
from pyglet.app import run


# Internal libraries
from client.network.client_network import ClientNetwork
from client.scenes.logical_window import LogicalWindow
from client.scenes.scene_gameplay import SceneGameplay
from client.scenes.scene_menu import SceneMenu
from common.config import WALL_CONFIG
from common.logger import setup_logging, get_logger

# Initialize logging for the client
setup_logging("arena-client")
logger = get_logger(__name__)

# Global window reference used by the menu to switch scenes
window_instance = None
network_instance = None


def main() -> None:
    """
    Initialize and run the game client.

    Sets up the window, scene, and network connection, then starts
    the pyglet application loop. Ensures network cleanup on exit.
    """
    # Create window and scenes
    global window_instance
    window = LogicalWindow()
    window_instance = window

    scene_gameplay = SceneGameplay(WALL_CONFIG)
    scene_menu = SceneMenu()

    # Register scenes
    window.scene_manager.add_scene("menu", scene_menu)
    window.scene_manager.add_scene("gameplay", scene_gameplay)

    # Start in menu
    try:
        window.scene_manager.switch_to("menu")
    except ValueError:
        return

    # Start network client in background thread (client uses gameplay scene callbacks)
    global network_instance
    network = ClientNetwork(scene_gameplay)
    network_instance = network
    network.start()

    # Run application and ensure cleanup
    try:
        logger.info("Starting client application")
        run()
    finally:
        network.stop()


if __name__ == "__main__":
    main()
