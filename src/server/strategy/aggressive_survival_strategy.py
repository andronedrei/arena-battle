# External libraries
import random
import math


# Internal libraries
from server.strategy.base import Strategy
from common.config import Direction


class AggressiveSurvivalStrategy(Strategy):
    """
    Very aggressive survival strategy - hunts and kills enemies.
    
    Behavior:
    - Always moves forward toward enemies
    - Shoots constantly when enemies are visible
    - Simple but effective movement
    """
    
    # Configuration
    CHANGE_DIRECTION_INTERVAL = 0.2  # Change direction more frequently when searching
    HEALTH_RETREAT_THRESHOLD = 12.0  # Retreat only when very very low health
    CLOSE_COMBAT_DISTANCE = 120  # prefer to close in for lethal engagements
    
    def __init__(self) -> None:
        """Initialize strategy state."""
        self.direction_timer = 0.0
        self.current_search_direction = random.choice(list(Direction))
    
    def execute(self, agent, dt: float) -> None:
        """
        Execute aggressive survival strategy.
        
        Args:
            agent: Agent instance to control.
            dt: Delta time in seconds.
        """
        # Always detect enemies every frame for maximum responsiveness
        agent.detect_enemies()
        
        # Check if we need to reload
        if agent.current_ammo == 0 and agent.reload_timer is None:
            agent.start_reload()
        
        # If we have any enemies in sight, go into combat mode
        if agent.detected_enemies:
            self._combat_mode(agent, dt)
        else:
            # No enemies visible - search aggressively
            self._search_mode(agent, dt)
    
    def _combat_mode(self, agent, dt: float) -> None:
        """
        Full combat mode - focus on killing the enemy.
        
        Args:
            agent: Agent instance.
            dt: Delta time.
        """
        # Prefer weakest (lowest health) visible enemy to focus-fire
        target_id = None
        min_health = float("inf")
        for eid in agent.detected_enemies:
            if eid in agent.agents_dict:
                e = agent.agents_dict[eid].state
                if e.health < min_health:
                    min_health = e.health
                    target_id = eid

        if not target_id or target_id not in agent.agents_dict:
            return

        target = agent.agents_dict[target_id].state
        
        # ALWAYS point gun at enemy (aim slightly ahead by nudging toward their facing)
        agent.point_gun_at(target.x, target.y)

        # ALWAYS shoot if we have ammo
        if agent.current_ammo > 0 and agent.reload_timer is None:
            agent.load_bullet()
        
        # Calculate distance to enemy
        dx = target.x - agent.state.x
        dy = target.y - agent.state.y
        distance = math.sqrt(dx * dx + dy * dy)
        
        # Movement strategy based on health and distance
        # Movement strategy: be more aggressive about closing gaps and finishing targets
        if agent.health < self.HEALTH_RETREAT_THRESHOLD and distance < 150:
            # Very low health and enemy is close - back up a bit while firing if possible
            retreat_angle = math.atan2(-dy, -dx)
            direction = self._angle_to_direction(retreat_angle)
            agent.move(dt, direction)
        elif distance > self.CLOSE_COMBAT_DISTANCE:
            # Enemy is far - rush directly toward them to close distance quickly
            agent.move_towards(dt, target.x, target.y)
        else:
            # Close enough - perform aggressive strafing to maintain pressure
            angle_to_enemy = math.atan2(dy, dx)
            # Alternate strafing directions faster
            strafe_sign = -1 if random.random() < 0.5 else 1
            strafe_angle = angle_to_enemy + (math.pi / 2) * strafe_sign
            direction = self._angle_to_direction(strafe_angle)
            agent.move(dt, direction)
            # If very close, sometimes dash directly into the enemy to ram shots
            if distance < 60 and random.random() < 0.3:
                agent.move_towards(dt, target.x, target.y)
    
    def _search_mode(self, agent, dt: float) -> None:
        """
        Search for enemies when none are visible.
        
        Args:
            agent: Agent instance.
            dt: Delta time.
        """
        self.direction_timer += dt
        
        # Change direction periodically while searching
        if self.direction_timer >= self.CHANGE_DIRECTION_INTERVAL:
            self.current_search_direction = random.choice(list(Direction))
            self.direction_timer = 0.0
        
        # Keep moving in search direction
        agent.move(dt, self.current_search_direction)
        
        # If blocked, immediately pick new direction
        if agent.is_blocked():
            self.current_search_direction = random.choice(list(Direction))
            agent.move(dt, self.current_search_direction)
    
    def _angle_to_direction(self, angle: float) -> Direction:
        """
        Convert angle to nearest 8-direction.
        
        Args:
            angle: Angle in radians.
        
        Returns:
            Direction enum value.
        """
        # Normalize angle to [0, 2π)
        angle = angle % (2 * math.pi)
        
        # Map to 8 directions
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