# External libraries
from pyglet.graphics import Batch


# Internal libraries
from client.display.batch_object import BatchObject


class Scene:
    """
    Represents a scene in the application, managing visual elements and
    interactions. It uses a Batch for efficient drawing of graphical
    objects, reducing draw calls.

    Events are handled at the LogicalWindow level. This class provides
    helper methods that subclasses override to implement scene-specific
    behavior. Scenes work entirely in logical coordinate space with no
    direct window dependency.
    """

    def __init__(self):
        """Initialize an empty scene with batch management."""
        self.batch = Batch()
        self.batch_objects: list[BatchObject] = []
        self.objects_to_remove: list[BatchObject] = []

    # Batch management

    def add_to_batch(self, batch_object: BatchObject) -> BatchObject:
        """
        Register a batch object for automatic cleanup and tracking.

        Args:
            batch_object: The object to track.

        Returns:
            The batch object (for chaining).
        """
        self.batch_objects.append(batch_object)
        return batch_object

    def remove_from_batch(self, batch_object: BatchObject) -> None:
        """
        Mark a batch object for deferred removal.

        Actual removal occurs at the end of the update cycle to avoid
        modifying the batch during iteration.

        Args:
            batch_object: The object to remove.
        """
        self.objects_to_remove.append(batch_object)

    # Internal cleanup

    def cleanup_removed_objects(self) -> None:
        """
        Process deferred object removals and cleanup.

        Must be called at the end of helper_update() in subclasses.
        """
        if not self.objects_to_remove:
            return

        # Convert to set for O(1) lookup during filtering
        to_remove_set = set(self.objects_to_remove)

        # Filter out removed objects
        self.batch_objects = [
            obj for obj in self.batch_objects
            if obj not in to_remove_set
        ]

        # Clean up removed objects
        for obj in self.objects_to_remove:
            if hasattr(obj, 'delete'):
                obj.delete()

        self.objects_to_remove.clear()

    def helper_leave(self) -> None:
        """
        Clean up all batch objects when leaving the scene.

        Subclasses should call super().helper_leave() at the end of
        their override if they need additional cleanup.
        """
        for obj in self.batch_objects:
            if hasattr(obj, 'delete'):
                obj.delete()

        self.batch_objects.clear()
        self.objects_to_remove.clear()

    # Virtual methods (must be implemented by subclasses)

    def helper_enter(self) -> None:
        """
        Called when entering this scene.

        Subclasses must implement this method.
        """
        raise NotImplementedError(
            f"{self.__class__.__name__} must implement helper_enter()"
        )

    def helper_update(self, dt: float) -> None:
        """
        Called each frame to update scene state.

        Subclasses must implement this method and call
        self.cleanup_removed_objects() at the end.

        Args:
            dt: Delta time since last update in seconds.
        """
        raise NotImplementedError(
            f"{self.__class__.__name__} must implement helper_update(dt)"
        )

    def helper_mouse_press(
        self, logical_x: float, logical_y: float, button: int, modifiers: int
    ) -> None:
        """
        Called when mouse is clicked.

        Coordinates are already converted to logical space.

        Args:
            logical_x: X coordinate in logical space.
            logical_y: Y coordinate in logical space.
            button: Mouse button identifier.
            modifiers: Keyboard modifier flags.
        """
        raise NotImplementedError(
            f"{self.__class__.__name__} must implement helper_mouse_press(...)"
        )
