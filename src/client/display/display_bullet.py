# External libraries
from pyglet.graphics import Batch, Group
from pyglet.shapes import Circle


# Internal libraries
from client.config import DEFAULT_COLOR, TEAM_COLORS
from client.display.batch_object import BatchObject
from common.states.state_bullet import StateBullet


class DisplayBullet(BatchObject):
    """
    Visual representation of bullet state.

    Manages rendering of bullets using pyglet shapes.
    Syncs with StateBullet for position and team changes.
    """

    def __init__(
        self,
        batch: Batch,
        bullet_state: StateBullet,
        group_order: int = 1,
        opacity: int = 255,
    ) -> None:
        """
        Initialize bullet display.

        Args:
            batch: Pyglet batch for rendering.
            bullet_state: Bullet state to visualize.
            group_order: Rendering layer order (z-depth).
            opacity: Visual opacity (0-255).
        """
        super().__init__(batch)
        self.state = bullet_state

        color = self.get_team_color(bullet_state.team)

        self.shape = self.register_sub_object(
            Circle(
                bullet_state.x,
                bullet_state.y,
                bullet_state.radius,
                color=color,
                batch=batch,
                group=Group(order=group_order),
            )
        )
        self.shape.opacity = opacity

    # Color

    def get_team_color(self, team: int) -> tuple[int, int, int]:
        """
        Get color for a given team.

        Args:
            team: Team identifier.

        Returns:
            RGB color tuple.
        """
        return TEAM_COLORS.get(team, DEFAULT_COLOR)

    # State synchronization

    def sync_from_state(self, new_state: StateBullet) -> None:
        """
        Update visuals from new state data.

        Args:
            new_state: Updated bullet state from network.
        """
        self.state = new_state

        self.shape.x = new_state.x
        self.shape.y = new_state.y
        self.shape.radius = new_state.radius

        # Update color if team changed
        new_color = self.get_team_color(new_state.team)
        if self.shape.color != new_color:
            self.shape.color = new_color

    # Visual properties

    def set_color(self, color: tuple[int, int, int]) -> None:
        """
        Change visual color.

        Args:
            color: RGB color tuple.
        """
        self.shape.color = color

    def set_opacity(self, opacity: int) -> None:
        """
        Change visual opacity.

        Args:
            opacity: Opacity value (0-255).
        """
        self.shape.opacity = opacity

    # Cleanup

    def delete(self) -> None:
        """Clean up all rendering resources."""
        super().delete()
