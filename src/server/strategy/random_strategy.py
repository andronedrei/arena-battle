# External libraries
import random

# Internal libraries
from server.strategy.base import Strategy
from common.config import Direction


class RandomStrategy(Strategy):
    """
    Random movement strategy for agent behavior.

    Agent moves randomly, changing direction periodically. Shoots at
    nearest detected enemy.
    """

    # Configuration
    DIRECTION_CHANGE_INTERVAL = 0.6  # Change direction more frequently to find enemies

    # Initialization

    def __init__(self, game_manager=None) -> None:
        """Initialize strategy state.
        
        Args:
            game_manager: Optional game manager instance (required for CTF mode).
        """
        self.game_manager = game_manager
        self.current_direction = Direction.NORTH
        self.direction_timer = 0.0

    # Behavior

    def execute(self, agent, dt: float) -> None:
        """
        Execute strategy logic for one frame.

        Moves in random direction, changing every DIRECTION_CHANGE_INTERVAL
        seconds. Points at and shoots nearest visible enemy.

        Args:
            agent: Agent instance to control.
            dt: Delta time in seconds.
        """
        self.direction_timer += dt

        # Update direction at interval
        if self.direction_timer >= self.DIRECTION_CHANGE_INTERVAL:
            self.current_direction = random.choice(list(Direction))
            self.direction_timer = 0.0

        # Move in current direction
        agent.move(dt, self.current_direction)

        # Engage visible enemies aggressively
        if agent.detected_enemies:
            # Prefer NEAREST enemy (closest distance)
            target_id = None
            min_dist_sq = float("inf")
            
            for eid in agent.detected_enemies:
                if eid in agent.agents_dict:
                    e = agent.agents_dict[eid].state

                    # Calculate distance squared (faster than sqrt)
                    dx = e.x - agent.state.x
                    dy = e.y - agent.state.y
                    dist_sq = dx*dx + dy*dy
                    
                    # Prioritize by closest distance
                    if dist_sq < min_dist_sq:
                        min_dist_sq = dist_sq
                        target_id = eid

            if target_id is not None:
                target = agent.agents_dict[target_id].state
                agent.point_gun_at(target.x, target.y)
                
                # Load AND shoot
                agent.load_bullet()
                if hasattr(agent, 'shoot'): # Safety check
                    agent.shoot()
                
                # Move slightly toward enemy to increase hit chance
                agent.move_towards(dt, target.x, target.y)
                