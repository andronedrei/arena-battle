# client/display/display_bullet.py
from pyglet.graphics import Batch, Group
from pyglet.shapes import Circle
import math

from client.display.batch_object import BatchObject
from common.states.state_bullet import StateBullet
from client.config import TEAM_COLORS, DEFAULT_COLOR, BULLET_COLOR


class DisplayBullet(BatchObject):
    """
    Pure visual representation of StateBullet.
    Only handles rendering - no game logic.
    """

    def __init__(self, batch: Batch, bullet_state: StateBullet,
                 group_order: int = 1, opacity: int = 255):
        """
        Constructor
        
        Args:
            batch: Pyglet batch for rendering
            bullet_state: Bullet state to visualize
            group_order: Rendering layer order
            opacity: Visual opacity (0-255)
        """
        super().__init__(batch)
        self.state = bullet_state

        # Choose color based on team
        color = self.get_team_color(bullet_state.team)

        # Visual representation (circle for bullet)
        self.shape = self.register_sub_object(
            Circle(
                bullet_state.x,
                bullet_state.y,
                bullet_state.radius,
                color=color,
                batch=batch,
                group=Group(order=group_order)
            )
        )
        self.shape.opacity = opacity

    # === COLOR HELPERS ===

    def get_team_color(self, team: int) -> tuple[int, int, int]:
        """Get color based on team."""
        return TEAM_COLORS.get(team, DEFAULT_COLOR)

    # === STATE SYNCHRONIZATION ===

    def sync_from_state(self, new_state: StateBullet):
        """
        Update visual from new state data.
        Call this after receiving network updates.
        """
        self.state = new_state

        # Update position
        self.shape.x = new_state.x
        self.shape.y = new_state.y
        self.shape.radius = new_state.radius

        # Update color if team changed
        new_color = self.get_team_color(new_state.team)
        if self.shape.color != new_color:
            self.shape.color = new_color

    # === VISUAL PROPERTY SETTERS ===

    def set_color(self, color: tuple[int, int, int]):
        """Change visual color."""
        self.shape.color = color

    def set_opacity(self, opacity: int):
        """Change visual opacity (0-255)."""
        self.shape.opacity = opacity

    # === CLEANUP ===

    def delete(self):
        """Cleanup rendering resources."""
        super().delete()
