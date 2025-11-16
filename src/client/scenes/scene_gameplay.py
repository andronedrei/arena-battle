# External libraries
from collections import deque

# Internal libraries
from client.display.display_background import DisplayBackground
from client.display.display_bullet import DisplayBullet
from client.display.display_entity import DisplayEntity
from client.display.display_walls import DisplayWalls
from client.scenes.scene import Scene
from common.config import (
    GRID_UNIT,
    LOGICAL_SCREEN_HEIGHT,
    LOGICAL_SCREEN_WIDTH,
)
from common.states.state_bullet import StateBullet
from common.states.state_entity import StateEntity
from pyglet.text import Label
from pyglet.graphics import Group


class SceneGameplay(Scene):
    """
    Client-side SURVIVAL gameplay scene.

    Displays game state for survival mode - pure team deathmatch.
    NO KOTH elements (no zone, no scores, just combat).
    """

    def __init__(self, walls_config_file: str) -> None:
        """
        Initialize the survival gameplay scene.

        Args:
            walls_config_file: Path to the walls configuration file.
        """
        super().__init__()
        self.walls_config_file = walls_config_file

        # Display objects
        self.display_bg: DisplayBackground | None = None
        self.display_walls: DisplayWalls | None = None

        # Entity and bullet displays
        self.display_entities: dict[int, DisplayEntity] = {}
        self.display_bullets: dict[int, DisplayBullet] = {}

        # Network update queues (filled by network layer)
        self.pending_entities_queue: deque[bytes] = deque()
        self.pending_walls_queue: deque[bytes] = deque()
        self.pending_bullets_queue: deque[bytes] = deque()
        self.walls_changed: bool = False
        
        # Team counters for display
        self.team_a_count = 0
        self.team_b_count = 0
        self.team_counter_label = None

    # Lifecycle

    def helper_enter(self) -> None:
        """Initialize background, walls, and prepare for entity updates."""
        self.display_bg = self.add_to_batch(
            DisplayBackground(batch=self.batch)
        )

        self.display_walls = self.add_to_batch(
            DisplayWalls(
                batch=self.batch,
                grid_unit=GRID_UNIT,
                world_width=LOGICAL_SCREEN_WIDTH,
                world_height=LOGICAL_SCREEN_HEIGHT,
                walls_config_file=self.walls_config_file,
            )
        )
        
        # Add team counter display
        from client.display.batch_object import BatchObject
        counter_obj = BatchObject(self.batch)
        self.team_counter_label = counter_obj.register_sub_object(
            Label(
                "Team A: 0  |  Team B: 0",
                x=LOGICAL_SCREEN_WIDTH // 2,
                y=LOGICAL_SCREEN_HEIGHT - 30,
                anchor_x="center",
                anchor_y="center",
                font_size=16,
                color=(255, 255, 255, 255),
                batch=self.batch,
                group=Group(order=10),
            )
        )
        self.add_to_batch(counter_obj)

    def helper_update(self, dt: float) -> None:
        """
        Process all pending network updates and refresh display state.

        Updates are processed in order: walls, entities, bullets. FOV is
        refreshed if walls changed to maintain visibility accuracy.

        Args:
            dt: Delta time since last update in seconds.
        """
        # Process wall updates
        while self.pending_walls_queue:
            self.apply_walls_update(self.pending_walls_queue.popleft())
            self.walls_changed = True

        # Process entity updates
        while self.pending_entities_queue:
            self.apply_entities_update(
                self.pending_entities_queue.popleft()
            )

        # Process bullet updates
        while self.pending_bullets_queue:
            self.apply_bullets_update(self.pending_bullets_queue.popleft())

        # Refresh FOV visualization if walls changed
        if self.walls_changed:
            self.refresh_all_entity_fov()
            self.walls_changed = False

        self.cleanup_removed_objects()

    def helper_mouse_press(
        self, logical_x: float, logical_y: float, button: int, modifiers: int
    ) -> None:
        """Handle mouse input (placeholder for future implementation)."""
        pass

    def helper_leave(self) -> None:
        """Clean up all display objects and queues."""
        super().helper_leave()

        self.display_bg = None
        self.display_walls = None
        self.display_entities.clear()
        self.display_bullets.clear()
        self.pending_entities_queue.clear()
        self.pending_walls_queue.clear()
        self.pending_bullets_queue.clear()

    # Network event handlers

    def on_entities_update(self, packed_data: bytes) -> None:
        """
        Queue entity state update from network layer.

        Args:
            packed_data: Serialized entity state data.
        """
        if packed_data:
            self.pending_entities_queue.append(packed_data)

    def on_walls_update(self, packed_data: bytes) -> None:
        """
        Queue walls state update from network layer.

        Args:
            packed_data: Serialized walls state data.
        """
        if packed_data:
            self.pending_walls_queue.append(packed_data)

    def on_bullets_update(self, packed_data: bytes) -> None:
        """
        Queue bullets state update from network layer.

        Args:
            packed_data: Serialized bullets state data.
        """
        if packed_data:
            self.pending_bullets_queue.append(packed_data)

    # Update application

    def apply_entities_update(self, packed_data: bytes) -> None:
        """
        Create or update display entities from state packet.

        Creates new DisplayEntity objects for entities that don't exist yet,
        updates existing ones, and removes displays for deleted entities.

        Args:
            packed_data: Serialized entity state data.
        """
        from client.config import TEAM_RENDER_ORDERS

        try:
            entities_list = StateEntity.unpack_entities(packed_data)
        except ValueError:
            return

        received_ids = {
            state_entity.id_entity for state_entity in entities_list
        }

        # Update or create displays
        for state_entity in entities_list:
            if state_entity.id_entity not in self.display_entities:
                # Get render order based on team
                group_order = TEAM_RENDER_ORDERS.get(
                    state_entity.team, 2
                )

                display = self.add_to_batch(
                    DisplayEntity(
                        batch=self.batch,
                        entity_state=state_entity,
                        walls_state=self.display_walls.state,
                        group_order=group_order,
                    )
                )
                self.display_entities[state_entity.id_entity] = display
            else:
                self.display_entities[
                    state_entity.id_entity
                ].sync_from_state(state_entity)

        # Remove displays for deleted entities
        removed_ids = set(self.display_entities.keys()) - received_ids
        for entity_id in removed_ids:
            self.display_entities[entity_id].delete()
            del self.display_entities[entity_id]
        
        # Update team counters
        self._update_team_counts(entities_list)

    def apply_bullets_update(self, packed_data: bytes) -> None:
        """
        Create or update display bullets from state packet.

        Creates new DisplayBullet objects for bullets that don't exist yet,
        updates existing ones, and removes displays for deleted bullets.

        Args:
            packed_data: Serialized bullet state data.
        """
        try:
            bullets_list = StateBullet.unpack_bullets(packed_data)
        except ValueError:
            return

        received_ids = {
            state_bullet.id_bullet for state_bullet in bullets_list
        }

        # Update or create displays
        for state_bullet in bullets_list:
            if state_bullet.id_bullet not in self.display_bullets:
                display = self.add_to_batch(
                    DisplayBullet(
                        batch=self.batch,
                        bullet_state=state_bullet,
                        group_order=2,
                    )
                )
                self.display_bullets[state_bullet.id_bullet] = display
            else:
                self.display_bullets[
                    state_bullet.id_bullet
                ].sync_from_state(state_bullet)

        # Remove displays for deleted bullets
        removed_ids = set(self.display_bullets.keys()) - received_ids
        for bullet_id in removed_ids:
            self.display_bullets[bullet_id].delete()
            del self.display_bullets[bullet_id]

    def apply_walls_update(self, packed_data: bytes) -> None:
        """
        Update walls display from state packet.

        Args:
            packed_data: Serialized walls state data.
        """
        try:
            self.display_walls.unpack_changes(packed_data)
        except ValueError:
            return

    def refresh_all_entity_fov(self) -> None:
        """Refresh field-of-view visualization for all entities."""
        for display_entity in self.display_entities.values():
            display_entity.update_fov_polygon()
    
    def _update_team_counts(self, entities_list) -> None:
        """Update team alive counters."""
        from common.states.state_entity import Team
        
        team_a = sum(1 for e in entities_list if e.team == Team.TEAM_A)
        team_b = sum(1 for e in entities_list if e.team == Team.TEAM_B)
        
        self.team_a_count = team_a
        self.team_b_count = team_b
        
        if self.team_counter_label:
            self.team_counter_label.text = f"Team A: {team_a}  |  Team B: {team_b}"
            
            # Check for winner
            if team_a == 0 and team_b > 0:
                self.team_counter_label.text = "TEAM B WINS!"
                self.team_counter_label.color = (255, 100, 100, 255)
            elif team_b == 0 and team_a > 0:
                self.team_counter_label.text = "TEAM A WINS!"
                self.team_counter_label.color = (100, 200, 255, 255)