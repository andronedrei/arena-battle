# Internal libraries
from client.scenes.scene import Scene


class SceneManager():
    """
    A class responsible for switching between different scenes,
    each one with its own batch

    Each scene is stored in a dict and can be identified with a name
    """

    def __init__(self):
        self.scenes: dict[str, Scene] = {}  # dict to access scenes by name
        self.cur_scene_instance: Scene = None

    def add_scene(self, scene_name, scene_instance):
        """ Add a scene to be managed """
        self.scenes[scene_name] = scene_instance

    def switch_to(self, scene_name):
        """ Switch to a registered scene """
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
            # Ensure partial resources are cleaned
            try:
                new_scene.helper_leave()
            finally:
                self.cur_scene_instance = None
            raise

    def delete_scene(self, scene_name):
        """ Remove a scene from the manager and cleanup its resources """
        if scene_name not in self.scenes:
            raise ValueError(f"Scene '{scene_name}' not found")

        scene = self.scenes[scene_name]

        # If deleting the current scene, leave it first
        if self.cur_scene_instance is scene:
            scene.helper_leave()
            self.cur_scene_instance = None

        # Remove from dictionary
        del self.scenes[scene_name]
