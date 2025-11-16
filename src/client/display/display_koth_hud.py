"""
KOTH HUD - displays scores, timer, and game status.

Shows team scores, zone control, remaining time, and winner announcement.
"""

from pyglet.graphics import Batch, Group
from pyglet.text import Label
from pyglet.shapes import Rectangle

from client.display.batch_object import BatchObject
from common.config import LOGICAL_SCREEN_WIDTH, LOGICAL_SCREEN_HEIGHT

from common.koth_config import KOTH_MAX_POINTS, KOTH_MAX_DURATION
from common.states.state_koth import StateKOTH, KOTHZoneStatus


class DisplayKOTHHUD(BatchObject):
    """
    KOTH heads-up display.
    
    Shows game state information at the top of the screen.
    """
    
    def __init__(
        self,
        batch: Batch,
        group_order: int = 10,  # High order to render on top
    ) -> None:
        """
        Initialize KOTH HUD.
        
        Args:
            batch: Pyglet batch for rendering.
            group_order: Rendering layer order.
        """
        super().__init__(batch)
        
        # HUD background
        hud_height = 60
        self.bg = self.register_sub_object(
            Rectangle(
                0, LOGICAL_SCREEN_HEIGHT - hud_height,
                LOGICAL_SCREEN_WIDTH, hud_height,
                color=(40, 40, 40),
                batch=batch,
                group=Group(order=group_order),
            )
        )
        self.bg.opacity = 200
        
        # Team A score (left)
        self.label_team_a = self.register_sub_object(
            Label(
                "Team A: 0",
                x=100,
                y=LOGICAL_SCREEN_HEIGHT - 30,
                anchor_x="center",
                anchor_y="center",
                font_size=18,
                color=(100, 200, 255, 255),
                batch=batch,
                group=Group(order=group_order + 1),
            )
        )
        
        # Team B score (right)
        self.label_team_b = self.register_sub_object(
            Label(
                "Team B: 0",
                x=LOGICAL_SCREEN_WIDTH - 100,
                y=LOGICAL_SCREEN_HEIGHT - 30,
                anchor_x="center",
                anchor_y="center",
                font_size=18,
                color=(255, 100, 100, 255),
                batch=batch,
                group=Group(order=group_order + 1),
            )
        )
        
        # Zone status (center)
        self.label_zone_status = self.register_sub_object(
            Label(
                "Zone: NEUTRAL",
                x=LOGICAL_SCREEN_WIDTH // 2,
                y=LOGICAL_SCREEN_HEIGHT - 20,
                anchor_x="center",
                anchor_y="center",
                font_size=14,
                color=(200, 200, 200, 255),
                batch=batch,
                group=Group(order=group_order + 1),
            )
        )
        
        # Timer (center, below status)
        self.label_timer = self.register_sub_object(
            Label(
                "Time: 0:00",
                x=LOGICAL_SCREEN_WIDTH // 2,
                y=LOGICAL_SCREEN_HEIGHT - 45,
                anchor_x="center",
                anchor_y="center",
                font_size=12,
                color=(180, 180, 180, 255),
                batch=batch,
                group=Group(order=group_order + 1),
            )
        )
        
        # Winner announcement (hidden by default)
        self.label_winner = self.register_sub_object(
            Label(
                "",
                x=LOGICAL_SCREEN_WIDTH // 2,
                y=LOGICAL_SCREEN_HEIGHT // 2,
                anchor_x="center",
                anchor_y="center",
                font_size=48,
                color=(255, 255, 100, 255),
                batch=batch,
                group=Group(order=group_order + 2),
            )
        )
    
    def update_from_state(self, koth_state: StateKOTH) -> None:
        """
        Update HUD display from KOTH state.
        
        Args:
            koth_state: Current KOTH game state.
        """
        # Update scores
        self.label_team_a.text = f"Team A: {int(koth_state.team_a_score)}"
        self.label_team_b.text = f"Team B: {int(koth_state.team_b_score)}"
        
        # Update zone status
        zone_names = {
            KOTHZoneStatus.NEUTRAL: "NEUTRAL",
            KOTHZoneStatus.TEAM_A: "TEAM A",
            KOTHZoneStatus.TEAM_B: "TEAM B",
            KOTHZoneStatus.CONTESTED: "CONTESTED",
        }
        zone_name = zone_names.get(koth_state.zone_status, "UNKNOWN")
        self.label_zone_status.text = f"Zone: {zone_name}"
        
        # Update zone status color
        zone_colors = {
            KOTHZoneStatus.NEUTRAL: (200, 200, 200, 255),
            KOTHZoneStatus.TEAM_A: (100, 200, 255, 255),
            KOTHZoneStatus.TEAM_B: (255, 100, 100, 255),
            KOTHZoneStatus.CONTESTED: (255, 255, 100, 255),
        }
        self.label_zone_status.color = zone_colors.get(
            koth_state.zone_status, (200, 200, 200, 255)
        )
        
        # Update timer
        minutes = int(koth_state.time_elapsed // 60)
        seconds = int(koth_state.time_elapsed % 60)
        
        if KOTH_MAX_DURATION > 0:
            remaining = KOTH_MAX_DURATION - koth_state.time_elapsed
            remaining_minutes = int(remaining // 60)
            remaining_seconds = int(remaining % 60)
            self.label_timer.text = f"Time Left: {remaining_minutes}:{remaining_seconds:02d}"
        else:
            self.label_timer.text = f"Time: {minutes}:{seconds:02d}"
        
        # Update winner announcement
        if koth_state.game_over:
            if koth_state.winner_team == 1:
                self.label_winner.text = "TEAM A WINS!"
                self.label_winner.color = (100, 200, 255, 255)
            elif koth_state.winner_team == 2:
                self.label_winner.text = "TEAM B WINS!"
                self.label_winner.color = (255, 100, 100, 255)
            else:
                self.label_winner.text = "DRAW!"
                self.label_winner.color = (200, 200, 200, 255)
        else:
            self.label_winner.text = ""
    
    def delete(self) -> None:
        """Clean up HUD resources."""
        super().delete()