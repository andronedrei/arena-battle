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
    CHANGE_DIRECTION_INTERVAL = 0.5  # Change direction every half second when searching
    HEALTH_RETREAT_THRESHOLD = 25.0  # Only retreat when very low health
    
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
        # Get closest enemy
        target_id = agent.get_closest_enemy()
        if not target_id or target_id not in agent.agents_dict:
            return
        
        target = agent.agents_dict[target_id].state
        
        # ALWAYS point gun at enemy
        agent.point_gun_at(target.x, target.y)
        
        # ALWAYS shoot if we have ammo
        if agent.current_ammo > 0 and agent.reload_timer is None:
            agent.load_bullet()
        
        # Calculate distance to enemy
        dx = target.x - agent.state.x
        dy = target.y - agent.state.y
        distance = math.sqrt(dx * dx + dy * dy)
        
        # Movement strategy based on health and distance
        if agent.health < self.HEALTH_RETREAT_THRESHOLD and distance < 200:
            # Very low health and enemy is close - back up while shooting
            retreat_angle = math.atan2(-dy, -dx)
            direction = self._angle_to_direction(retreat_angle)
            agent.move(dt, direction)
        elif distance > 100:
            # Enemy is far - move directly toward them
            agent.move_towards(dt, target.x, target.y)
        else:
            # Good distance - circle strafe while shooting
            # Move perpendicular to enemy
            angle_to_enemy = math.atan2(dy, dx)
            strafe_angle = angle_to_enemy + math.pi / 2
            
            # Randomly switch strafe direction
            if random.random() < 0.1:
                strafe_angle += math.pi
            
            direction = self._angle_to_direction(strafe_angle)
            agent.move(dt, direction)
    
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