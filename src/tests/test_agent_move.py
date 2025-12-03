import unittest
from src.server.gameplay.agent import Agent
from src.common.states.state_walls import StateWalls
from src.server.strategy.base import Strategy
from src.common.config import Direction


class MockStrategy(Strategy):
    def execute(self, agent, dt):
        pass


class TestAgentMove(unittest.TestCase):
    def test_agent_move(self):
        """Test if the agent moves correctly."""
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

        initial_position = (agent.state.x, agent.state.y)
        agent.move(1.0, Direction.NORTH)
        self.assertNotEqual((agent.state.x, agent.state.y), initial_position)

if __name__ == "__main__":
    unittest.main()