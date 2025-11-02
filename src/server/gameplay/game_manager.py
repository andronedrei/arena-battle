"""
Server-side game simulation manager.
Handles agent updates, detection, and entity state management.
"""

from common.states.state_walls import StateWalls
from common.states.state_entity import StateEntity, Team
from server.gameplay.agent import Agent


# === AGENT CONFIGURATION ===
DETECTION_INTERVAL = 5  # Check enemies every Nth tick (reduces CPU)

# Test agent spawn positions
TEAM_A_SPAWN = (100.0, 100.0)
TEAM_B_SPAWN = (700.0, 500.0)

# Entity properties
DEFAULT_RADIUS = 23.0
DEFAULT_GUN_ROT_SPEED = 2 * 3.14 / 5  # Radians per second


class GameManager:
    """
    Server-side game simulation and state management.
    
    Responsibilities:
    - Update agent logic (movement, rotation, etc.)
    - Manage enemy detection at intervals
    - Expose entity states for network transmission
    """
    
    def __init__(self, walls_state: StateWalls):
        """
        Initialize game manager with world state.
        
        Args:
            walls_state: StateWalls instance containing collision geometry
        """
        self.walls_state = walls_state
        self.agents: dict[int, Agent] = {}
        
        # Simulation state
        self.tick_count = 0
        self.is_running = False
    
    def spawn_test_agents(self):
        """
        Create and register two test agents (MVP for 1v1).
        
        Teams:
        - Agent 0: TEAM_A at (100, 100)
        - Agent 1: TEAM_B at (700, 500)
        """
        # Team A agent
        entity_a = StateEntity(
            id_entity=0,
            x=TEAM_A_SPAWN[0],
            y=TEAM_A_SPAWN[1],
            radius=DEFAULT_RADIUS,
            team=Team.TEAM_A,
            gun_angle=0.0
        )
        agent_a = Agent(entity_a, self.walls_state)
        self.agents[0] = agent_a
        
        # Team B agent
        entity_b = StateEntity(
            id_entity=1,
            x=TEAM_B_SPAWN[0],
            y=TEAM_B_SPAWN[1],
            radius=DEFAULT_RADIUS,
            team=Team.TEAM_B,
            gun_angle=3.14
        )
        agent_b = Agent(entity_b, self.walls_state)
        self.agents[1] = agent_b
        
        print(f"[GAME] Spawned {len(self.agents)} agents")
    
    def update(self, dt: float):
        """
        Execute single simulation tick.
        
        Args:
            dt: Delta time in seconds since last update
        
        Operations:
        1. Update agent logic (rotation, movement, etc.)
        2. Run enemy detection periodically (every Nth tick)
        """
        # Update all agents
        for agent in self.agents.values():
            # Test behavior: slowly rotate gun
            agent.state.gun_angle += DEFAULT_GUN_ROT_SPEED * dt
        
        # Periodic detection (reduces raycasting CPU cost)
        if self.tick_count % DETECTION_INTERVAL == 0:
            for agent in self.agents.values():
                agent.detect_enemies(self.agents)
        
        self.tick_count += 1
    
    def get_entities_dict(self) -> dict[int, StateEntity]:
        """
        Get all entity states for network transmission.
        
        Returns:
            Dictionary mapping agent ID -> StateEntity
        """
        return {aid: agent.state for aid, agent in self.agents.items()}
