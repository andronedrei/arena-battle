# Internal libraries
from common.config import (
    GRID_UNIT,
    LOGICAL_SCREEN_HEIGHT,
    LOGICAL_SCREEN_WIDTH,
)
from common.states.state_entity import Team
from common.states.state_walls import StateWalls
from server.config import (
    DETECTION_INTERVAL,
    TEAM_A_SPAWNS,
    TEAM_B_SPAWNS,
)
from server.gameplay.agent import Agent
from server.gameplay.bullet import Bullet
from server.gameplay.collision import (
    find_bullet_agent_collisions,
    find_bullet_wall_collisions,
)


class GameManager:
    """
    Server-side game simulation and state management.

    Responsibilities: update agent logic, manage enemy detection, handle
    bullet collisions, and expose entity states for network transmission.
    """

    # Initialization

    def __init__(self, wall_config_file: str) -> None:
        """
        Initialize game manager with world state.

        Args:
            wall_config_file: Path to walls configuration file.
        """
        self.walls_state = StateWalls(
            grid_unit=GRID_UNIT,
            world_width=LOGICAL_SCREEN_WIDTH,
            world_height=LOGICAL_SCREEN_HEIGHT,
        )
        self.walls_state.load_from_file(wall_config_file)

        self.agents: dict[int, Agent] = {}
        self.bullets: dict[int, Bullet] = {}
        self.tick_count = 0
        self.is_running = False
        # Winner team for the match (None while ongoing)
        self.winner_team = None

    # Agent management

    def spawn_test_agents(self) -> None:
        """Spawn agents with assigned strategies from configuration."""

        # Spawn Team A agents
        for x, y, strategy_class in TEAM_A_SPAWNS:
            agent = Agent(
                walls_state=self.walls_state,
                agents_dict=self.agents,
                bullets_dict=self.bullets,
                strategy=strategy_class(),
                x=x,
                y=y,
                team=Team.TEAM_A,
            )
            self.agents[agent.state.id_entity] = agent

        # Spawn Team B agents
        for x, y, strategy_class in TEAM_B_SPAWNS:
            agent = Agent(
                walls_state=self.walls_state,
                agents_dict=self.agents,
                bullets_dict=self.bullets,
                strategy=strategy_class(),
                x=x,
                y=y,
                team=Team.TEAM_B,
            )
            self.agents[agent.state.id_entity] = agent

    # Simulation

    def update(self, dt: float) -> None:
        """
        Execute single simulation tick.

        Updates bullets, checks collisions, runs agent strategies, and
        performs periodic detection. Cleans up expired entities.

        Args:
            dt: Delta time in seconds.
        """
        # Update bullets
        for bullet in self.bullets.values():
            bullet.update(dt)

        # Clean up expired bullets
        expired_bullets = [
            bid for bid, bullet in self.bullets.items()
            if not bullet.is_alive()
        ]
        for bid in expired_bullets:
            del self.bullets[bid]

        # Update all agents
        for agent in self.agents.values():
            agent.update_strategy(dt)

        # Periodic enemy detection
        if self.tick_count % DETECTION_INTERVAL == 0:
            for agent in self.agents.values():
                agent.detect_enemies()

        # Check bullet-agent collisions
        bullet_hits = find_bullet_agent_collisions(
            self.bullets, self.agents
        )
        for bullet_id, hit_agents in bullet_hits.items():
            if not hit_agents or bullet_id not in self.bullets:
                continue

            bullet = self.bullets[bullet_id]
            for agent_id in hit_agents:
                if agent_id in self.agents:
                    self.agents[agent_id].take_damage(bullet.damage)

            del self.bullets[bullet_id]

        # Check bullet-wall collisions
        destroyed_bullets = find_bullet_wall_collisions(
            self.bullets, self.walls_state
        )
        for bullet_id in destroyed_bullets:
            if bullet_id in self.bullets:
                del self.bullets[bullet_id]

        # Remove dead agents and clean up references
        dead_agents = [
            aid for aid, agent in self.agents.items()
            if not agent.is_alive()
        ]
        for aid in dead_agents:
            # Remove from other agents' detection lists
            for other_agent in self.agents.values():
                other_agent.detected_enemies.discard(aid)
            del self.agents[aid]

        # Check win condition: if only one team remains, mark winner and stop
        remaining_teams = set()
        for agent in self.agents.values():
            if agent.state.team is not None:
                remaining_teams.add(agent.state.team)

        # Filter out neutral/teamless markers if present (assume Team enum non-neutral values indicate teams)
        if len(remaining_teams) == 1:
            # single team left -> that team wins
            self.winner_team = remaining_teams.pop()
            # stop running to allow network manager to broadcast GAME_END
            self.is_running = False

        self.tick_count += 1
