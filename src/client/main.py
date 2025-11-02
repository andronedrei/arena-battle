from pyglet.app import run
from client.scenes.logical_window import LogicalWindow
from client.scenes.scene_gameplay import SceneGameplay
from client.network.client_network import ClientNetwork

from common.config import WALL_CONFIG


def main():
    # Create window
    my_window = LogicalWindow()

    # Create the scene
    scene_gameplay = SceneGameplay(WALL_CONFIG)

    # Add scene to window
    my_window.scene_manager.add_scene("gameplay", scene_gameplay)
    
    try:
        my_window.scene_manager.switch_to("gameplay")
    except ValueError as e:
        print(f"Error: {e}")

    # Start network client (background thread)
    network = ClientNetwork(scene_gameplay, uri="ws://localhost:8765/ws")
    network.start()

    # Run app
    try:
        run()
    finally:
        network.stop()



if __name__ == "__main__":
    main()

