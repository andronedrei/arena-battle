"""
KOTH Game Manager - Server-side implementation.

Manages zone control, scoring, and win conditions for King of the Hill mode.
"""

import math
from typing import Optional

from common.config import LOGICAL_SCREEN_WIDTH, LOGICAL_SCREEN_HEIGHT, GRID_UNIT
from common.states.state_entity import Team
from common.states.state_walls import StateWalls
from server.gameplay.agent import Agent
from server.gameplay.bullet import Bullet
from server.gameplay.collision import find_bullet_agent_collisions, find_bullet_wall_collisions
from server.config import DETECTION_INTERVAL, TEAM_A_SPAWNS, TEAM_B_SPAWNS

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


class GameManagerKOTH:
    """
    Server-side KOTH game manager.
    
    Extends base game logic with zone control, scoring, and win conditions.
    """
    
    def __init__(self, wall_config_file: str) -> None:
        """
        Initialize KOTH game manager.
        
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
        
        # KOTH-specific state
        self.koth_state = StateKOTH()
        self.scoring_timer = 0.0
        
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
            return distance_sq <= KOTH_ZONE_RADIUS * KOTH_ZONE_RADIUS
        
        elif KOTH_ZONE_SHAPE == "rectangle":
            return (
                KOTH_ZONE_RECT_X <= agent.state.x <= KOTH_ZONE_RECT_X + KOTH_ZONE_RECT_WIDTH
                and KOTH_ZONE_RECT_Y <= agent.state.y <= KOTH_ZONE_RECT_Y + KOTH_ZONE_RECT_HEIGHT
            )
        
        return False
    
    # Zone control logic
    
    def update_zone_control(self) -> None:
        """
        Determine current zone control status.
        
        Updates koth_state.zone_status based on which teams have agents in zone.
        """
        team_a_count = 0
        team_b_count = 0
        
        for agent in self.agents.values():
            if not agent.is_alive():
                continue
            
            if self.is_agent_in_zone(agent):
                if agent.state.team == Team.TEAM_A:
                    team_a_count += 1
                elif agent.state.team == Team.TEAM_B:
                    team_b_count += 1
        
        # Determine zone status
        if team_a_count > 0 and team_b_count > 0:
            self.koth_state.zone_status = KOTHZoneStatus.CONTESTED
        elif team_a_count > 0:
            self.koth_state.zone_status = KOTHZoneStatus.TEAM_A
        elif team_b_count > 0:
            self.koth_state.zone_status = KOTHZoneStatus.TEAM_B
        else:
            self.koth_state.zone_status = KOTHZoneStatus.NEUTRAL
    
    # Scoring
    
    def update_scoring(self, dt: float) -> None:
        """
        Update team scores based on zone control.
        
        Awards points at intervals defined by KOTH_SCORING_INTERVAL.
        
        Args:
            dt: Delta time in seconds.
        """
        self.scoring_timer += dt
        
        if self.scoring_timer >= KOTH_SCORING_INTERVAL:
            self.scoring_timer = 0.0
            
            # Award points based on zone control
            if self.koth_state.zone_status == KOTHZoneStatus.TEAM_A:
                points = KOTH_POINTS_PER_SECOND * KOTH_SCORING_INTERVAL
                self.koth_state.team_a_score += points
            
            elif self.koth_state.zone_status == KOTHZoneStatus.TEAM_B:
                points = KOTH_POINTS_PER_SECOND * KOTH_SCORING_INTERVAL
                self.koth_state.team_b_score += points
            
            elif self.koth_state.zone_status == KOTHZoneStatus.CONTESTED:
                # No points awarded if contested (based on config)
                if not KOTH_CONTESTED_BLOCKS_SCORING:
                    # Could implement majority-wins logic here if needed
                    pass
    
    # Win conditions
    
    def check_win_condition(self) -> Optional[int]:
        """
        Check if game has been won.
        
        Returns:
            Winning team ID (Team.TEAM_A or Team.TEAM_B) or None if ongoing.
        """
        # Check point limit
        if self.koth_state.team_a_score >= KOTH_MAX_POINTS:
            return Team.TEAM_A
        if self.koth_state.team_b_score >= KOTH_MAX_POINTS:
            return Team.TEAM_B
        
        # Check time limit
        if KOTH_MAX_DURATION > 0 and self.koth_state.time_elapsed >= KOTH_MAX_DURATION:
            # Team with higher score wins
            if self.koth_state.team_a_score > self.koth_state.team_b_score:
                return Team.TEAM_A
            elif self.koth_state.team_b_score > self.koth_state.team_a_score:
                return Team.TEAM_B
            else:
                # Tie - could implement tiebreaker logic here
                return Team.NEUTRAL
        
        return None
    
    # Game loop
    
    def spawn_test_agents(self) -> None:
        """Spawn agents for both teams."""
        # Spawn Team A
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
        
        # Spawn Team B
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
    
    def update(self, dt: float) -> None:
        """
        Execute single KOTH simulation tick.
        
        Updates bullets, agents, zone control, scoring, and checks win condition.
        
        Args:
            dt: Delta time in seconds.
        """
        # Update game timer
        if not self.koth_state.game_over:
            self.koth_state.time_elapsed += dt
        
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
                self.koth_state.game_over = True
                self.koth_state.winner_team = winner
                self.is_running = False
        
        self.tick_count += 1