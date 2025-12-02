import unittest
from src.server.gameplay.agent import Agent
from src.common.states.state_walls import StateWalls
from src.server.strategy.base import Strategy


class MockStrategy(Strategy):
    def execute(self, agent, dt):
        pass


class TestAgentHealth(unittest.TestCase):
    def test_agent_health_reduction(self):
        """Test if the agent's health decreases when taking damage."""
        walls_state = StateWalls(grid_unit=10, world_width=100, world_height=100)
        agents_dict = {}
        bullets_dict = {}
        strategy = MockStrategy()

        agent = Agent(
            walls_state=walls_state,
            agents_dict=agents_dict,
            bullets_dict=bullets_dict,
            strategy=strategy,
            health=100.0,
        )

        agent.take_damage(30.0)
        self.assertEqual(agent.health, 70.0)

        agent.take_damage(80.0)
        self.assertEqual(agent.health, 0.0)  # Health should not go below 0

if __name__ == "__main__":
    unittest.main()