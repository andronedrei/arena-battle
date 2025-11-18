"""
CTF Game Manager - Server-side implementation.

Manages flag states, captures, scoring, and win conditions for Capture the Flag mode.
"""

import math
from typing import Optional
from enum import IntEnum

from common.config import LOGICAL_SCREEN_WIDTH, LOGICAL_SCREEN_HEIGHT, GRID_UNIT
from common.states.state_entity import Team
from common.states.state_walls import StateWalls
from server.gameplay.agent import Agent
from server.gameplay.bullet import Bullet
from server.gameplay.collision import find_bullet_agent_collisions, find_bullet_wall_collisions
from server.config import DETECTION_INTERVAL
from common.logger import get_logger

# Import CTF configuration
from common.ctf_config import (
    CTF_FLAG_TEAM_A_BASE_X,
    CTF_FLAG_TEAM_A_BASE_Y,
    CTF_FLAG_TEAM_B_BASE_X,
    CTF_FLAG_TEAM_B_BASE_Y,
    CTF_FLAG_PICKUP_RADIUS,
    CTF_FLAG_RETURN_RADIUS,
    CTF_POINTS_PER_CAPTURE,
    CTF_FLAG_DROPS_ON_DEATH,
    CTF_FLAG_AUTO_RETURN_TIME,
    CTF_MAX_CAPTURES,
    CTF_MAX_DURATION,
)

logger = get_logger(__name__)


class FlagState(IntEnum):
    """Flag status enumeration."""
    AT_BASE = 0
    CARRIED = 1
    DROPPED = 2


class CTFFlag:
    """
    Represents a single CTF flag.
    
    Tracks position, state, and carrier information.
    """
    
    def __init__(
        self,
        team: int,
        base_x: float,
        base_y: float,
    ) -> None:
        """
        Initialize flag.
        
        Args:
            team: Team that owns this flag (Team.TEAM_A or Team.TEAM_B).
            base_x: Base X position.
            base_y: Base Y position.
        """
        self.team = team
        self.base_x = base_x
        self.base_y = base_y
        self.x = base_x
        self.y = base_y
        self.state = FlagState.AT_BASE
        self.carrier_id: Optional[int] = None
        self.drop_timer = 0.0  # Time since flag was dropped
    
    def reset_to_base(self) -> None:
        """Return flag to its base."""
        self.x = self.base_x
        self.y = self.base_y
        self.state = FlagState.AT_BASE
        self.carrier_id = None
        self.drop_timer = 0.0
        logger.info(f"Flag team {self.team} returned to base")
    
    def pickup(self, agent_id: int, agent_x: float, agent_y: float) -> None:
        """
        Flag picked up by agent.
        
        Args:
            agent_id: ID of agent picking up flag.
            agent_x: Agent X position.
            agent_y: Agent Y position.
        """
        self.state = FlagState.CARRIED
        self.carrier_id = agent_id
        self.x = agent_x
        self.y = agent_y
        self.drop_timer = 0.0
        logger.info(f"Flag team {self.team} picked up by agent #{agent_id}")
    
    def drop(self, x: float, y: float) -> None:
        """
        Drop flag at position.
        
        Args:
            x: Drop X position.
            y: Drop Y position.
        """
        self.state = FlagState.DROPPED
        self.carrier_id = None
        self.x = x
        self.y = y
        self.drop_timer = 0.0
        logger.info(f"Flag team {self.team} dropped at ({x:.1f}, {y:.1f})")
    
    def update_carrier_position(self, x: float, y: float) -> None:
        """Update flag position to carrier's position."""
        if self.state == FlagState.CARRIED:
            self.x = x
            self.y = y
    
    def update_drop_timer(self, dt: float) -> bool:
        """
        Update drop timer.
        
        Args:
            dt: Delta time.
        
        Returns:
            True if flag should auto-return.
        """
        if self.state == FlagState.DROPPED:
            self.drop_timer += dt
            if CTF_FLAG_AUTO_RETURN_TIME > 0 and self.drop_timer >= CTF_FLAG_AUTO_RETURN_TIME:
                return True
        return False


class GameManagerCTF:
    """
    Server-side CTF game manager.
    
    Manages flags, captures, scoring, and win conditions.
    """
    
    def __init__(self, wall_config_file: str) -> None:
        """
        Initialize CTF game manager.
        
        Args:
            wall_config_file: Path to walls configuration file.
        """
        # World state
        self.walls_state = StateWalls(
            grid_unit=GRID_UNIT,
            world_width=LOGICAL_SCREEN_WIDTH,
            world_height=LOGICAL_SCREEN_HEIGHT,
        )
        self.walls_state.load_from_file(wall_config_file)
        
        # Game entities
        self.agents: dict[int, Agent] = {}
        self.bullets: dict[int, Bullet] = {}
        self.tick_count = 0
        self.is_running = False
        
        # CTF-specific state
        self.flag_team_a = CTFFlag(Team.TEAM_A, CTF_FLAG_TEAM_A_BASE_X, CTF_FLAG_TEAM_A_BASE_Y)
        self.flag_team_b = CTFFlag(Team.TEAM_B, CTF_FLAG_TEAM_B_BASE_X, CTF_FLAG_TEAM_B_BASE_Y)
        
        # Compatibility aliases for network manager
        self.team_a_flag = self.flag_team_a
        self.team_b_flag = self.flag_team_b
        self.team_a_score = 0
        self.team_b_score = 0
        self.time_remaining = CTF_MAX_DURATION
        
        self.team_a_captures = 0
        self.team_b_captures = 0
        self.time_elapsed = 0.0
        self.game_over = False
        self.winner_team = 0
    
    # Flag logic
    
    def update_flags(self, dt: float) -> None:
        """
        Update flag states and check interactions.
        
        Args:
            dt: Delta time in seconds.
        """
        # Update flag positions for carriers
        for flag in [self.flag_team_a, self.flag_team_b]:
            if flag.state == FlagState.CARRIED and flag.carrier_id is not None:
                if flag.carrier_id in self.agents:
                    carrier = self.agents[flag.carrier_id]
                    flag.update_carrier_position(carrier.state.x, carrier.state.y)
                else:
                    # Carrier no longer exists - drop flag
                    flag.drop(flag.x, flag.y)
        
        # Check for flag pickups and captures
        for agent in self.agents.values():
            if not agent.is_alive():
                continue
            
            # Check if agent can pick up enemy flag
            enemy_flag = self.flag_team_b if agent.state.team == Team.TEAM_A else self.flag_team_a
            
            if enemy_flag.state != FlagState.CARRIED:
                dx = agent.state.x - enemy_flag.x
                dy = agent.state.y - enemy_flag.y
                distance = math.sqrt(dx * dx + dy * dy)
                
                if distance <= CTF_FLAG_PICKUP_RADIUS:
                    enemy_flag.pickup(agent.state.id_entity, agent.state.x, agent.state.y)
            
            # Check if carrier can capture flag
            if enemy_flag.carrier_id == agent.state.id_entity:
                # Get own flag status
                own_flag = self.flag_team_a if agent.state.team == Team.TEAM_A else self.flag_team_b
                
                # CRITICAL: Can only capture if own flag is at base!
                if own_flag.state != FlagState.AT_BASE:
                    # Own flag is taken or dropped - cannot capture yet
                    continue
                
                # Check if agent is in their own base
                own_base_x = CTF_FLAG_TEAM_A_BASE_X if agent.state.team == Team.TEAM_A else CTF_FLAG_TEAM_B_BASE_X
                own_base_y = CTF_FLAG_TEAM_A_BASE_Y if agent.state.team == Team.TEAM_A else CTF_FLAG_TEAM_B_BASE_Y
                
                dx = agent.state.x - own_base_x
                dy = agent.state.y - own_base_y
                distance = math.sqrt(dx * dx + dy * dy)
                
                # Debug: log carrier position relative to base
                if self.tick_count % 60 == 0:  # Every second
                    team_name = "A" if agent.state.team == Team.TEAM_A else "B"
                    logger.debug(f"Carrier (Team {team_name}) distance to base: {distance:.1f} (need <={CTF_FLAG_RETURN_RADIUS})")
                
                if distance <= CTF_FLAG_RETURN_RADIUS:
                    # CAPTURE!
                    self._capture_flag(agent.state.team, enemy_flag)
            
            # Check if agent can return their own flag
            own_flag = self.flag_team_a if agent.state.team == Team.TEAM_A else self.flag_team_b
            
            if own_flag.state == FlagState.DROPPED:
                dx = agent.state.x - own_flag.x
                dy = agent.state.y - own_flag.y
                distance = math.sqrt(dx * dx + dy * dy)
                
                if distance <= CTF_FLAG_PICKUP_RADIUS:
                    # Return flag to base
                    own_flag.reset_to_base()
                    logger.info(f"Agent #{agent.state.id_entity} returned their flag to base")
        
        # Check for flag auto-return
        if self.flag_team_a.update_drop_timer(dt):
            self.flag_team_a.reset_to_base()
        
        if self.flag_team_b.update_drop_timer(dt):
            self.flag_team_b.reset_to_base()
    
    def _capture_flag(self, team: int, flag: CTFFlag) -> None:
        """
        Handle flag capture.
        
        Args:
            team: Team that captured the flag.
            flag: Flag that was captured.
        """
        if team == Team.TEAM_A:
            self.team_a_captures += CTF_POINTS_PER_CAPTURE
            logger.info(f"TEAM A captured flag! Score: {self.team_a_captures}/{CTF_MAX_CAPTURES}")
        else:
            self.team_b_captures += CTF_POINTS_PER_CAPTURE
            logger.info(f"TEAM B captured flag! Score: {self.team_b_captures}/{CTF_MAX_CAPTURES}")
        
        # Reset flag to base
        flag.reset_to_base()
    
    def handle_agent_death(self, agent_id: int, agent_team: int, agent_x: float, agent_y: float) -> None:
        """
        Handle flag drop when carrier dies.
        
        Args:
            agent_id: ID of dead agent.
            agent_team: Team of dead agent.
            agent_x: X position where agent died.
            agent_y: Y position where agent died.
        """
        if not CTF_FLAG_DROPS_ON_DEATH:
            return
        
        # Check if agent was carrying a flag
        enemy_flag = self.flag_team_b if agent_team == Team.TEAM_A else self.flag_team_a
        
        if enemy_flag.carrier_id == agent_id:
            enemy_flag.drop(agent_x, agent_y)
    
    # Win conditions
    
    def check_win_condition(self) -> Optional[int]:
        """
        Check if game has been won.
        
        Returns:
            Winning team ID (Team.TEAM_A or Team.TEAM_B) or None if ongoing.
        """
        # Check if all agents are dead - log warning
        alive_agents = sum(1 for agent in self.agents.values() if agent.is_alive())
        if alive_agents == 0 and len(self.agents) == 0:
            logger.warning("No agents alive in CTF game - this may cause freeze")
        
        # Check capture limit
        if self.team_a_captures >= CTF_MAX_CAPTURES:
            logger.info(f"Team A wins by captures: {self.team_a_captures}/{CTF_MAX_CAPTURES}")
            return Team.TEAM_A
        if self.team_b_captures >= CTF_MAX_CAPTURES:
            logger.info(f"Team B wins by captures: {self.team_b_captures}/{CTF_MAX_CAPTURES}")
            return Team.TEAM_B
        
        # Check time limit
        if CTF_MAX_DURATION > 0 and self.time_elapsed >= CTF_MAX_DURATION:
            logger.info(f"Time expired! Final score: A={self.team_a_captures}, B={self.team_b_captures}")
            # Team with more captures wins
            if self.team_a_captures > self.team_b_captures:
                return Team.TEAM_A
            elif self.team_b_captures > self.team_a_captures:
                return Team.TEAM_B
            else:
                # Tie
                logger.info("Game ended in a tie")
                return Team.NEUTRAL
        
        return None
    
    # Game loop
    
    def spawn_test_agents(self) -> None:
        """Spawn agents for both teams using CTF-specific spawn points."""
        from server.config import TEAM_A_SPAWNS_CTF, TEAM_B_SPAWNS_CTF
        
        logger.info("=" * 60)
        logger.info("🚀 STARTING CTF AGENT SPAWN")
        logger.info(f"Team A spawn points: {len(TEAM_A_SPAWNS_CTF)}")
        logger.info(f"Team B spawn points: {len(TEAM_B_SPAWNS_CTF)}")
        logger.info("=" * 60)
        
        # Spawn Team A with CTF strategy
        team_a_count = 0
        for x, y, strategy_class in TEAM_A_SPAWNS_CTF:
            agent = Agent(
                walls_state=self.walls_state,
                agents_dict=self.agents,
                bullets_dict=self.bullets,
                strategy=strategy_class(self),  # Pass game manager to strategy
                x=x,
                y=y,
                team=Team.TEAM_A,
            )
            self.agents[agent.state.id_entity] = agent
            team_a_count += 1
            logger.info(f"✅ Spawned Team A agent #{agent.state.id_entity} at ({x}, {y})")
        
        # Spawn Team B with CTF strategy
        team_b_count = 0
        for x, y, strategy_class in TEAM_B_SPAWNS_CTF:
            agent = Agent(
                walls_state=self.walls_state,
                agents_dict=self.agents,
                bullets_dict=self.bullets,
                strategy=strategy_class(self),  # Pass game manager to strategy
                x=x,
                y=y,
                team=Team.TEAM_B,
            )
            self.agents[agent.state.id_entity] = agent
            team_b_count += 1
            logger.info(f"✅ Spawned Team B agent #{agent.state.id_entity} at ({x}, {y})")
        
        logger.info("=" * 60)
        logger.info(f"✅ CTF SPAWN COMPLETE: {team_a_count} Team A + {team_b_count} Team B = {len(self.agents)} total")
        logger.info("=" * 60)
    
    def update(self, dt: float) -> None:
        """
        Execute single CTF simulation tick.
        
        Updates bullets, agents, flags, and checks win condition.
        
        Args:
            dt: Delta time in seconds.
        """
        # Update game timer
        if not self.game_over:
            self.time_elapsed += dt
            # Update time remaining for network broadcast
            self.time_remaining = max(0.0, CTF_MAX_DURATION - self.time_elapsed)
            # Sync score aliases with capture counts
            self.team_a_score = self.team_a_captures
            self.team_b_score = self.team_b_captures
        
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
        
        # Update agents
        for agent in self.agents.values():
            agent.update_strategy(dt)
        
        # Periodic enemy detection
        if self.tick_count % DETECTION_INTERVAL == 0:
            for agent in self.agents.values():
                agent.detect_enemies()
        
        # Check bullet-agent collisions
        bullet_hits = find_bullet_agent_collisions(self.bullets, self.agents)
        for bullet_id, hit_agents in bullet_hits.items():
            if not hit_agents or bullet_id not in self.bullets:
                continue
            
            bullet = self.bullets[bullet_id]
            for agent_id in hit_agents:
                if agent_id in self.agents:
                    self.agents[agent_id].take_damage(bullet.damage)
            
            del self.bullets[bullet_id]
        
        # Check bullet-wall collisions
        destroyed_bullets = find_bullet_wall_collisions(self.bullets, self.walls_state)
        for bullet_id in destroyed_bullets:
            if bullet_id in self.bullets:
                del self.bullets[bullet_id]
        
        # Handle dead agents (drop flags if carrying)
        dead_agents = [
            aid for aid, agent in self.agents.items()
            if not agent.is_alive()
        ]
        for aid in dead_agents:
            agent = self.agents[aid]
            self.handle_agent_death(aid, agent.state.team, agent.state.x, agent.state.y)
            
            # Clean up references
            for other_agent in self.agents.values():
                other_agent.detected_enemies.discard(aid)
            
            del self.agents[aid]
        
        # CTF-specific updates
        if not self.game_over:
            self.update_flags(dt)
            
            # Periodic logging (every 5 seconds)
            if self.tick_count % 300 == 0:  # 60 FPS * 5 seconds
                alive_count = sum(1 for agent in self.agents.values() if agent.is_alive())
                logger.info(f"CTF status: time={self.time_elapsed:.1f}s, agents={alive_count}, A={self.team_a_captures}, B={self.team_b_captures}")
            
            # Check win condition
            winner = self.check_win_condition()
            if winner is not None:
                self.game_over = True
                self.winner_team = winner
                self.is_running = False
                logger.info(f"CTF game over! Winner: Team {winner}")
        
        self.tick_count += 1
    
    def get_ctf_state(self) -> dict:
        """
        Get current CTF state for network broadcast.
        
        Returns:
            Dictionary with CTF state information.
        """
        return {
            "team_a_captures": self.team_a_captures,
            "team_b_captures": self.team_b_captures,
            "time_remaining": max(0.0, CTF_MAX_DURATION - self.time_elapsed),
            "game_over": self.game_over,
            "winner_team": self.winner_team,
            "flag_team_a": {
                "x": self.flag_team_a.x,
                "y": self.flag_team_a.y,
                "state": int(self.flag_team_a.state),
                "carrier_id": self.flag_team_a.carrier_id,
            },
            "flag_team_b": {
                "x": self.flag_team_b.x,
                "y": self.flag_team_b.y,
                "state": int(self.flag_team_b.state),
                "carrier_id": self.flag_team_b.carrier_id,
            }
        }
