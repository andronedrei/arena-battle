"""
CTF gameplay scene - client-side.

Extends base gameplay scene with CTF-specific visuals and state handling.
"""

from collections import deque
import json

from client.display.display_background import DisplayBackground
from client.display.display_bullet import DisplayBullet
from client.display.display_entity import DisplayEntity
from client.display.display_walls import DisplayWalls
from client.scenes.scene import Scene
from common.config import GRID_UNIT, LOGICAL_SCREEN_HEIGHT, LOGICAL_SCREEN_WIDTH
from common.states.state_bullet import StateBullet
from common.states.state_entity import StateEntity

from client.display.display_ctf_flag import DisplayCTFFlag
from client.display.display_ctf_hud import DisplayCTFHUD
from common.logger import get_logger
import pyglet

logger = get_logger(__name__)


class SceneGameplayCTF(Scene):
    """
    Client-side CTF gameplay scene.
    
    Displays CTF game state with flag visualization and scoreboard.
    """
    
    def __init__(self, walls_config_file: str) -> None:
        """
        Initialize CTF gameplay scene.
        
        Args:
            walls_config_file: Path to walls configuration file.
        """
        super().__init__()
        self.walls_config_file = walls_config_file
        
        # Display objects
        self.display_bg: DisplayBackground | None = None
        self.display_walls: DisplayWalls | None = None
        self.display_ctf_hud: DisplayCTFHUD | None = None
        
        # Flag displays
        self.display_flag_team_a: DisplayCTFFlag | None = None
        self.display_flag_team_b: DisplayCTFFlag | None = None
        
        # Entity and bullet displays
        self.display_entities: dict[int, DisplayEntity] = {}
        self.display_bullets: dict[int, DisplayBullet] = {}
        
        # Network update queues
        self.pending_entities_queue: deque[bytes] = deque()
        self.pending_walls_queue: deque[bytes] = deque()
        self.pending_bullets_queue: deque[bytes] = deque()
        self.pending_ctf_queue: deque[bytes] = deque()
        self.walls_changed: bool = False
        
        # CTF state
        self.ctf_state: dict = {}
        
        # Win screen labels
        self.win_label: pyglet.text.Label | None = None
        self.win_background: pyglet.shapes.Rectangle | None = None
    
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
        
        # CTF flags (initial positions, will be updated from server)
        # Team A flag (starts on left side)
        self.display_flag_team_a = self.add_to_batch(
            DisplayCTFFlag(
                batch=self.batch,
                team=1,  # Team A
                x=100,
                y=LOGICAL_SCREEN_HEIGHT // 2,
                group_order=3,
            )
        )
        
        # Team B flag (starts on right side)
        self.display_flag_team_b = self.add_to_batch(
            DisplayCTFFlag(
                batch=self.batch,
                team=2,  # Team B
                x=LOGICAL_SCREEN_WIDTH - 100,
                y=LOGICAL_SCREEN_HEIGHT // 2,
                group_order=3,
            )
        )
        
        # CTF HUD (rendered on top of everything)
        self.display_ctf_hud = self.add_to_batch(
            DisplayCTFHUD(
                batch=self.batch,
                group_order=10,
            )
        )
        
        # Win screen (hidden by default, shown on game over)
        # Semi-transparent dark background
        self.win_background = pyglet.shapes.Rectangle(
            x=0,
            y=0,
            width=LOGICAL_SCREEN_WIDTH,
            height=LOGICAL_SCREEN_HEIGHT,
            color=(0, 0, 0),
            batch=self.batch,
        )
        self.win_background.opacity = 180
        self.win_background.visible = False
        
        # Win message label (using HTMLLabel for bold support)
        self.win_label = pyglet.text.Label(
            "",
            font_name="Arial",
            font_size=72,
            x=LOGICAL_SCREEN_WIDTH // 2,
            y=LOGICAL_SCREEN_HEIGHT // 2,
            anchor_x="center",
            anchor_y="center",
            batch=self.batch,
        )
        self.win_label.visible = False
        self.win_label.bold = True  # Set bold after creation
    
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
        
        # Process CTF state updates
        while self.pending_ctf_queue:
            self.apply_ctf_update(self.pending_ctf_queue.popleft())
        
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
        
        # Clean up win screen
        if self.win_label:
            self.win_label.delete()
            self.win_label = None
        if self.win_background:
            self.win_background.delete()
            self.win_background = None
        
        self.display_bg = None
        self.display_walls = None
        self.display_ctf_hud = None
        self.display_flag_team_a = None
        self.display_flag_team_b = None
        self.display_entities.clear()
        self.display_bullets.clear()
        self.pending_entities_queue.clear()
        self.pending_walls_queue.clear()
        self.pending_bullets_queue.clear()
        self.pending_ctf_queue.clear()
    
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
    
    def on_ctf_update(self, packed_data: bytes) -> None:
        """Queue CTF state update."""
        if packed_data:
            self.pending_ctf_queue.append(packed_data)
    
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
    
    def apply_ctf_update(self, packed_data: bytes) -> None:
        """Update CTF visuals from state packet."""
        try:
            # Parse JSON state from server
            json_str = packed_data.decode('utf-8')
            self.ctf_state = json.loads(json_str)
            
            # Update flag positions
            flag_a = self.ctf_state.get("flag_team_a", {})
            flag_b = self.ctf_state.get("flag_team_b", {})
            
            if self.display_flag_team_a and flag_a:
                self.display_flag_team_a.update_position(
                    flag_a.get("x", 100),
                    flag_a.get("y", LOGICAL_SCREEN_HEIGHT // 2)
                )
                self.display_flag_team_a.set_carrier(flag_a.get("carrier"))
                self.display_flag_team_a.set_dropped(not flag_a.get("at_base", False) and flag_a.get("carrier") is None)
            
            if self.display_flag_team_b and flag_b:
                self.display_flag_team_b.update_position(
                    flag_b.get("x", LOGICAL_SCREEN_WIDTH - 100),
                    flag_b.get("y", LOGICAL_SCREEN_HEIGHT // 2)
                )
                self.display_flag_team_b.set_carrier(flag_b.get("carrier"))
                self.display_flag_team_b.set_dropped(not flag_b.get("at_base", False) and flag_b.get("carrier") is None)
            
            # Update HUD
            if self.display_ctf_hud:
                self.display_ctf_hud.update_from_state(self.ctf_state)
            
            # Update win screen
            game_over = self.ctf_state.get("game_over", False)
            winner_team = self.ctf_state.get("winner_team", 0)
            
            if game_over and self.win_label and self.win_background:
                # Show win screen (removed winner_team > 0 check to show tie games too)
                self.win_background.visible = True
                self.win_label.visible = True
                
                # Set message and color based on winner
                if winner_team == 1:  # Team A -> Blue
                    self.win_label.text = "TEAM BLUE WINS!"
                    self.win_label.color = (100, 150, 255, 255)  # Blue
                elif winner_team == 2:  # Team B -> Red
                    self.win_label.text = "TEAM RED WINS!"
                    self.win_label.color = (255, 100, 100, 255)  # Red
                else:  # Tie (Team.NEUTRAL) or invalid
                    self.win_label.text = "TIE GAME!"
                    self.win_label.color = (200, 200, 200, 255)  # Gray
                
                logger.info(f"Win screen displayed: {self.win_label.text}")
        
        except (ValueError, json.JSONDecodeError) as e:
            logger.warning("Failed to parse CTF state: %s", e)
            return
    
    def refresh_all_entity_fov(self) -> None:
        """Refresh FOV visualization for all entities."""
        for display_entity in self.display_entities.values():
            display_entity.update_fov_polygon()
