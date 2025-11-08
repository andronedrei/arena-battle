# External libraries
import math

from pyglet.graphics import Batch, Group
from pyglet.shapes import Circle, Polygon, Rectangle
from pyglet.text import Label


# Internal libraries
from client.config import (
    DEFAULT_COLOR,
    GUN_COLOR,
    GUN_LENGTH_RATIO,
    GUN_WIDTH_RATIO,
    TEAM_COLORS,
)
from client.display.batch_object import BatchObject
from common.config import (
    FOV_NUM_RAYS,
    FOV_OPENING,
    FOV_OPACITY,
    FOV_RATIO,
    RAY_STEP_DIVISOR,
)
from common.config import AMMO_INFINITE
from common.states.state_entity import StateEntity
from common.states.state_walls import StateWalls


class DisplayEntity(BatchObject):
    """
    Visual representation of entity state.

    Renders entity body, gun, and field-of-view polygon using pyglet shapes.
    Syncs with StateEntity for position, orientation, and team changes.
    """

    def __init__(
        self,
        batch: Batch,
        entity_state: StateEntity,
        walls_state: StateWalls,
        group_order: int = 2,
        opacity: int = 255,
    ) -> None:
        """
        Initialize entity display.

        Args:
            batch: Pyglet batch for rendering.
            entity_state: Entity state to visualize.
            walls_state: StateWalls for FOV ray casting.
            group_order: Base rendering layer order.
            opacity: Visual opacity (0-255).
        """
        super().__init__(batch)
        self.state = entity_state
        self.walls_state = walls_state
        self.base_group_order = group_order

        color = self.get_team_color(entity_state.team)

        # FOV polygon (behind body)
        self.fov_polygon = self.create_fov_polygon(opacity)

        # Body circle
        self.shape = self.register_sub_object(
            Circle(
                entity_state.x,
                entity_state.y,
                entity_state.radius,
                color=color,
                batch=batch,
                group=Group(order=group_order + 1),
            )
        )
        self.shape.opacity = opacity

        # Gun rectangle
        gun_length = entity_state.radius * GUN_LENGTH_RATIO
        gun_width = entity_state.radius * GUN_WIDTH_RATIO

        self.gun = self.register_sub_object(
            Rectangle(
                x=entity_state.x,
                y=entity_state.y,
                width=gun_length,
                height=gun_width,
                color=GUN_COLOR,
                batch=batch,
                group=Group(order=group_order + 2),
            )
        )
        self.gun.anchor_x = 0
        self.gun.anchor_y = gun_width / 2
        self.gun.rotation = math.degrees(entity_state.gun_angle)
        self.gun.opacity = opacity

        # Health and ammo labels (above the entity)
        hp_y = entity_state.y + entity_state.radius + 6
        self.hp_label = self.register_sub_object(
            Label(
                f"HP: {int(entity_state.health)}",
                x=entity_state.x,
                y=hp_y,
                anchor_x="center",
                anchor_y="bottom",
                font_size=10,
                color=(255, 255, 255, 255),
                batch=batch,
                group=Group(order=group_order + 3),
            )
        )

        ammo_text = (
            "∞" if entity_state.ammo == AMMO_INFINITE else str(int(entity_state.ammo))
        )
        self.ammo_label = self.register_sub_object(
            Label(
                f"Ammo: {ammo_text}",
                x=entity_state.x,
                y=hp_y + 12,
                anchor_x="center",
                anchor_y="bottom",
                font_size=10,
                color=(200, 200, 200, 255),
                batch=batch,
                group=Group(order=group_order + 3),
            )
        )

    # Color

    def get_team_color(self, team: int) -> tuple[int, int, int]:
        """
        Get color for a given team.

        Args:
            team: Team identifier from Team enum.

        Returns:
            RGB color tuple.
        """
        return TEAM_COLORS.get(team, DEFAULT_COLOR)

    # FOV visualization

    def create_fov_polygon(self, opacity: int) -> Polygon | None:
        """
        Create FOV visualization polygon via ray casting.

        Args:
            opacity: Opacity for the polygon (0-255).

        Returns:
            Polygon object or None if creation fails.
        """
        try:
            points = self.calculate_fov_polygon()

            if len(points) < 3:
                return None

            team_color = self.get_team_color(self.state.team)
            fov_opacity = min(FOV_OPACITY, opacity)

            polygon = self.register_sub_object(
                Polygon(
                    *points,
                    color=team_color,
                    batch=self.batch,
                    group=Group(order=self.base_group_order + 0),
                )
            )
            polygon.opacity = fov_opacity

            return polygon
        except (ValueError, RuntimeError):
            return None

    def calculate_fov_polygon(self) -> list[tuple[float, float]]:
        """
        Calculate FOV polygon points via ray casting.

        Returns:
            List of (x, y) coordinate tuples forming the FOV polygon.
        """
        fov_radius = FOV_RATIO * self.state.radius
        center_angle = self.state.gun_angle
        half_opening = FOV_OPENING / 2
        start_angle = center_angle - half_opening

        points = [(self.state.x, self.state.y)]
        angle_step = FOV_OPENING / FOV_NUM_RAYS

        for i in range(FOV_NUM_RAYS + 1):
            angle = start_angle + i * angle_step
            hit_point = self.cast_ray(
                self.state.x, self.state.y, angle, fov_radius
            )
            points.append(hit_point)

        return points

    def cast_ray(
        self, start_x: float, start_y: float, angle: float, max_distance: float
    ) -> tuple[float, float]:
        """
        Cast a ray from position along angle until hitting wall or max dist.

        Args:
            start_x: Ray origin X coordinate.
            start_y: Ray origin Y coordinate.
            angle: Ray direction angle in radians.
            max_distance: Maximum ray distance in pixels.

        Returns:
            Tuple of (hit_x, hit_y) coordinates.
        """
        dx = math.cos(angle)
        dy = -math.sin(angle)

        step_size = self.walls_state.grid_unit / RAY_STEP_DIVISOR
        current_x = start_x
        current_y = start_y
        traveled = 0

        while traveled < max_distance:
            current_x += dx * step_size
            current_y += dy * step_size
            traveled += step_size

            if self.walls_state.has_wall_at_pos(current_x, current_y):
                return (current_x, current_y)

        return (
            start_x + dx * max_distance,
            start_y + dy * max_distance,
        )

    def update_fov_polygon(self) -> None:
        """Recalculate FOV polygon with current entity state."""
        if self.fov_polygon is None:
            return

        points = self.calculate_fov_polygon()
        if len(points) < 3:
            return

        # Remove old polygon
        self.fov_polygon.delete()
        self.unregister_sub_object(self.fov_polygon)

        # Create new polygon
        team_color = self.get_team_color(self.state.team)
        fov_opacity = min(FOV_OPACITY, self.fov_polygon.opacity)

        self.fov_polygon = self.register_sub_object(
            Polygon(
                *points,
                color=team_color,
                batch=self.batch,
                group=Group(order=self.base_group_order + 0),
            )
        )
        self.fov_polygon.opacity = fov_opacity

    # State synchronization

    def sync_from_state(self, new_state: StateEntity) -> None:
        """
        Update visuals from new state data.

        Args:
            new_state: Updated entity state from network.
        """
        self.state = new_state

        self.update_fov_polygon()

        # Update body
        self.shape.x = new_state.x
        self.shape.y = new_state.y
        self.shape.radius = new_state.radius

        # Update gun
        self.gun.x = new_state.x
        self.gun.y = new_state.y

        gun_length = new_state.radius * GUN_LENGTH_RATIO
        gun_width = new_state.radius * GUN_WIDTH_RATIO
        self.gun.width = gun_length
        self.gun.height = gun_width
        self.gun.anchor_y = gun_width / 2

        self.gun.rotation = math.degrees(new_state.gun_angle)

        # Update color if team changed
        new_color = self.get_team_color(new_state.team)
        if self.shape.color != new_color:
            self.shape.color = new_color

        # Update health & ammo labels
        try:
            self.hp_label.text = f"HP: {int(new_state.health)}"
            self.hp_label.x = new_state.x
            self.hp_label.y = new_state.y + new_state.radius + 6

            if new_state.ammo == AMMO_INFINITE:
                self.ammo_label.text = "Ammo: ∞"
            else:
                self.ammo_label.text = f"Ammo: {int(new_state.ammo)}"
            self.ammo_label.x = new_state.x
            self.ammo_label.y = new_state.y + new_state.radius + 18
        except Exception:
            # If labels are unavailable for any reason, ignore UI update
            pass

    # Visual properties

    def set_color(self, color: tuple[int, int, int]) -> None:
        """
        Change body color.

        Args:
            color: RGB color tuple.
        """
        self.shape.color = color

    def set_opacity(self, opacity: int) -> None:
        """
        Change visual opacity for body and gun.

        Args:
            opacity: Opacity value (0-255).
        """
        self.shape.opacity = opacity
        self.gun.opacity = opacity

        if self.fov_polygon:
            fov_opacity = min(FOV_OPACITY, opacity)
            self.fov_polygon.opacity = fov_opacity

    # Cleanup

    def delete(self) -> None:
        """Clean up all rendering resources."""
        super().delete()
