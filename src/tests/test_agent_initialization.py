import unittest
from src.server.gameplay.agent import Agent
from src.common.states.state_walls import StateWalls
from src.server.strategy.base import Strategy


class MockStrategy(Strategy):
    def execute(self, agent, dt):
        pass


class TestAgentInitialization(unittest.TestCase):
    def test_agent_initialization(self):
        """Test if the agent initializes with correct default values."""
        # Provide required arguments for StateWalls
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
            y=20.0,
            team=1,
        )

        self.assertEqual(agent.state.x, 10.0)
        self.assertEqual(agent.state.y, 20.0)
        self.assertEqual(agent.state.team, 1)

if __name__ == "__main__":
    unittest.main()