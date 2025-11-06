# server/gameplay/game_manager.py

from common.states.state_walls import StateWalls
from common.states.state_entity import StateEntity, Team
from server.gameplay.agent import Agent
from server.gameplay.bullet import Bullet
from server.gameplay.collision import find_bullet_agent_collisions, find_bullet_wall_collisions
from server.strategy.random_strategy import RandomStrategy


# === AGENT CONFIGURATION ===
DETECTION_INTERVAL = 5


# Test agent spawn positions
TEAM_A_SPAWN = (100.0, 100.0)
TEAM_B_SPAWN = (700.0, 500.0)


# Entity properties
DEFAULT_RADIUS = 23.0
DEFAULT_GUN_ROT_SPEED = 2 * 3.14 / 5


class GameManager:
    """
    Server-side game simulation and state management.
    
    Responsibilities:
    - Update agent logic (movement, rotation, etc.)
    - Manage enemy detection at intervals
    - Handle bullet collisions
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
        self.bullets: dict[int, Bullet] = {}
        
        # Simulation state
        self.tick_count = 0
        self.is_running = False

    def spawn_test_agents(self):
        """Create two test agents."""
        # Team A agent - left side, gun_angle auto-set to 0
        agent_a = Agent(
            walls_state=self.walls_state,
            agents_dict=self.agents,
            bullets_dict=self.bullets,
            strategy=RandomStrategy(),
            x=TEAM_A_SPAWN[0],
            y=TEAM_A_SPAWN[1],
            team=Team.TEAM_A,
            health=100.0,
            damage=25.0,
            speed=50.0,
            shoot_duration=1
        )
        
        # Team B agent - right side, gun_angle auto-set to π
        agent_b = Agent(
            walls_state=self.walls_state,
            agents_dict=self.agents,
            bullets_dict=self.bullets,
            strategy=RandomStrategy(),
            x=TEAM_B_SPAWN[0],
            y=TEAM_B_SPAWN[1],
            team=Team.TEAM_B,
            health=100.0,
            damage=25.0,
            speed=50.0,
            shoot_duration=1
        )
        
        self.agents[agent_a.state.id_entity] = agent_a
        self.agents[agent_b.state.id_entity] = agent_b
        
        print(f"[GAME] Spawned {len(self.agents)} agents")

    # server/gameplay/game_manager.py

    def update(self, dt: float):
        """Execute single simulation tick."""
        
        # Update bullets
        for bullet in self.bullets.values():
            bullet.update(dt)

        # Clean up expired bullets
        expired = [bid for bid, bullet in self.bullets.items() if not bullet.is_alive()]
        for bid in expired:
            del self.bullets[bid]

        # Update all agents strategy
        for agent in self.agents.values():
            agent.update_strategy(dt)

        # Periodic detection
        if self.tick_count % DETECTION_INTERVAL == 0:
            for agent in self.agents.values():
                agent.detect_enemies()

        print(f"[TICK {self.tick_count}] Bullets before collision: {len(self.bullets)}")

        # Check bullet collisions with agents
        bullet_hits = find_bullet_agent_collisions(self.bullets, self.agents)
        for bullet_id, hit_agents in bullet_hits.items():
            if len(hit_agents) == 0:
                continue
            
            if bullet_id not in self.bullets:
                continue
            
            bullet = self.bullets[bullet_id]
            
            for agent_id in hit_agents:
                if agent_id in self.agents:
                    agent = self.agents[agent_id]
                    agent.take_damage(bullet.damage)
                    print(f"[HIT] Agent {agent_id} health: {agent.health:.1f}")
            
            if bullet_id in self.bullets:
                del self.bullets[bullet_id]

        # Check bullet collisions with walls
        destroyed_bullets = find_bullet_wall_collisions(self.bullets, self.walls_state)
        for bullet_id in destroyed_bullets:
            if bullet_id in self.bullets:
                del self.bullets[bullet_id]

        # Remove dead agents - clean up references
        dead_agents = [aid for aid, agent in self.agents.items() if not agent.is_alive()]
        for aid in dead_agents:
            print(f"[DEAD] Agent {aid} eliminated")
            # Clear from other agents' detected_enemies first
            for other_agent in self.agents.values():
                other_agent.detected_enemies.discard(aid)
            del self.agents[aid]

        print(f"[TICK {self.tick_count}] Bullets after collision: {len(self.bullets)}\n")
        
        self.tick_count += 1

