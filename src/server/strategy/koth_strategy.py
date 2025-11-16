# External libraries
import random
import math


# Internal libraries
from server.strategy.base import Strategy
from common.config import Direction
from common.koth_config import (
    KOTH_ZONE_CENTER_X,
    KOTH_ZONE_CENTER_Y,
    KOTH_ZONE_RADIUS,
    KOTH_ZONE_RECT_X,
    KOTH_ZONE_RECT_Y,
    KOTH_ZONE_RECT_WIDTH,
    KOTH_ZONE_RECT_HEIGHT,
    KOTH_ZONE_SHAPE,
)


class KOTHStrategy(Strategy):
    """
    Aggressive KOTH strategy - GET IN ZONE AND HOLD IT.
    
    Behavior:
    - Rush to zone immediately
    - Stay in zone at all costs
    - Shoot any enemies in or near zone
    - Only leave zone if very low health
    """
    
    # Configuration
    ZONE_ORBIT_RADIUS = 80.0  # How close to center to patrol
    LOW_HEALTH_THRESHOLD = 20.0  # When to temporarily leave zone
    CHANGE_DIRECTION_INTERVAL = 0.8  # Change patrol direction
    
    def __init__(self) -> None:
        """Initialize strategy state."""
        self.zone_center_x = KOTH_ZONE_CENTER_X
        self.zone_center_y = KOTH_ZONE_CENTER_Y
        self.patrol_direction = random.choice(list(Direction))
        self.direction_timer = 0.0
        self.in_zone = False
    
    def execute(self, agent, dt: float) -> None:
        """
        Execute KOTH strategy.
        
        Args:
            agent: Agent instance to control.
            dt: Delta time in seconds.
        """
        # Always detect enemies
        agent.detect_enemies()
        
        # Check if we need to reload
        if agent.current_ammo == 0 and agent.reload_timer is None:
            agent.start_reload()
        
        # Check if we're in the zone
        self.in_zone = self._is_in_zone(agent)
        
        # Calculate distance to zone center
        dx = self.zone_center_x - agent.state.x
        dy = self.zone_center_y - agent.state.y
        distance_to_center = math.sqrt(dx * dx + dy * dy)
        
        # Very low health - temporarily retreat
        if agent.health < self.LOW_HEALTH_THRESHOLD:
            self._emergency_retreat(agent, dt)
            return
        
        # If we see enemies, always shoot at them
        if agent.detected_enemies:
            target_id = agent.get_closest_enemy()
            if target_id and target_id in agent.agents_dict:
                target = agent.agents_dict[target_id].state
                
                # Always aim at enemy
                agent.point_gun_at(target.x, target.y)
                
                # Always shoot if we have ammo
                if agent.current_ammo > 0 and agent.reload_timer is None:
                    agent.load_bullet()
        
        # Movement based on position
        if not self.in_zone:
            # Not in zone - RUSH TO IT
            self._rush_to_zone(agent, dt)
        else:
            # In zone - HOLD IT
            self._hold_zone(agent, dt, distance_to_center)
    
    def _is_in_zone(self, agent) -> bool:
        """Check if agent is inside the hill zone."""
        if KOTH_ZONE_SHAPE == "circle":
            dx = agent.state.x - KOTH_ZONE_CENTER_X
            dy = agent.state.y - KOTH_ZONE_CENTER_Y
            distance_sq = dx * dx + dy * dy
            return distance_sq <= KOTH_ZONE_RADIUS * KOTH_ZONE_RADIUS
        elif KOTH_ZONE_SHAPE == "rectangle":
            return (
                KOTH_ZONE_RECT_X <= agent.state.x <= KOTH_ZONE_RECT_X + KOTH_ZONE_RECT_WIDTH
                and KOTH_ZONE_RECT_Y <= agent.state.y <= KOTH_ZONE_RECT_Y + KOTH_ZONE_RECT_HEIGHT
            )
        return False
    
    def _rush_to_zone(self, agent, dt: float) -> None:
        """
        Move as fast as possible to the zone.
        
        Args:
            agent: Agent instance.
            dt: Delta time.
        """
        # Move directly toward zone center
        agent.move_towards(dt, self.zone_center_x, self.zone_center_y)
        
        # If no enemies to shoot at, point gun toward zone too
        if not agent.detected_enemies:
            agent.point_gun_at(self.zone_center_x, self.zone_center_y)
    
    def _hold_zone(self, agent, dt: float, distance_to_center: float) -> None:
        """
        Stay in zone and defend it.
        
        Args:
            agent: Agent instance.
            dt: Delta time.
            distance_to_center: Distance to zone center.
        """
        self.direction_timer += dt
        
        # If we're drifting toward edge, move back to center
        if distance_to_center > self.ZONE_ORBIT_RADIUS:
            agent.move_towards(dt, self.zone_center_x, self.zone_center_y)
            return
        
        # We're in a good position - patrol around center
        if self.direction_timer >= self.CHANGE_DIRECTION_INTERVAL:
            self.patrol_direction = random.choice(list(Direction))
            self.direction_timer = 0.0
        
        # Patrol
        agent.move(dt, self.patrol_direction)
        
        # If we hit a wall, change direction immediately
        if agent.is_blocked():
            self.patrol_direction = random.choice(list(Direction))
            agent.move(dt, self.patrol_direction)
    
    def _emergency_retreat(self, agent, dt: float) -> None:
        """
        Emergency retreat when very low health.
        
        Args:
            agent: Agent instance.
            dt: Delta time.
        """
        # If we have enemies, run away from closest one
        if agent.detected_enemies:
            target_id = agent.get_closest_enemy()
            if target_id and target_id in agent.agents_dict:
                enemy = agent.agents_dict[target_id].state
                
                # Move away from enemy
                dx = agent.state.x - enemy.x
                dy = agent.state.y - enemy.y
                angle = math.atan2(dy, dx)
                direction = self._angle_to_direction(angle)
                agent.move(dt, direction)
                
                # Still shoot while retreating
                agent.point_gun_at(enemy.x, enemy.y)
                if agent.current_ammo > 0 and agent.reload_timer is None:
                    agent.load_bullet()
                return
        
        # No visible enemies - move randomly away from zone
        dx = agent.state.x - self.zone_center_x
        dy = agent.state.y - self.zone_center_y
        angle = math.atan2(dy, dx)
        direction = self._angle_to_direction(angle)
        agent.move(dt, direction)
    
    def _angle_to_direction(self, angle: float) -> Direction:
        """Convert angle to nearest 8-direction."""
        angle = angle % (2 * math.pi)
        section = int((angle + math.pi / 8) / (math.pi / 4)) % 8
        
        directions = [
            Direction.EAST,
            Direction.NORTH_EAST,
            Direction.NORTH,
            Direction.NORTH_WEST,
            Direction.WEST,
            Direction.SOUTH_WEST,
            Direction.SOUTH,
            Direction.SOUTH_EAST,
        ]
        
        return directions[section]