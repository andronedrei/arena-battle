"""
KOTH Game Manager - DEBUG VERSION with extensive logging.

This version adds comprehensive logging to help identify why scoring doesn't work.
"""

import math
from typing import Optional

from common.config import LOGICAL_SCREEN_WIDTH, LOGICAL_SCREEN_HEIGHT, GRID_UNIT
from common.states.state_entity import Team
from common.states.state_walls import StateWalls
from server.gameplay.agent import Agent
from server.gameplay.bullet import Bullet
from server.gameplay.collision import find_bullet_agent_collisions, find_bullet_wall_collisions
from server.config import DETECTION_INTERVAL, TEAM_A_SPAWNS_KOTH, TEAM_B_SPAWNS_KOTH

# Import KOTH configuration
from common.koth_config import (
    KOTH_ZONE_CENTER_X,
    KOTH_ZONE_CENTER_Y,
    KOTH_ZONE_RADIUS,
    KOTH_ZONE_RECT_X,
    KOTH_ZONE_RECT_Y,
    KOTH_ZONE_RECT_WIDTH,
    KOTH_ZONE_RECT_HEIGHT,
    KOTH_ZONE_SHAPE,
    KOTH_POINTS_PER_SECOND,
    KOTH_SCORING_INTERVAL,
    KOTH_CONTESTED_BLOCKS_SCORING,
    KOTH_MAX_POINTS,
    KOTH_MAX_DURATION,
)
from common.states.state_koth import StateKOTH, KOTHZoneStatus
from common.logger import get_logger

logger = get_logger(__name__)


class GameManagerKOTH:
    """
    Server-side KOTH game manager - DEBUG VERSION.
    
    Extends base game logic with zone control, scoring, and win conditions.
    """
    
    def __init__(self, wall_config_file: str) -> None:
        """
        Initialize KOTH game manager.
        
        Args:
            wall_config_file: Path to walls configuration file.
        """
        logger.info("=" * 80)
        logger.info("INITIALIZING GameManagerKOTH - DEBUG VERSION")
        logger.info("=" * 80)
        
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
        
        # KOTH-specific state
        self.koth_state = StateKOTH()
        self.scoring_timer = 0.0
        
        # Debug counters
        self.debug_update_count = 0
        self.debug_zone_checks = 0
        self.debug_scoring_attempts = 0
        
        logger.info(f"Zone config: shape={KOTH_ZONE_SHAPE}, center=({KOTH_ZONE_CENTER_X}, {KOTH_ZONE_CENTER_Y})")
        if KOTH_ZONE_SHAPE == "circle":
            logger.info(f"  Circle radius={KOTH_ZONE_RADIUS}")
        else:
            logger.info(f"  Rectangle: ({KOTH_ZONE_RECT_X}, {KOTH_ZONE_RECT_Y}) size=({KOTH_ZONE_RECT_WIDTH}x{KOTH_ZONE_RECT_HEIGHT})")
        logger.info(f"Scoring: {KOTH_POINTS_PER_SECOND} pts/sec, interval={KOTH_SCORING_INTERVAL}s")
        logger.info(f"Win conditions: {KOTH_MAX_POINTS} points OR {KOTH_MAX_DURATION}s")
        logger.info("=" * 80)
        
    # Zone geometry
    
    def is_agent_in_zone(self, agent: Agent) -> bool:
        """
        Check if agent is inside the hill zone.
        
        Args:
            agent: Agent to check.
        
        Returns:
            True if agent is in zone, False otherwise.
        """
        if KOTH_ZONE_SHAPE == "circle":
            dx = agent.state.x - KOTH_ZONE_CENTER_X
            dy = agent.state.y - KOTH_ZONE_CENTER_Y
            distance_sq = dx * dx + dy * dy
            in_zone = distance_sq <= KOTH_ZONE_RADIUS * KOTH_ZONE_RADIUS
            
            # Debug logging every 100 checks
            if self.debug_zone_checks % 100 == 0:
                distance = math.sqrt(distance_sq)
                logger.debug(f"Agent {agent.state.id_entity} at ({agent.state.x:.1f}, {agent.state.y:.1f}), distance={distance:.1f}, in_zone={in_zone}")
            self.debug_zone_checks += 1
            
            return in_zone
        
        elif KOTH_ZONE_SHAPE == "rectangle":
            in_zone = (
                KOTH_ZONE_RECT_X <= agent.state.x <= KOTH_ZONE_RECT_X + KOTH_ZONE_RECT_WIDTH
                and KOTH_ZONE_RECT_Y <= agent.state.y <= KOTH_ZONE_RECT_Y + KOTH_ZONE_RECT_HEIGHT
            )
            return in_zone
        
        return False
    
    # Zone control logic
    
    def update_zone_control(self) -> None:
        """
        Determine current zone control status.
        
        Updates koth_state.zone_status based on which teams have agents in zone.
        """
        team_a_count = 0
        team_b_count = 0
        
        team_a_agents = []
        team_b_agents = []
        
        logger.debug(f"[Tick {self.tick_count}] Checking zone control, total agents={len(self.agents)}")
        
        for agent in self.agents.values():
            if not agent.is_alive():
                continue
            
            if self.is_agent_in_zone(agent):
                if agent.state.team == Team.TEAM_A:
                    team_a_count += 1
                    team_a_agents.append(agent.state.id_entity)
                elif agent.state.team == Team.TEAM_B:
                    team_b_count += 1
                    team_b_agents.append(agent.state.id_entity)
        
        # Determine zone status
        old_status = self.koth_state.zone_status
        
        if team_a_count > 0 and team_b_count > 0:
            self.koth_state.zone_status = KOTHZoneStatus.CONTESTED
        elif team_a_count > 0:
            self.koth_state.zone_status = KOTHZoneStatus.TEAM_A
        elif team_b_count > 0:
            self.koth_state.zone_status = KOTHZoneStatus.TEAM_B
        else:
            self.koth_state.zone_status = KOTHZoneStatus.NEUTRAL
        
        # Log zone status changes or every 60 ticks
        if old_status != self.koth_state.zone_status or self.tick_count % 60 == 0:
            status_names = {0: "NEUTRAL", 1: "TEAM_A", 2: "TEAM_B", 3: "CONTESTED"}
            logger.info(f"[Tick {self.tick_count}] Zone status: {status_names[self.koth_state.zone_status]} (Team A: {team_a_count} agents {team_a_agents}, Team B: {team_b_count} agents {team_b_agents})")
    
    # Scoring
    
    def update_scoring(self, dt: float) -> None:
        """
        Update team scores based on zone control - FIXED VERSION.
        
        Awards points at intervals defined by KOTH_SCORING_INTERVAL.
        
        Args:
            dt: Delta time in seconds.
        """
        self.scoring_timer += dt
        
        # Log scoring state every 60 ticks
        if self.tick_count % 60 == 0:
            logger.info(f"[Tick {self.tick_count}] Scoring timer: {self.scoring_timer:.3f}s, Team A: {self.koth_state.team_a_score:.1f}, Team B: {self.koth_state.team_b_score:.1f}")
        
        while self.scoring_timer >= KOTH_SCORING_INTERVAL:
            self.scoring_timer -= KOTH_SCORING_INTERVAL
            self.debug_scoring_attempts += 1
            
            # Award points based on zone control
            if self.koth_state.zone_status == KOTHZoneStatus.TEAM_A:
                points = KOTH_POINTS_PER_SECOND * KOTH_SCORING_INTERVAL
                self.koth_state.team_a_score += points
                logger.info(f"[Tick {self.tick_count}] ✅ TEAM A SCORED {points:.1f} points! Total: {self.koth_state.team_a_score:.1f}")
            
            elif self.koth_state.zone_status == KOTHZoneStatus.TEAM_B:
                points = KOTH_POINTS_PER_SECOND * KOTH_SCORING_INTERVAL
                self.koth_state.team_b_score += points
                logger.info(f"[Tick {self.tick_count}] ✅ TEAM B SCORED {points:.1f} points! Total: {self.koth_state.team_b_score:.1f}")
            
            elif self.koth_state.zone_status == KOTHZoneStatus.CONTESTED:
                logger.debug(f"[Tick {self.tick_count}] Zone CONTESTED - no points awarded")
                if not KOTH_CONTESTED_BLOCKS_SCORING:
                    pass
            else:
                logger.debug(f"[Tick {self.tick_count}] Zone NEUTRAL - no points awarded")
    
    # Win conditions
    
    def check_win_condition(self) -> Optional[int]:
        """
        Check if game has been won.
        
        Returns:
            Winning team ID (Team.TEAM_A or Team.TEAM_B) or None if ongoing.
        """
        # Check point limit
        if self.koth_state.team_a_score >= KOTH_MAX_POINTS:
            logger.info(f"🏆 TEAM A WINS by points! ({self.koth_state.team_a_score:.1f} >= {KOTH_MAX_POINTS})")
            return Team.TEAM_A
        if self.koth_state.team_b_score >= KOTH_MAX_POINTS:
            logger.info(f"🏆 TEAM B WINS by points! ({self.koth_state.team_b_score:.1f} >= {KOTH_MAX_POINTS})")
            return Team.TEAM_B
        
        # Check time limit
        if KOTH_MAX_DURATION > 0 and self.koth_state.time_elapsed >= KOTH_MAX_DURATION:
            logger.info(f"⏱️  TIME LIMIT REACHED ({self.koth_state.time_elapsed:.1f}s >= {KOTH_MAX_DURATION}s)")
            # Team with higher score wins
            if self.koth_state.team_a_score > self.koth_state.team_b_score:
                logger.info(f"🏆 TEAM A WINS by time! ({self.koth_state.team_a_score:.1f} > {self.koth_state.team_b_score:.1f})")
                return Team.TEAM_A
            elif self.koth_state.team_b_score > self.koth_state.team_a_score:
                logger.info(f"🏆 TEAM B WINS by time! ({self.koth_state.team_b_score:.1f} > {self.koth_state.team_a_score:.1f})")
                return Team.TEAM_B
            else:
                logger.info(f"🤝 DRAW! Both teams have {self.koth_state.team_a_score:.1f} points")
                return Team.NEUTRAL
        
        return None
    
    # Game loop
    
    def spawn_test_agents(self) -> None:
        """Spawn agents for both teams using KOTH-specific spawn points."""
        logger.info("Spawning KOTH agents...")
        
        # Spawn Team A with KOTH strategy
        team_a_count = 0
        for x, y, strategy_class in TEAM_A_SPAWNS_KOTH:
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
            team_a_count += 1
        
        # Spawn Team B with KOTH strategy
        team_b_count = 0
        for x, y, strategy_class in TEAM_B_SPAWNS_KOTH:
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
            team_b_count += 1
        
        logger.info(f"✅ Spawned {team_a_count} Team A agents and {team_b_count} Team B agents")
        logger.info(f"Total agents in game: {len(self.agents)}")
    
    def update(self, dt: float) -> None:
        """
        Execute single KOTH simulation tick.
        
        Updates bullets, agents, zone control, scoring, and checks win condition.
        
        Args:
            dt: Delta time in seconds.
        """
        self.debug_update_count += 1
        
        # Log game state every 60 ticks
        if self.tick_count % 60 == 0:
            logger.info(f"[Tick {self.tick_count}] Game state: time={self.koth_state.time_elapsed:.1f}s, game_over={self.koth_state.game_over}, agents={len(self.agents)}")
        
        # Update game timer
        if not self.koth_state.game_over:
            self.koth_state.time_elapsed += dt
        else:
            logger.warning(f"[Tick {self.tick_count}] Game is OVER! time_elapsed not updating.")
        
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
        
        # Remove dead agents
        dead_agents = [
            aid for aid, agent in self.agents.items()
            if not agent.is_alive()
        ]
        for aid in dead_agents:
            logger.info(f"[Tick {self.tick_count}] Agent {aid} died")
            for other_agent in self.agents.values():
                other_agent.detected_enemies.discard(aid)
            del self.agents[aid]
        
        # KOTH-specific updates
        if not self.koth_state.game_over:
            self.update_zone_control()
            self.update_scoring(dt)
            
            # Check win condition
            winner = self.check_win_condition()
            if winner is not None:
                logger.info(f"🎉 GAME OVER! Winner: {winner}")
                self.koth_state.game_over = True
                self.koth_state.winner_team = winner
                self.is_running = False
        else:
            if self.tick_count % 60 == 0:
                logger.warning(f"[Tick {self.tick_count}] Game is already over, skipping KOTH updates")
        
        self.tick_count += 1