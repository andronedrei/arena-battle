# gameplay_scene.py
from client.scenes.scene import Scene
from client.display.display_background import DisplayBackground
from client.display.display_walls import DisplayWalls
from client.display.display_entity import DisplayEntity
from common.states.state_entity import StateEntity
from common.states.state_walls import StateWalls
from common.config import GRID_UNIT
from common.config import LOGICAL_SCREEN_WIDTH, LOGICAL_SCREEN_HEIGHT
from collections import deque



class SceneGameplay(Scene):
    """
    Client-side gameplay scene.
    Displays game state received from server.
    """

    def __init__(self, walls_config_file):
        super().__init__()
        self.display_bg = None
        self.display_walls: DisplayWalls = None
        self.walls_config_file = walls_config_file

        # Display entities dict
        self.display_entities: dict[int, DisplayEntity] = {}

        # Network update queues (filled by network handlers)
        self.pending_entities_queue: deque[bytes] = deque()
        self.pending_walls_queue: deque[bytes] = deque()
        self.walls_changed: bool = False

    def helper_enter(self):
        """Create background, walls, and initial entities."""
        # Background
        self.display_bg = self.add_to_batch(
            DisplayBackground(batch=self.batch)
        )

        # Walls
        self.display_walls = self.add_to_batch(
            DisplayWalls(
                batch=self.batch,
                grid_unit=GRID_UNIT,
                world_width=LOGICAL_SCREEN_WIDTH,
                world_height=LOGICAL_SCREEN_HEIGHT,
                walls_config_file=self.walls_config_file
            )
        )

    # ~ override
    def helper_update(self, dt):
        """Main update loop - apply all pending network updates."""
        
        # Apply all pending wall updates
        while self.pending_walls_queue:
            packed_data = self.pending_walls_queue.popleft()
            self.apply_walls_update(packed_data)
            self.walls_changed = True

        # Apply all pending entity updates
        while self.pending_entities_queue:
            packed_data = self.pending_entities_queue.popleft()
            self.apply_entities_update(packed_data)

        # Refresh FOV if walls changed this frame
        if self.walls_changed:
            self.refresh_all_entity_fov()
            self.walls_changed = False

        # Clean up removed objects
        self.cleanup_removed_objects()

    # ~ override
    def helper_mouse_press(self, logical_x, logical_y, button, modifiers):
        """Set movement direction based on click quadrant (8 directions)."""
        pass

    # ~ override
    def helper_leave(self):
        """Cleanup all batch objects automatically."""
        super().helper_leave()

        # Reset references
        self.display_bg = None
        self.display_walls = None
        self.walls_state = None
        self.display_entities.clear()
        self.pending_entities_queue.clear()
        self.pending_walls_queue.clear()

    # === NETWORK EVENT HANDLERS (called from network thread/callback) ===

    def on_entities_update(self, packed_data: bytes):
        """
        Store entity update data for processing in next update() cycle.
        Called by network layer.
        """
        if packed_data:
            self.pending_entities_queue.append(packed_data)

    def on_walls_update(self, packed_data: bytes):
        """
        Store wall update data for processing in next update() cycle.
        Called by network layer.
        """
        if packed_data:
            self.pending_walls_queue.append(packed_data)

    # === UPDATE APPLICATION METHODS (called from helper_update) ===

    def apply_entities_update(self, packed_data: bytes):
        """Apply buffered entity updates to display objects."""
        try:
            entities_list = StateEntity.unpack_entities(packed_data)
        except ValueError as e:
            print(f"Invalid entity packet: {e}")
            return

        # Track which IDs we received
        received_ids = set()

        # Update displays
        for state_entity in entities_list:
            received_ids.add(state_entity.id_entity)

            if state_entity.id_entity not in self.display_entities:
                # Create new display entity
                display = self.add_to_batch(
                    DisplayEntity(
                        batch=self.batch,
                        entity_state=state_entity,
                        walls_state=self.display_walls.state,
                        group_order=3
                    )
                )
                self.display_entities[state_entity.id_entity] = display
            else:
                # Update existing display
                self.display_entities[state_entity.id_entity].sync_from_state(state_entity)

        # Remove displays for entities that no longer exist
        removed_ids = set(self.display_entities.keys()) - received_ids
        for entity_id in removed_ids:
            self.display_entities[entity_id].delete()
            del self.display_entities[entity_id]

    def apply_walls_update(self, packed_data: bytes):
        """Apply buffered wall updates to state and display."""
        try:
            # Apply changes to walls_state
            added_cells, removed_cells = self.walls_state.unpack_changes(packed_data)
  
            # Update display
            self.display_walls.unpack_changes(packed_data)

        except ValueError as e:
            print(f"Invalid wall packet: {e}")
            return

    def refresh_all_entity_fov(self):
        """Refresh FOV visualization for all entities (call when walls change)."""
        for display_entity in self.display_entities.values():
            display_entity.update_fov_polygon()
