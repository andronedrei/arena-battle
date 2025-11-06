How to Build an Agent Strategy
Part 1: Available Agent Methods
Movement

    agent.move(dt, direction) - Move in direction (NORTH, SOUTH, EAST, WEST, NORTH_EAST, etc.)

    agent.move_towards(dt, target_x, target_y) - Move towards a point using 8-directional approach

    agent.is_blocked() - Check if movement was blocked

    agent.blocked_by() - Get what blocked the agent

Gun & Weapon

    agent.point_gun_at(target_x, target_y) - Rotate gun towards target

    agent.set_target_gun_angle(angle) - Set gun angle directly (radians)

    agent.load_bullet() - Fire weapon (automatically handles cooldown)

Vision & Detection

    agent.detected_enemies - Set of currently visible enemy IDs

    agent.can_see(target_id) - Quick check if specific agent is visible

    agent.get_closest_enemy() - Get nearest alive visible enemy

Agent Info

    agent.state.x, agent.state.y - Current position

    agent.state.gun_angle - Current gun angle (radians)

    agent.state.team - Team affiliation

    agent.health - Current health

    agent.is_alive() - Check if alive

    agent.agents_dict[agent_id].state - Access other agents' state

Part 2: Create Your Strategy

python
from server.strategy.base import Strategy
from common.config import Direction
import math


class HuntStrategy(Strategy):
    """Hunt down and shoot the closest visible enemy."""

    def __init__(self) -> None:
        self.patrol_direction = Direction.NORTH
        self.patrol_timer = 0.0

    def execute(self, agent, dt: float) -> None:
        """Execute hunt behavior each frame."""
        if agent.detected_enemies:
            self._hunt_enemy(agent, dt)
        else:
            self._patrol(agent, dt)

    def _hunt_enemy(self, agent, dt: float) -> None:
        """Hunt the closest enemy."""
        closest_id = agent.get_closest_enemy()
        if not closest_id:
            return

        enemy = agent.agents_dict[closest_id]
        
        agent.move_towards(dt, enemy.state.x, enemy.state.y)
        agent.point_gun_at(enemy.state.x, enemy.state.y)
        
        dx = enemy.state.x - agent.state.x
        dy = enemy.state.y - agent.state.y
        distance = math.sqrt(dx * dx + dy * dy)
        
        if distance < 200:
            agent.load_bullet()

    def _patrol(self, agent, dt: float) -> None:
        """Patrol randomly when no enemies detected."""
        self.patrol_timer += dt
        
        if self.patrol_timer >= 3.0:
            import random
            self.patrol_direction = random.choice(list(Direction))
            self.patrol_timer = 0.0
        
        agent.move(dt, self.patrol_direction)

Part 3: Register Your Strategy

Add to server/config.py:

python
from server.strategy.hunt_strategy import HuntStrategy

TEAM_A_SPAWNS = [
    (160.0, 120.0, "hunt"),
    (160.0, 360.0, "random"),
]

Update GameManager.spawn_test_agents() strategy map:

python
strategy_map = {
    "random": RandomStrategy,
    "hunt": HuntStrategy,
}

Part 4: Key Points to Remember

✅ Shooting - Call agent.load_bullet() once when you want to shoot. The agent automatically handles the cooldown timer and fires when ready.

✅ Detection - Enemy detection happens automatically. The agent.detected_enemies set is always available.

✅ Direction - Use Direction enum values: NORTH, SOUTH, EAST, WEST, NORTH_EAST, SOUTH_EAST, SOUTH_WEST, NORTH_WEST

✅ Mix Strategies - Combine different strategies in spawn config to test interactions between defensive, hunting, and random agents.
Example: Defensive Strategy

python
class DefensiveStrategy(Strategy):
    """Stay near spawn and shoot at distance."""

    def __init__(self, spawn_x: float, spawn_y: float) -> None:
        self.spawn_x = spawn_x
        self.spawn_y = spawn_y
        self.DEFEND_RANGE = 150

    def execute(self, agent, dt: float) -> None:
        if agent.detected_enemies:
            closest_id = agent.get_closest_enemy()
            if closest_id:
                enemy = agent.agents_dict[closest_id]
                agent.point_gun_at(enemy.state.x, enemy.state.y)
                agent.load_bullet()

        dx = self.spawn_x - agent.state.x
        dy = self.spawn_y - agent.state.y
        distance = math.sqrt(dx * dx + dy * dy)
        
        if distance > self.DEFEND_RANGE:
            agent.move_towards(dt, self.spawn_x, self.spawn_y)
