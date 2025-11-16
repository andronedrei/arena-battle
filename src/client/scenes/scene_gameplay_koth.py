"""
KOTH gameplay scene - client-side.

Extends base gameplay scene with KOTH-specific visuals and state handling.
"""

from collections import deque

from client.display.display_background import DisplayBackground
from client.display.display_bullet import DisplayBullet
from client.display.display_entity import DisplayEntity
from client.display.display_walls import DisplayWalls
from client.scenes.scene import Scene
from common.config import GRID_UNIT, LOGICAL_SCREEN_HEIGHT, LOGICAL_SCREEN_WIDTH
from common.states.state_bullet import StateBullet
from common.states.state_entity import StateEntity

from client.display.display_koth_zone import DisplayKOTHZone
from client.display.display_koth_hud import DisplayKOTHHUD
from common.states.state_koth import StateKOTH


class SceneGameplayKOTH(Scene):
    """
    Client-side KOTH gameplay scene.
    
    Displays KOTH game state with zone visualization and scoreboard.
    """
    
    def __init__(self, walls_config_file: str) -> None:
        """
        Initialize KOTH gameplay scene.
        
        Args:
            walls_config_file: Path to walls configuration file.
        """
        super().__init__()
        self.walls_config_file = walls_config_file
        
        # Display objects
        self.display_bg: DisplayBackground | None = None
        self.display_walls: DisplayWalls | None = None
        self.display_koth_zone: DisplayKOTHZone | None = None
        self.display_koth_hud: DisplayKOTHHUD | None = None
        
        # Entity and bullet displays
        self.display_entities: dict[int, DisplayEntity] = {}
        self.display_bullets: dict[int, DisplayBullet] = {}
        
        # Network update queues
        self.pending_entities_queue: deque[bytes] = deque()
        self.pending_walls_queue: deque[bytes] = deque()
        self.pending_bullets_queue: deque[bytes] = deque()
        self.pending_koth_queue: deque[bytes] = deque()
        self.walls_changed: bool = False
    
    # Lifecycle
    
    def helper_enter(self) -> None:
        """Initialize all visual components."""
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
                walls_config_file=self.walls_config_file,
            )
        )
        
        # KOTH zone (rendered below entities but above background)
        self.display_koth_zone = self.add_to_batch(
            DisplayKOTHZone(
                batch=self.batch,
                group_order=1,
            )
        )
        
        # KOTH HUD (rendered on top of everything)
        self.display_koth_hud = self.add_to_batch(
            DisplayKOTHHUD(
                batch=self.batch,
                group_order=10,
            )
        )
    
    def helper_update(self, dt: float) -> None:
        """
        Process network updates and refresh display.
        
        Args:
            dt: Delta time since last update.
        """
        # Process wall updates
        while self.pending_walls_queue:
            self.apply_walls_update(self.pending_walls_queue.popleft())
            self.walls_changed = True
        
        # Process entity updates
        while self.pending_entities_queue:
            self.apply_entities_update(self.pending_entities_queue.popleft())
        
        # Process bullet updates
        while self.pending_bullets_queue:
            self.apply_bullets_update(self.pending_bullets_queue.popleft())
        
        # Process KOTH state updates
        while self.pending_koth_queue:
            self.apply_koth_update(self.pending_koth_queue.popleft())
        
        # Refresh FOV if walls changed
        if self.walls_changed:
            self.refresh_all_entity_fov()
            self.walls_changed = False
        
        self.cleanup_removed_objects()
    
    def helper_mouse_press(
        self, logical_x: float, logical_y: float, button: int, modifiers: int
    ) -> None:
        """Handle mouse input."""
        pass
    
    def helper_leave(self) -> None:
        """Clean up all resources."""
        super().helper_leave()
        
        self.display_bg = None
        self.display_walls = None
        self.display_koth_zone = None
        self.display_koth_hud = None
        self.display_entities.clear()
        self.display_bullets.clear()
        self.pending_entities_queue.clear()
        self.pending_walls_queue.clear()
        self.pending_bullets_queue.clear()
        self.pending_koth_queue.clear()
    
    # Network event handlers
    
    def on_entities_update(self, packed_data: bytes) -> None:
        """Queue entity state update."""
        if packed_data:
            self.pending_entities_queue.append(packed_data)
    
    def on_walls_update(self, packed_data: bytes) -> None:
        """Queue walls state update."""
        if packed_data:
            self.pending_walls_queue.append(packed_data)
    
    def on_bullets_update(self, packed_data: bytes) -> None:
        """Queue bullets state update."""
        if packed_data:
            self.pending_bullets_queue.append(packed_data)
    
    def on_koth_update(self, packed_data: bytes) -> None:
        """Queue KOTH state update."""
        if packed_data:
            self.pending_koth_queue.append(packed_data)
    
    # Update application
    
    def apply_entities_update(self, packed_data: bytes) -> None:
        """Create or update entity displays from state packet."""
        from client.config import TEAM_RENDER_ORDERS
        
        try:
            entities_list = StateEntity.unpack_entities(packed_data)
        except ValueError:
            return
        
        received_ids = {e.id_entity for e in entities_list}
        
        # Update or create displays
        for state_entity in entities_list:
            if state_entity.id_entity not in self.display_entities:
                group_order = TEAM_RENDER_ORDERS.get(state_entity.team, 2)
                
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
                self.display_entities[state_entity.id_entity].sync_from_state(
                    state_entity
                )
        
        # Remove deleted entities
        removed_ids = set(self.display_entities.keys()) - received_ids
        for entity_id in removed_ids:
            self.display_entities[entity_id].delete()
            del self.display_entities[entity_id]
    
    def apply_bullets_update(self, packed_data: bytes) -> None:
        """Create or update bullet displays from state packet."""
        try:
            bullets_list = StateBullet.unpack_bullets(packed_data)
        except ValueError:
            return
        
        received_ids = {b.id_bullet for b in bullets_list}
        
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
                self.display_bullets[state_bullet.id_bullet].sync_from_state(
                    state_bullet
                )
        
        # Remove deleted bullets
        removed_ids = set(self.display_bullets.keys()) - received_ids
        for bullet_id in removed_ids:
            self.display_bullets[bullet_id].delete()
            del self.display_bullets[bullet_id]
    
    def apply_walls_update(self, packed_data: bytes) -> None:
        """Update walls display from state packet."""
        try:
            self.display_walls.unpack_changes(packed_data)
        except ValueError:
            return
    
    def apply_koth_update(self, packed_data: bytes) -> None:
        """
        Update KOTH state from network packet.
        
        Updates zone visualization and HUD with current game state.
        
        Args:
            packed_data: Serialized KOTH state from server.
        """
        try:
            koth_state = StateKOTH.unpack(packed_data)
        except ValueError as e:
            # Invalid packet - log and skip
            from common.logger import get_logger
            logger = get_logger(__name__)
            logger.warning(f"Failed to unpack KOTH state: {e}")
            return
        
        # Update zone visualization
        if self.display_koth_zone:
            self.display_koth_zone.update_status(koth_state.zone_status)
        
        # Update HUD
        if self.display_koth_hud:
            self.display_koth_hud.update_from_state(koth_state)
    
    def refresh_all_entity_fov(self) -> None:
        """Refresh FOV visualization for all entities."""
        for display_entity in self.display_entities.values():
            display_entity.update_fov_polygon()