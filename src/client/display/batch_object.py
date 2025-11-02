from pyglet.graphics import Batch


class BatchObject:
    """
    Base class for all objects that render into a pyglet Batch.
    Automatically tracks sub-elements for cleanup.
    """

    def __init__(self, batch: Batch):
        self.batch = batch
        self.sub_objects = []  # track child batch objects

    def register_sub_object(self, obj):
        """ Register a sub-object (shape, sprite, label)
        for automatic cleanup. """
        self.sub_objects.append(obj)
        return obj

    def unregister_sub_object(self, obj):
        """ Remove a sub-object from tracking (e.g., when replacing it). """
        try:
            self.sub_objects.remove(obj)
        except ValueError:
            pass  # Already removed or never registered

    def delete(self):
        """
        Cleanup all sub-objects from the batch.
        Subclasses should call super().delete() at the end of their
        delete method if they override this one.
        """
        for obj in self.sub_objects:
            if hasattr(obj, 'delete'):
                obj.delete()
        self.sub_objects.clear()
