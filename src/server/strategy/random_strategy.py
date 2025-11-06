# server/strategy/random_strategy.py
from server.strategy.base import Strategy
from server.gameplay.agent import Direction
import random


class RandomStrategy(Strategy):
    """Random movement strategy - never gets blocked."""
    
    DIRECTION_CHANGE_INTERVAL = 2.0  # Change direction every 2 seconds
    
    def __init__(self):
        """Initialize strategy state."""
        self.current_direction = Direction.NORTH
        self.direction_timer = 0.0
    
    def execute(self, agent, dt: float):
        """Move randomly and shoot when target detected."""
        self.direction_timer += dt
        
        # Pick random direction every 2 seconds
        if self.direction_timer >= self.DIRECTION_CHANGE_INTERVAL:
            self.current_direction = random.choice(list(Direction))
            self.direction_timer = 0.0
        
        # Move in random direction (always succeeds)
        agent.move(dt, self.current_direction)
        
        # If enemy detected, point gun and fire
        if agent.detected_enemies:
            target_id = agent.get_closest_enemy()
            target = agent.agents_dict[target_id].state
            agent.point_gun_at(target.x, target.y)
            agent.load_bullet()
