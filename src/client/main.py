# External libraries
from pyglet.app import run


# Internal libraries
from client.network.client_network import ClientNetwork
from client.scenes.logical_window import LogicalWindow
from client.scenes.scene_gameplay import SceneGameplay
from common.config import WALL_CONFIG


def main() -> None:
    """
    Initialize and run the game client.

    Sets up the window, scene, and network connection, then starts
    the pyglet application loop. Ensures network cleanup on exit.
    """
    # Create window and scene
    window = LogicalWindow()
    scene_gameplay = SceneGameplay(WALL_CONFIG)

    # Register and switch to gameplay scene
    window.scene_manager.add_scene("gameplay", scene_gameplay)
    try:
        window.scene_manager.switch_to("gameplay")
    except ValueError:
        return

    # Start network client in background thread
    network = ClientNetwork(scene_gameplay)
    network.start()

    # Run application and ensure cleanup
    try:
        run()
    finally:
        network.stop()


if __name__ == "__main__":
    main()
