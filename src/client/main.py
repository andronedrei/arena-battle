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
    
    # Create a wrapper that routes to the active scene
    class SceneRouter:
        """Routes network updates to the currently active scene."""
        def __init__(self, window_manager):
            self.window = window_manager
        
        def on_entities_update(self, data):
            if self.window.scene_manager.cur_scene_instance:
                self.window.scene_manager.cur_scene_instance.on_entities_update(data)
        
        def on_walls_update(self, data):
            if self.window.scene_manager.cur_scene_instance:
                self.window.scene_manager.cur_scene_instance.on_walls_update(data)
        
        def on_bullets_update(self, data):
            if self.window.scene_manager.cur_scene_instance:
                self.window.scene_manager.cur_scene_instance.on_bullets_update(data)
        
        def on_koth_update(self, data):
            if self.window.scene_manager.cur_scene_instance:
                if hasattr(self.window.scene_manager.cur_scene_instance, 'on_koth_update'):
                    self.window.scene_manager.cur_scene_instance.on_koth_update(data)
    
    # Start unified network client with router
    scene_router = SceneRouter(window)
    network = ClientNetwork(scene_router)
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