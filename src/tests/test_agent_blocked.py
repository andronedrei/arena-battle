import unittest
from src.server.gameplay.agent import Agent
from src.common.states.state_walls import StateWalls
from src.server.strategy.base import Strategy
from src.common.config import Direction
from src.server.gameplay.collision import CollisionType


class MockStrategy(Strategy):
    def execute(self, agent, dt):
        pass


class TestAgentBlocked(unittest.TestCase):
    def test_agent_blocked(self):
        """Test if the agent detects when it is blocked."""
        walls_state = StateWalls(grid_unit=10, world_width=100, world_height=100)
        agents_dict = {}
        bullets_dict = {}
        strategy = MockStrategy()

        agent = Agent(
            walls_state=walls_state,
            agents_dict=agents_dict,
            bullets_dict=bullets_dict,
            strategy=strategy,
            x=10.0,
            y=10.0,
        )

        # Simulate a blocking obstacle
        agent.blocked = (CollisionType.WALL, 1)
        self.assertTrue(agent.is_blocked())
        self.assertEqual(agent.blocked_by(), (CollisionType.WALL, 1))

        # Remove the block
        agent.blocked = None
        self.assertFalse(agent.is_blocked())
        self.assertIsNone(agent.blocked_by())

if __name__ == "__main__":
    unittest.main()