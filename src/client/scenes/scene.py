# External libraries
from pyglet.graphics import Batch

# Internal libraries
from client.display.batch_object import BatchObject


class Scene:
    """
    Represents a scene in the application, managing visual elements and
    interactions. It uses a Batch for efficient drawing of graphical
    objects, reducing draw calls.

    Events are handled at the LogicalWindow level, this class has helpers
    that will probably be overwritten by each individual scene.

    Scenes work entirely in logical coordinate space and have no direct
    window dependency
    """

    def __init__(self):
        """ Constructor """
        self.batch = Batch()
        self.batch_objects: list[BatchObject] = []
        self.objects_to_remove: list[BatchObject] = []

    def add_to_batch(self, batch_object: BatchObject):
        """
        Register a batch object for automatic cleanup.

        Args:
            batch_object: The object to track

        Returns:
            The batch object (for chaining)
        """
        self.batch_objects.append(batch_object)
        return batch_object

    def remove_from_batch(self, batch_object: BatchObject):
        """
        Mark a batch object for removal.
        Actual removal happens at end of update cycle.

        Args:
            batch_object: The object to remove
        """
        self.objects_to_remove.append(batch_object)

    def cleanup_removed_objects(self):
        """
        Process deferred object removals.
        !!!!! Must be called at end of helper_update() in subclasses.
        """
        if not self.objects_to_remove:
            return

        # Convert to set for O(1) lookup
        to_remove_set = set(self.objects_to_remove)

        # Filter out removed objects using list comprehension
        self.batch_objects = [
            obj for obj in self.batch_objects
            if obj not in to_remove_set
        ]

        # Delete the objects
        for obj in self.objects_to_remove:
            if hasattr(obj, 'delete'):
                obj.delete()

        self.objects_to_remove.clear()

    # ~ virtual
    def helper_enter(self):
        """ Helper for when entering the scene.
        Must be implemented by subclasses. """
        raise NotImplementedError(
            f"{self.__class__.__name__} must implement helper_enter()"
        )

    # ~ virtual
    def helper_update(self, dt):
        """
        Helper for handling scene update.
        Must be implemented by subclasses.

        !!!!! Note: Subclasses should call self.cleanup_removed_objects()
        at the end of their update method.
        """
        raise NotImplementedError(
            f"{self.__class__.__name__} must implement helper_update(dt)"
        )

    # ~ virtual
    def helper_mouse_press(self, logical_x, logical_y, button, modifiers):
        """ Event mouse click (already in logical coordinates).
        Must be implemented by subclasses. """
        raise NotImplementedError(
            f"{self.__class__.__name__} must implement helper_mouse_press(...)"
        )

    def helper_leave(self):
        """
        Helper for when leaving this scene - cleans up all batch objects.
        Subclasses should call super().helper_leave() at the end of
        their helper_leave method if they override this one.
        """
        for obj in self.batch_objects:
            if hasattr(obj, 'delete'):
                obj.delete()

        self.batch_objects.clear()
        self.objects_to_remove.clear()
