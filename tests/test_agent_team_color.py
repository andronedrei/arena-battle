import unittest
from src.server.gameplay.agent import Agent
from src.common.states.state_walls import StateWalls
from src.server.strategy.base import Strategy
from src.common.states.state_entity import Team


class MockStrategy(Strategy):
    def execute(self, agent, dt):
        pass


class TestAgentTeamColor(unittest.TestCase):
    def test_team_color_assignment(self):
        """Test if the agent's team color is assigned correctly."""
        walls_state = StateWalls(grid_unit=10, world_width=100, world_height=100)
        agents_dict = {}
        bullets_dict = {}
        strategy = MockStrategy()

        # Create agents for different teams
        agent_team_1 = Agent(
            walls_state=walls_state,
            agents_dict=agents_dict,
            bullets_dict=bullets_dict,
            strategy=strategy,
            team=Team.TEAM_A,
        )
        agent_team_2 = Agent(
            walls_state=walls_state,
            agents_dict=agents_dict,
            bullets_dict=bullets_dict,
            strategy=strategy,
            team=Team.TEAM_B,
        )
        agent_team_neutral = Agent(
            walls_state=walls_state,
            agents_dict=agents_dict,
            bullets_dict=bullets_dict,
            strategy=strategy,
            team=Team.NEUTRAL,
        )

        # Check team colors
        self.assertEqual(agent_team_1.state.team, Team.TEAM_A)
        self.assertEqual(agent_team_2.state.team, Team.TEAM_B)
        self.assertEqual(agent_team_neutral.state.team, Team.NEUTRAL)

if __name__ == "__main__":
    unittest.main()