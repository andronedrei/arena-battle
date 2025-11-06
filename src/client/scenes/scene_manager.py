# Internal libraries
from client.scenes.scene import Scene


class SceneManager:
    """
    Manages scene switching and lifecycle for the application.

    Each scene is identified by a unique name and stored in a dictionary.
    Handles transitions between scenes, including proper cleanup of the
    previous scene and initialization of the new one. Includes rollback
    on initialization failure to maintain consistency.
    """

    def __init__(self) -> None:
        """Initialize the scene manager with no active scene."""
        self.scenes: dict[str, Scene] = {}
        self.cur_scene_instance: Scene | None = None

    # Scene management

    def add_scene(self, scene_name: str, scene_instance: Scene) -> None:
        """
        Register a scene for management.

        Args:
            scene_name: Unique identifier for the scene.
            scene_instance: The Scene object to manage.
        """
        self.scenes[scene_name] = scene_instance

    def switch_to(self, scene_name: str) -> None:
        """
        Transition to a registered scene.

        Leaves the current scene before entering the new one. If the new
        scene initialization fails, both scenes are cleaned up and the
        manager state is reset to ensure consistency.

        Args:
            scene_name: Name of the scene to switch to.

        Raises:
            ValueError: If the scene name is not registered.
        """
        if scene_name not in self.scenes:
            raise ValueError(f"Scene '{scene_name}' not found")

        new_scene = self.scenes[scene_name]

        # Leave current scene if any
        if self.cur_scene_instance:
            self.cur_scene_instance.helper_leave()

        # Enter new scene with rollback on failure
        try:
            self.cur_scene_instance = new_scene
            self.cur_scene_instance.helper_enter()
        except Exception:
            try:
                new_scene.helper_leave()
            finally:
                self.cur_scene_instance = None
            raise

    def delete_scene(self, scene_name: str) -> None:
        """
        Remove a scene and clean up its resources.

        If the scene is currently active, it is left before deletion.

        Args:
            scene_name: Name of the scene to delete.

        Raises:
            ValueError: If the scene name is not registered.
        """
        if scene_name not in self.scenes:
            raise ValueError(f"Scene '{scene_name}' not found")

        scene = self.scenes[scene_name]

        # Clean up if currently active
        if self.cur_scene_instance is scene:
            scene.helper_leave()
            self.cur_scene_instance = None

        del self.scenes[scene_name]
