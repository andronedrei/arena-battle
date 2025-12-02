import unittest
from src.server.gameplay.agent import Agent
from src.common.states.state_walls import StateWalls
from src.server.strategy.base import Strategy
from src.common.config import AMMO_INFINITE


class MockStrategy(Strategy):
    def execute(self, agent, dt):
        pass


class TestAgentShoot(unittest.TestCase):
    def test_agent_shooting(self):
        """Test if the agent shoots bullets with infinite ammo."""
        walls_state = StateWalls(grid_unit=10, world_width=100, world_height=100)
        agents_dict = {}
        bullets_dict = {}
        strategy = MockStrategy()

        # Create an agent with infinite ammo
        agent = Agent(
            walls_state=walls_state,
            agents_dict=agents_dict,
            bullets_dict=bullets_dict,
            strategy=strategy,
            ammo=AMMO_INFINITE,
        )

        # Test shooting with infinite ammo
        initial_ammo = agent.current_ammo
        agent.load_bullet()
        self.assertEqual(agent.current_ammo, initial_ammo)  # Ammo should remain infinite

if __name__ == "__main__":
    unittest.main()