# External libraries
from pyglet.graphics import Batch, Group
from pyglet.shapes import Circle, Rectangle, Polygon
import math


# Internal libraries
from client.display.batch_object import BatchObject
from common.states.state_entity import StateEntity, Team
from common.config import FOV_RATIO, FOV_OPENING, FOV_NUM_RAYS
from common.config import FOV_OPACITY, RAY_STEP_DIVISOR

from client.config import (
    TEAM_COLORS, DEFAULT_COLOR, GUN_LENGTH_RATIO, GUN_WIDTH_RATIO, GUN_COLOR
)


class DisplayEntity(BatchObject):
    """
    Pure visual representation of EntityState.
    Only handles rendering - no game logic or collision detection.
    """

    def __init__(self, batch: Batch, entity_state: StateEntity,
                 walls_state, group_order: int = 2, opacity: int = 255):
        """
        Constructor
        
        Args:
            batch: Pyglet batch for rendering
            entity_state: Entity state to visualize
            walls_state: StateWalls instance for FOV ray casting
            group_order: Base rendering layer order
            opacity: Visual opacity (0-255)
        """
        super().__init__(batch)
        self.state = entity_state
        self.walls_state = walls_state
        self.base_group_order = group_order

        # Choose color based on team
        color = self.get_team_color(entity_state.team)

        # FOV polygon (drawn first, behind everything)
        # Layer: group_order + 0
        self.fov_polygon = self.create_fov_polygon(opacity)

        # Visual representation (circle for body)
        # Layer: group_order + 1
        self.shape = self.register_sub_object(
            Circle(
                entity_state.x,
                entity_state.y,
                entity_state.radius,
                color=color,
                batch=batch,
                group=Group(order=group_order + 1)
            )
        )
        self.shape.opacity = opacity

        # Gun visual (rectangle)
        # Layer: group_order + 2
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
                group=Group(order=group_order + 2)
            )
        )
        
        # Set anchor so gun rotates from entity center (left-middle of rectangle)
        self.gun.anchor_x = 0
        self.gun.anchor_y = gun_width / 2
        
        # Convert radians to degrees (pyglet uses degrees)
        self.gun.rotation = math.degrees(entity_state.gun_angle)
        self.gun.opacity = opacity

    # === COLOR HELPERS ===

    def get_team_color(self, team: int) -> tuple[int, int, int]:
        """ Get color based on team. """
        return TEAM_COLORS.get(team, DEFAULT_COLOR)

    # === FOV VISUALIZATION ===

    def create_fov_polygon(self, opacity):
        """Create FOV visualization polygon using ray casting."""
        try:
            points = self.calculate_fov_polygon()
            
            if len(points) < 3:
                return None

            team_color = self.get_team_color(self.state.team)
            fov_opacity = min(FOV_OPACITY, opacity)

            # Create Polygon with unpacked points
            polygon = self.register_sub_object(
                Polygon(
                    *points,
                    color=team_color,
                    batch=self.batch,
                    group=Group(order=self.base_group_order + 0)
                )
            )
            polygon.opacity = fov_opacity

            return polygon
            
        except Exception as e:
            print(f"ERROR creating FOV polygon: {type(e).__name__}: {e}")
            import traceback
            traceback.print_exc()
            return None

    def calculate_fov_polygon(self):
        """Calculate FOV polygon points using ray casting."""
        fov_radius = FOV_RATIO * self.state.radius
        center_angle = self.state.gun_angle
        half_opening = FOV_OPENING / 2
        start_angle = center_angle - half_opening
        
        points = [(self.state.x, self.state.y)]
        angle_step = FOV_OPENING / FOV_NUM_RAYS
        
        for i in range(FOV_NUM_RAYS + 1):
            angle = start_angle + i * angle_step
            hit_point = self.cast_ray(self.state.x, self.state.y, angle, fov_radius)
            points.append(hit_point)
        
        return points

    def cast_ray(self, start_x, start_y, angle, max_distance):
        """Cast a single ray..."""
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
        
        # Reached max distance without hitting wall
        return (start_x + dx * max_distance, start_y + dy * max_distance)

    def update_fov_polygon(self):
        """Update FOV polygon based on current state."""
        if self.fov_polygon is None:
            return
        
        points = self.calculate_fov_polygon()
        if len(points) < 3:
            return
        
        # Delete old polygon and unregister
        self.fov_polygon.delete()
        self.unregister_sub_object(self.fov_polygon)
        
        # Create new polygon with updated points
        team_color = self.get_team_color(self.state.team)
        fov_opacity = min(FOV_OPACITY, self.fov_polygon.opacity)
        
        self.fov_polygon = self.register_sub_object(
            Polygon(
                *points,
                color=team_color,
                batch=self.batch,
                group=Group(order=self.base_group_order + 0)
            )
        )
        self.fov_polygon.opacity = fov_opacity


    # === STATE SYNCHRONIZATION ===

    def sync_from_state(self, new_state: StateEntity):
        """
        Update visual from new state data.
        Call this after receiving network updates.
        """
        self.state = new_state
 
        # Update FOV polygon
        self.update_fov_polygon()
 
        # Update body position and size
        self.shape.x = new_state.x
        self.shape.y = new_state.y
        self.shape.radius = new_state.radius

        # Update gun position, size, and rotation
        self.gun.x = new_state.x
        self.gun.y = new_state.y

        gun_length = new_state.radius * GUN_LENGTH_RATIO
        gun_width = new_state.radius * GUN_WIDTH_RATIO
        self.gun.width = gun_length
        self.gun.height = gun_width

        # Update anchor when size changes
        self.gun.anchor_y = gun_width / 2

        # Update gun angle (convert radians to degrees)
        self.gun.rotation = math.degrees(new_state.gun_angle)

        # Update color if team changed
        new_color = self.get_team_color(new_state.team)
        if self.shape.color != new_color:
            self.shape.color = new_color

    # === VISUAL PROPERTY SETTERS ===

    def set_color(self, color: tuple[int, int, int]):
        """ Change visual color (body only, gun stays at GUN_COLOR). """
        self.shape.color = color

    def set_opacity(self, opacity: int):
        """ Change visual opacity (0-255) for body and gun. """
        self.shape.opacity = opacity
        self.gun.opacity = opacity

        # Update FOV opacity
        if self.fov_polygon:
            fov_opacity = min(FOV_OPACITY, opacity)
            self.fov_polygon.opacity = fov_opacity

    # === CLEANUP ===

    def delete(self):
        """ Cleanup rendering resources. """
        super().delete()
