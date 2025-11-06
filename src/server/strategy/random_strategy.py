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
    DIRECTION_CHANGE_INTERVAL = 2.0  # Seconds between direction changes

    # Initialization

    def __init__(self) -> None:
        """Initialize strategy state."""
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

        # Engage visible enemies
        if agent.detected_enemies:
            target_id = agent.get_closest_enemy()
            target = agent.agents_dict[target_id].state
            agent.point_gun_at(target.x, target.y)
            agent.load_bullet()
