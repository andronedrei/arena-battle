# External libraries
from pyglet.graphics import Batch


class BatchObject:
    """
    Base class for objects that render into a pyglet Batch.

    Automatically tracks and manages cleanup of sub-objects (shapes,
    sprites, labels) to prevent resource leaks.
    """

    def __init__(self, batch: Batch) -> None:
        """
        Initialize the batch object.

        Args:
            batch: Pyglet Batch to render into.
        """
        self.batch = batch
        self.sub_objects: list = []

    # Sub-object management

    def register_sub_object(self, obj: object) -> object:
        """
        Register a sub-object for automatic cleanup.

        Args:
            obj: A shape, sprite, label, or other batch object.

        Returns:
            The registered object (for chaining).
        """
        self.sub_objects.append(obj)
        return obj

    def unregister_sub_object(self, obj: object) -> None:
        """
        Remove a sub-object from tracking.

        Args:
            obj: The object to stop tracking.
        """
        try:
            self.sub_objects.remove(obj)
        except ValueError:
            # Object not in list (already removed or never registered)
            pass

    # Cleanup

    def delete(self) -> None:
        """
        Clean up all sub-objects.

        Subclasses should call super().delete() at the end of their
        delete method if they override this one.
        """
        for obj in self.sub_objects:
            if hasattr(obj, "delete"):
                obj.delete()
        self.sub_objects.clear()
