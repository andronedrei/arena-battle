"""
CTF HUD - displays scores, timer, flag status, and captures.

Shows team captures, flag positions, remaining time, and winner announcement.
"""

from pyglet.graphics import Batch, Group
from pyglet.text import Label
from pyglet.shapes import Rectangle

from client.display.batch_object import BatchObject
from common.config import LOGICAL_SCREEN_WIDTH, LOGICAL_SCREEN_HEIGHT


class DisplayCTFHUD(BatchObject):
    """
    CTF heads-up display.
    
    Shows game state information at the top of the screen.
    """
    
    def __init__(
        self,
        batch: Batch,
        group_order: int = 10,  # High order to render on top
    ) -> None:
        """
        Initialize CTF HUD.
        
        Args:
            batch: Pyglet batch for rendering.
            group_order: Rendering layer order.
        """
        super().__init__(batch)
        
        # HUD background
        hud_height = 80
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
        
        # Team A captures (left side)
        self.label_team_a_captures = self.register_sub_object(
            Label(
                "Team A: 0 captures",
                x=100,
                y=LOGICAL_SCREEN_HEIGHT - 25,
                anchor_x="center",
                anchor_y="center",
                font_size=18,
                color=(100, 200, 255, 255),
                batch=batch,
                group=Group(order=group_order + 1),
            )
        )
        
        # Team A flag status
        self.label_team_a_flag = self.register_sub_object(
            Label(
                "Flag: At Base",
                x=100,
                y=LOGICAL_SCREEN_HEIGHT - 55,
                anchor_x="center",
                anchor_y="center",
                font_size=12,
                color=(150, 220, 255, 255),
                batch=batch,
                group=Group(order=group_order + 1),
            )
        )
        
        # Team B captures (right side)
        self.label_team_b_captures = self.register_sub_object(
            Label(
                "Team B: 0 captures",
                x=LOGICAL_SCREEN_WIDTH - 100,
                y=LOGICAL_SCREEN_HEIGHT - 25,
                anchor_x="center",
                anchor_y="center",
                font_size=18,
                color=(255, 100, 100, 255),
                batch=batch,
                group=Group(order=group_order + 1),
            )
        )
        
        # Team B flag status
        self.label_team_b_flag = self.register_sub_object(
            Label(
                "Flag: At Base",
                x=LOGICAL_SCREEN_WIDTH - 100,
                y=LOGICAL_SCREEN_HEIGHT - 55,
                anchor_x="center",
                anchor_y="center",
                font_size=12,
                color=(255, 150, 150, 255),
                batch=batch,
                group=Group(order=group_order + 1),
            )
        )
        
        # Game title (center top)
        self.label_title = self.register_sub_object(
            Label(
                "CAPTURE THE FLAG",
                x=LOGICAL_SCREEN_WIDTH // 2,
                y=LOGICAL_SCREEN_HEIGHT - 20,
                anchor_x="center",
                anchor_y="center",
                font_size=16,
                color=(200, 200, 200, 255),
                batch=batch,
                group=Group(order=group_order + 1),
            )
        )
        
        # Timer (center, below title)
        self.label_timer = self.register_sub_object(
            Label(
                "Time: 0:00",
                x=LOGICAL_SCREEN_WIDTH // 2,
                y=LOGICAL_SCREEN_HEIGHT - 50,
                anchor_x="center",
                anchor_y="center",
                font_size=14,
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
    
    def update_from_state(self, ctf_state: dict) -> None:
        """
        Update HUD display from CTF state.
        
        Args:
            ctf_state: Dictionary containing CTF game state:
                {
                    "team_a_captures": int,
                    "team_b_captures": int,
                    "flag_team_a": {"x": float, "y": float, "carrier": int|None, "at_base": bool},
                    "flag_team_b": {"x": float, "y": float, "carrier": int|None, "at_base": bool},
                    "time_elapsed": float,
                    "max_time": float,
                    "max_captures": int,
                    "game_over": bool,
                    "winner_team": int
                }
        """
        # Update captures
        team_a_captures = ctf_state.get("team_a_captures", 0)
        team_b_captures = ctf_state.get("team_b_captures", 0)
        
        self.label_team_a_captures.text = f"Team A: {team_a_captures} captures"
        self.label_team_b_captures.text = f"Team B: {team_b_captures} captures"
        
        # Update flag statuses
        flag_a = ctf_state.get("flag_team_a", {})
        flag_b = ctf_state.get("flag_team_b", {})
        
        self.label_team_a_flag.text = self._get_flag_status_text(flag_a)
        self.label_team_b_flag.text = self._get_flag_status_text(flag_b)
        
        # Update timer
        time_elapsed = ctf_state.get("time_elapsed", 0.0)
        max_time = ctf_state.get("max_time", 0.0)
        
        minutes = int(time_elapsed // 60)
        seconds = int(time_elapsed % 60)
        
        if max_time > 0:
            remaining = max_time - time_elapsed
            remaining_minutes = int(remaining // 60)
            remaining_seconds = int(remaining % 60)
            self.label_timer.text = f"Time Left: {remaining_minutes}:{remaining_seconds:02d}"
        else:
            self.label_timer.text = f"Time: {minutes}:{seconds:02d}"
        
        # Hide winner announcement from HUD (scene has its own larger win screen)
        self.label_winner.text = ""
    
    def _get_flag_status_text(self, flag_data: dict) -> str:
        """
        Generate flag status text.
        
        Args:
            flag_data: Dictionary with flag information.
        
        Returns:
            Status string (e.g., "Flag: Carried by #3", "Flag: Dropped").
        """
        if flag_data.get("at_base", False):
            return "Flag: At Base"
        
        carrier = flag_data.get("carrier")
        if carrier is not None:
            return f"Flag: Carried by #{carrier}"
        
        return "Flag: Dropped"
    
    def delete(self) -> None:
        """Clean up HUD resources."""
        super().delete()
