"""
CTF Base Defender Strategy - Specialized bot for base defense.

Primary role: Guard the base and protect the flag.
Fallback: If alone in team, becomes attacker to capture enemy flag.
"""

import random
import math

from server.strategy.base import Strategy
from common.config import Direction
from common.ctf_config import (
    CTF_FLAG_TEAM_A_BASE_X,
    CTF_FLAG_TEAM_A_BASE_Y,
    CTF_FLAG_TEAM_B_BASE_X,
    CTF_FLAG_TEAM_B_BASE_Y,
    CTF_FLAG_PICKUP_RADIUS,
    CTF_FLAG_RETURN_RADIUS,
)
from common.states.state_entity import Team
from common.logger import get_logger

logger = get_logger(__name__)


class CTFBaseDefenderStrategy(Strategy):
    """
    Dedicated base defender with fallback attacker behavior.
    
    Behavior:
    - Primary: Patrol and defend base area
    - If flag taken: Hunt the carrier aggressively
    - If flag dropped: Immediately return it
    - If alone in team: Switch to attacker mode and capture enemy flag
    """
    
    # Configuration
    BASE_PATROL_RADIUS = 120.0  # Patrol radius around base
    TIGHT_DEFENSE_RADIUS = 80.0  # Close defense when flag at base
    HUNTER_MODE_RADIUS = 400.0  # Max distance to chase carrier
    CHANGE_DIRECTION_INTERVAL = 0.6  # Patrol direction change interval
    LOW_HEALTH_THRESHOLD = 20.0  # When to play more defensively
    
    def __init__(self, game_manager) -> None:
        """
        Initialize base defender strategy.
        
        Args:
            game_manager: GameManagerCTF instance for accessing game state.
        """
        self.game_manager = game_manager
        self.direction_timer = 0.0
        self.patrol_direction = random.choice(list(Direction))
        # Simple stuck detection
        self._stuck_counter = 0
        self._last_position = None
        self._avoidance_timer = 0.0
        self._avoidance_direction = None
        self._is_alone = False  # Track if bot is alone in team
    
    def execute(self, agent, dt: float) -> None:
        """
        Execute base defender strategy.
        
        Args:
            agent: Agent instance to control.
            dt: Delta time in seconds.
        """
        # Always detect enemies
        agent.detect_enemies()
        
        # Check if we need to reload
        if agent.current_ammo == 0 and agent.reload_timer is None:
            agent.start_reload()
        
        # Check if agent is stuck and needs wall avoidance
        self._check_stuck(agent, dt)
        
        # Check if we're alone in the team
        self._check_if_alone(agent)
        
        # If alone, become attacker
        if self._is_alone:
            self._attacker_behavior(agent, dt)
        else:
            # Normal defender behavior
            self._defender_behavior(agent, dt)
        
        # Always engage enemies
        if agent.detected_enemies:
            self._combat(agent)
    
    def _check_if_alone(self, agent) -> None:
        """
        Check if this bot is the last one alive in its team.
        
        Args:
            agent: Agent instance.
        """
        teammates_alive = 0
        for other_agent in self.game_manager.agents.values():
            if other_agent.state.team == agent.state.team and other_agent.is_alive():
                teammates_alive += 1
        
        # If only 1 agent (this bot) is alive, switch to attacker
        was_alone = self._is_alone
        self._is_alone = (teammates_alive == 1)
        
        # Log when status changes
        if not was_alone and self._is_alone:
            logger.info(f"Base Defender #{agent.state.id_entity} is now ALONE! Switching to attacker mode.")
        elif was_alone and not self._is_alone:
            logger.info(f"Base Defender #{agent.state.id_entity} has teammates again. Resuming defense.")
    
    def _check_stuck(self, agent, dt: float) -> None:
        """
        Simple stuck detection: if not moving, pick a random direction and go.
        
        Args:
            agent: Agent instance.
            dt: Delta time.
        """
        current_pos = (agent.state.x, agent.state.y)
        
        # Initialize last position
        if self._last_position is None:
            self._last_position = current_pos
            return
        
        # Calculate movement distance
        dx = current_pos[0] - self._last_position[0]
        dy = current_pos[1] - self._last_position[1]
        distance_moved = math.sqrt(dx * dx + dy * dy)
        
        # If moved less than 1 pixel, increment stuck counter
        if distance_moved < 1.0:
            self._stuck_counter += 1
        else:
            self._stuck_counter = 0  # Reset when moving
        
        self._last_position = current_pos
        
        # If stuck for 20 frames (~0.33 seconds), activate avoidance
        if self._stuck_counter >= 20 and self._avoidance_timer <= 0:
            # Pick a random direction
            all_directions = [
                Direction.NORTH, Direction.NORTH_EAST, Direction.EAST, Direction.SOUTH_EAST,
                Direction.SOUTH, Direction.SOUTH_WEST, Direction.WEST, Direction.NORTH_WEST
            ]
            self._avoidance_direction = random.choice(all_directions)
            # Go in that direction for 0.5-1.0 seconds
            self._avoidance_timer = random.uniform(0.5, 1.0)
            self._stuck_counter = 0  # Reset counter
        
        # Apply avoidance if active
        if self._avoidance_timer > 0:
            self._avoidance_timer -= dt
            agent.move(dt, self._avoidance_direction)
            # If timer expired, clear direction
            if self._avoidance_timer <= 0:
                self._avoidance_direction = None
    
    def _defender_behavior(self, agent, dt: float) -> None:
        """
        Main defender behavior: patrol base and respond to threats.
        
        Args:
            agent: Agent instance.
            dt: Delta time.
        """
        # Skip movement if avoidance is active
        if self._avoidance_timer > 0:
            return
        
        own_flag = self._get_own_flag(agent)
        own_base_x, own_base_y = self._get_own_base(agent)
        
        # Priority 1: If flag is dropped, GO GET IT IMMEDIATELY
        if own_flag.state == 2:  # FlagState.DROPPED
            agent.move_towards(dt, own_flag.x, own_flag.y)
            if not agent.detected_enemies:
                agent.point_gun_at(own_flag.x, own_flag.y)
            return
        
        # Priority 2: If flag is taken, HUNT THE CARRIER
        if own_flag.state == 1:  # FlagState.CARRIED
            if own_flag.carrier_id and own_flag.carrier_id in agent.agents_dict:
                carrier = agent.agents_dict[own_flag.carrier_id].state
                
                # Calculate distance to carrier
                dx = carrier.x - agent.state.x
                dy = carrier.y - agent.state.y
                distance = math.sqrt(dx * dx + dy * dy)
                
                # Only chase if within reasonable distance
                if distance <= self.HUNTER_MODE_RADIUS:
                    agent.move_towards(dt, carrier.x, carrier.y)
                    agent.point_gun_at(carrier.x, carrier.y)
                    
                    # Shoot aggressively at carrier
                    if agent.current_ammo > 0 and agent.reload_timer is None:
                        agent.load_bullet()
                    return
        
        # Priority 3: Normal patrol around base
        dx = agent.state.x - own_base_x
        dy = agent.state.y - own_base_y
        distance_to_base = math.sqrt(dx * dx + dy * dy)
        
        # Use tighter patrol if flag is safe at base
        patrol_radius = self.TIGHT_DEFENSE_RADIUS if own_flag.state == 0 else self.BASE_PATROL_RADIUS
        
        if distance_to_base > patrol_radius:
            # Too far from base - return
            agent.move_towards(dt, own_base_x, own_base_y)
            if not agent.detected_enemies:
                agent.point_gun_at(own_base_x, own_base_y)
        else:
            # Patrol around base
            self.direction_timer += dt
            if self.direction_timer >= self.CHANGE_DIRECTION_INTERVAL:
                self.patrol_direction = random.choice(list(Direction))
                self.direction_timer = 0.0
            
            agent.move(dt, self.patrol_direction)
            
            # If blocked, change direction immediately
            if agent.is_blocked():
                self.patrol_direction = random.choice(list(Direction))
                agent.move(dt, self.patrol_direction)
        
        # Always scan for threats when not engaging
        if not agent.detected_enemies:
            # Look toward enemy side
            enemy_base_x, enemy_base_y = self._get_enemy_base(agent)
            agent.point_gun_at(enemy_base_x, enemy_base_y)
    
    def _attacker_behavior(self, agent, dt: float) -> None:
        """
        Attacker behavior when alone: capture enemy flag.
        
        Args:
            agent: Agent instance.
            dt: Delta time.
        """
        enemy_flag = self._get_enemy_flag(agent)
        own_flag = self._get_own_flag(agent)
        
        # Am I carrying the enemy flag?
        if enemy_flag.carrier_id == agent.state.id_entity:
            # Bring it home!
            own_base_x, own_base_y = self._get_own_base(agent)
            
            # Calculate distance to base
            dx = own_base_x - agent.state.x
            dy = own_base_y - agent.state.y
            distance = math.sqrt(dx * dx + dy * dy)
            
            # If close enough to capture, stop moving
            if distance <= CTF_FLAG_RETURN_RADIUS:
                if agent.detected_enemies:
                    pass  # Just defend
                else:
                    agent.point_gun_at(own_base_x, own_base_y)
                return
            
            # Move toward base
            if self._avoidance_timer > 0:
                pass  # Avoidance active
            else:
                agent.move_towards(dt, own_base_x, own_base_y)
            
            # Point gun at enemies or forward
            if not agent.detected_enemies:
                agent.point_gun_at(own_base_x, own_base_y)
            return
        
        # Move toward enemy flag
        if self._avoidance_timer > 0:
            pass  # Avoidance active
        else:
            agent.move_towards(dt, enemy_flag.x, enemy_flag.y)
        
        # Point gun in movement direction if no enemies
        if not agent.detected_enemies:
            agent.point_gun_at(enemy_flag.x, enemy_flag.y)
    
    def _combat(self, agent) -> None:
        """
        Combat behavior: shoot at enemies.
        
        Args:
            agent: Agent instance.
        """
        # Find closest enemy
        target_id = agent.get_closest_enemy()
        if not target_id or target_id not in agent.agents_dict:
            return
        
        target = agent.agents_dict[target_id].state
        
        # Calculate distance to target
        dx = target.x - agent.state.x
        dy = target.y - agent.state.y
        distance = math.sqrt(dx * dx + dy * dy)
        
        # Always aim at enemy
        agent.point_gun_at(target.x, target.y)
        
        # Shoot if we have ammo and are not reloading
        if agent.current_ammo > 0 and agent.reload_timer is None:
            # Check if gun is roughly aimed (within 30 degrees)
            target_angle = math.atan2(dy, dx)
            angle_diff = abs(target_angle - agent.state.gun_angle)
            # Normalize angle difference to [-pi, pi]
            while angle_diff > math.pi:
                angle_diff -= 2 * math.pi
            while angle_diff < -math.pi:
                angle_diff += 2 * math.pi
            
            # Shoot if roughly aimed or close range
            if abs(angle_diff) < 0.52 or distance < 150.0:
                agent.load_bullet()
    
    def _get_enemy_flag(self, agent):
        """Get enemy flag reference."""
        if agent.state.team == Team.TEAM_A:
            return self.game_manager.flag_team_b
        else:
            return self.game_manager.flag_team_a
    
    def _get_own_flag(self, agent):
        """Get own flag reference."""
        if agent.state.team == Team.TEAM_A:
            return self.game_manager.flag_team_a
        else:
            return self.game_manager.flag_team_b
    
    def _get_own_base(self, agent) -> tuple[float, float]:
        """Get own base coordinates."""
        if agent.state.team == Team.TEAM_A:
            return (CTF_FLAG_TEAM_A_BASE_X, CTF_FLAG_TEAM_A_BASE_Y)
        else:
            return (CTF_FLAG_TEAM_B_BASE_X, CTF_FLAG_TEAM_B_BASE_Y)
    
    def _get_enemy_base(self, agent) -> tuple[float, float]:
        """Get enemy base coordinates."""
        if agent.state.team == Team.TEAM_A:
            return (CTF_FLAG_TEAM_B_BASE_X, CTF_FLAG_TEAM_B_BASE_Y)
        else:
            return (CTF_FLAG_TEAM_A_BASE_X, CTF_FLAG_TEAM_A_BASE_Y)
