"""
CTF AI Strategy - Intelligent bot behavior for Capture the Flag.

Implements role-based behavior: Attacker, Carrier, Hunter, and Escort.
"""

import random
import math
from enum import IntEnum

from server.strategy.base import Strategy
from common.config import Direction
from common.ctf_config import (
    CTF_FLAG_TEAM_A_BASE_X,
    CTF_FLAG_TEAM_A_BASE_Y,
    CTF_FLAG_TEAM_B_BASE_X,
    CTF_FLAG_TEAM_B_BASE_Y,
    CTF_FLAG_PICKUP_RADIUS,
)
from common.states.state_entity import Team
from common.logger import get_logger

logger = get_logger(__name__)


class CTFRole(IntEnum):
    """Bot role enumeration."""
    ATTACKER = 0     # Go get enemy flag
    CARRIER = 1      # Carrying flag back to base
    HUNTER = 2       # Chase enemy carrier
    ESCORT = 3       # Escort friendly carrier without crowding


class CTFStrategy(Strategy):
    """
    Advanced CTF strategy with dynamic role assignment.
    
    Behavior:
    - Attackers rush enemy flag
    - Carriers bring flag home
    - Hunters chase enemy carriers
    - Escorts support friendly carrier
    """
    
    # Configuration
    LOW_HEALTH_THRESHOLD = 25.0  # When to retreat
    CARRIER_ESCORT_DISTANCE = 120.0  # Distance to maintain from carrier
    CARRIER_MIN_DISTANCE = 60.0  # Minimum distance to avoid crowding carrier
    HUNTER_AGGRESSION_RANGE = 250.0  # Range to chase carrier
    ESCORT_LATERAL_OFFSET = 80.0  # Lateral offset for escort positioning
    
    def __init__(self, game_manager) -> None:
        """
        Initialize CTF strategy.
        
        Args:
            game_manager: GameManagerCTF instance for accessing game state.
        """
        self.game_manager = game_manager
        self.role = CTFRole.ATTACKER  # Default role
        # Permanent escort assignment: None=unassigned, True=escort, False=attacker
        self._is_escort = None
        # Simple stuck detection
        self._stuck_counter = 0
        self._last_position = None
        # Avoidance: just pick a random direction and go for a time
        self._avoidance_timer = 0.0
        self._avoidance_direction = None
    
    def execute(self, agent, dt: float) -> None:
        """
        Execute CTF strategy with dynamic role switching.
        
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
        
        # Determine current role based on game state
        self._update_role(agent)
        
        # Debug logging (only for agent ID 0 to avoid spam)
        if agent.state.id_entity == 0:
            enemy_count = len(agent.detected_enemies)
            logger.debug(f"Agent 0: role={self.role.name}, enemies={enemy_count}, ammo={agent.current_ammo}, reload={agent.reload_timer}")
        
        # Execute role-specific behavior
        if self.role == CTFRole.CARRIER:
            self._carrier_behavior(agent, dt)
        elif self.role == CTFRole.ESCORT:
            self._escort_behavior(agent, dt)
        elif self.role == CTFRole.HUNTER:
            self._hunter_behavior(agent, dt)
        else:  # ATTACKER
            self._attacker_behavior(agent, dt)
        
        # CRITICAL: Always attempt to shoot at visible enemies
        # This is a fallback to ensure bots never stop shooting
        if agent.detected_enemies:
            self._combat(agent)
    
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
    
    def _update_role(self, agent) -> None:
        """
        Dynamically assign role based on game state.
        
        Args:
            agent: Agent instance.
        """
        enemy_flag = self._get_enemy_flag(agent)
        own_flag = self._get_own_flag(agent)
        
        # Am I carrying the flag?
        if enemy_flag.carrier_id == agent.state.id_entity:
            self.role = CTFRole.CARRIER
            return
        
        # CRITICAL: Is a TEAMMATE carrying the enemy flag?
        if enemy_flag.state == 1 and enemy_flag.carrier_id:  # FlagState.CARRIED
            # Check if carrier is a teammate
            if enemy_flag.carrier_id in agent.agents_dict:
                carrier_agent = agent.agents_dict[enemy_flag.carrier_id]
                if carrier_agent.state.team == agent.state.team:
                    # Teammate has flag! Don't crowd them
                    # Make PERMANENT assignment (don't re-randomize every frame!)
                    # Initialize _is_escort if not present (backward compatibility)
                    if not hasattr(self, '_is_escort'):
                        self._is_escort = None
                    
                    if self._is_escort is None:
                        # First time seeing carrier - assign role permanently
                        self._is_escort = random.random() < 0.5
                    
                    if self._is_escort:
                        self.role = CTFRole.ESCORT
                        return
                    else:
                        # Stay at base but as attacker ready to push
                        self.role = CTFRole.ATTACKER
                        return
        
        # Is our flag taken? Hunt the carrier!
        if own_flag.state == 1:  # FlagState.CARRIED
            # Check if carrier exists and is alive
            if own_flag.carrier_id and own_flag.carrier_id in agent.agents_dict:
                carrier = agent.agents_dict[own_flag.carrier_id].state
                dx = agent.state.x - carrier.x
                dy = agent.state.y - carrier.y
                distance = math.sqrt(dx * dx + dy * dy)
                
                if distance < self.HUNTER_AGGRESSION_RANGE:
                    self.role = CTFRole.HUNTER
                    return
            else:
                # Carrier doesn't exist but flag is marked as carried - flag logic bug?
                # Just become attacker to keep moving
                self.role = CTFRole.ATTACKER
                return
        
        # Default: be an attacker (base defense handled by CTFBaseDefenderStrategy)
        self.role = CTFRole.ATTACKER
    
    def _attacker_behavior(self, agent, dt: float) -> None:
        """
        Attacker: go get the enemy flag.
        
        Args:
            agent: Agent instance.
            dt: Delta time.
        """
        enemy_flag = self._get_enemy_flag(agent)
        
        # If avoidance is active, let it handle movement
        if self._avoidance_timer > 0:
            pass
        else:
            # Normal movement toward flag
            agent.move_towards(dt, enemy_flag.x, enemy_flag.y)
        
        # Point gun in movement direction if no enemies
        if not agent.detected_enemies:
            agent.point_gun_at(enemy_flag.x, enemy_flag.y)
    
    def _carrier_behavior(self, agent, dt: float) -> None:
        """
        Carrier: bring flag back to base.
        
        Args:
            agent: Agent instance.
            dt: Delta time.
        """
        own_base_x, own_base_y = self._get_own_base(agent)
        
        # Calculate distance to base
        dx = own_base_x - agent.state.x
        dy = own_base_y - agent.state.y
        distance = math.sqrt(dx * dx + dy * dy)
        
        # Track if carrier is stuck (distance not changing)
        if not hasattr(self, '_last_distance'):
            self._last_distance = distance
            self._stuck_counter = 0
        
        # Check if carrier is stuck (same distance for multiple frames)
        distance_change = abs(distance - self._last_distance)
        if distance_change < 1.0:  # Less than 1 pixel change
            self._stuck_counter += 1
        else:
            self._stuck_counter = 0
        
        self._last_distance = distance
        
        # Log carrier progress every 2 seconds
        if hasattr(self, '_carrier_log_timer'):
            self._carrier_log_timer += dt
        else:
            self._carrier_log_timer = 0.0
        
        if self._carrier_log_timer >= 2.0:
            logger.info(f"Carrier #{agent.state.id_entity} distance to base: {distance:.1f} pixels (stuck_counter={self._stuck_counter})")
            self._carrier_log_timer = 0.0
        
        # Low health? Evade enemies more
        if agent.health < self.LOW_HEALTH_THRESHOLD and agent.detected_enemies:
            self._evade_enemies(agent, dt)
            return
        
        # If close enough to capture, stop moving and just wait for capture
        # This prevents blocking and struggling at the base entrance
        from common.ctf_config import CTF_FLAG_RETURN_RADIUS
        if distance <= CTF_FLAG_RETURN_RADIUS:
            # Close enough! Stop moving, just point gun at enemies
            # Game manager will detect capture automatically
            if agent.detected_enemies:
                # Defend while waiting for capture
                pass
            else:
                # Just stand still and wait
                agent.point_gun_at(own_base_x, own_base_y)
            return
        
        # Move towards base
        if self._avoidance_timer > 0:
            # Avoidance active, don't interfere
            pass
        else:
            # Normal path
            agent.move_towards(dt, own_base_x, own_base_y)
        
        # Point gun at enemies if any, else toward base
        if not agent.detected_enemies:
            agent.point_gun_at(own_base_x, own_base_y)
    
    def _escort_behavior(self, agent, dt: float) -> None:
        """
        Escort: support friendly carrier without crowding them.
        
        Args:
            agent: Agent instance.
            dt: Delta time.
        """
        # Initialize if missing (defensive)
        if not hasattr(self, '_is_escort'):
            self._is_escort = None
        
        enemy_flag = self._get_enemy_flag(agent)
        
        # Verify teammate still has flag
        if enemy_flag.state != 1 or not enemy_flag.carrier_id:
            # Flag not carried anymore - reset escort assignment
            self._is_escort = None
            self.role = CTFRole.ATTACKER
            return
        
        if enemy_flag.carrier_id not in agent.agents_dict:
            self._is_escort = None
            self.role = CTFRole.ATTACKER
            return
        
        carrier_agent = agent.agents_dict[enemy_flag.carrier_id]
        if carrier_agent.state.team != agent.state.team:
            # Not our teammate
            self._is_escort = None
            self.role = CTFRole.ATTACKER
            return
        
        carrier_pos = carrier_agent.state
        own_base_x, own_base_y = self._get_own_base(agent)
        
        # Calculate vector from carrier to base
        base_dx = own_base_x - carrier_pos.x
        base_dy = own_base_y - carrier_pos.y
        base_distance = math.sqrt(base_dx * base_dx + base_dy * base_dy)
        
        if base_distance < 0.01:
            # Carrier at base, become attacker and reset assignment
            self._is_escort = None
            self.role = CTFRole.ATTACKER
            return
        
        # Calculate escort position: lateral to carrier's path
        # Position ourselves to the side of carrier, not behind them
        base_angle = math.atan2(base_dy, base_dx)
        
        # Alternate between left and right side based on agent ID
        side_multiplier = 1 if agent.state.id_entity % 2 == 0 else -1
        lateral_angle = base_angle + (math.pi / 2) * side_multiplier
        
        # Target position: offset from carrier laterally
        target_x = carrier_pos.x + math.cos(lateral_angle) * self.ESCORT_LATERAL_OFFSET
        target_y = carrier_pos.y + math.sin(lateral_angle) * self.ESCORT_LATERAL_OFFSET
        
        # Calculate distance to carrier
        dx_carrier = agent.state.x - carrier_pos.x
        dy_carrier = agent.state.y - carrier_pos.y
        distance_to_carrier = math.sqrt(dx_carrier * dx_carrier + dy_carrier * dy_carrier)
        
        # If too close to carrier, move away
        if distance_to_carrier < self.CARRIER_MIN_DISTANCE:
            # Move perpendicular away from carrier
            away_angle = math.atan2(dy_carrier, dx_carrier)
            away_dir = self._angle_to_direction(away_angle)
            agent.move(dt, away_dir)
        # If too far, move toward escort position
        elif distance_to_carrier > self.CARRIER_ESCORT_DISTANCE:
            agent.move_towards(dt, target_x, target_y)
        else:
            # Maintain escort position, move parallel to carrier
            agent.move_towards(dt, target_x, target_y)
        
        # Combat: always aim at enemies if present
        # Otherwise scan for threats ahead of carrier
        if not agent.detected_enemies:
            # Look ahead of carrier
            scan_x = carrier_pos.x + base_dx * 0.5
            scan_y = carrier_pos.y + base_dy * 0.5
            agent.point_gun_at(scan_x, scan_y)
    
    def _hunter_behavior(self, agent, dt: float) -> None:
        """
        Hunter: chase and kill enemy carrier.
        
        Args:
            agent: Agent instance.
            dt: Delta time.
        """
        own_flag = self._get_own_flag(agent)
        
        # Flag not carried anymore? Switch role
        if own_flag.state != 1:  # Not CARRIED
            self.role = CTFRole.ATTACKER
            return
        
        # Find carrier
        if own_flag.carrier_id and own_flag.carrier_id in agent.agents_dict:
            carrier = agent.agents_dict[own_flag.carrier_id].state
            
            # Rush toward carrier
            agent.move_towards(dt, carrier.x, carrier.y)
            
            # Always aim at carrier
            agent.point_gun_at(carrier.x, carrier.y)
            
            # Shoot aggressively at carrier
            # Hunter should ALWAYS shoot when they have ammo
            if agent.current_ammo > 0 and agent.reload_timer is None:
                agent.load_bullet()
        else:
            # Carrier not visible - become attacker to keep moving
            self.role = CTFRole.ATTACKER
    
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
        # Be aggressive - shoot at any enemy in reasonable range
        if agent.current_ammo > 0 and agent.reload_timer is None:
            # Check if gun is roughly aimed (within 30 degrees)
            target_angle = math.atan2(dy, dx)
            angle_diff = abs(target_angle - agent.state.gun_angle)
            # Normalize angle difference to [-pi, pi]
            while angle_diff > math.pi:
                angle_diff -= 2 * math.pi
            while angle_diff < -math.pi:
                angle_diff += 2 * math.pi
            
            # Shoot if roughly aimed (30 degrees = 0.52 radians)
            if abs(angle_diff) < 0.52 or distance < 150.0:
                agent.load_bullet()
    
    def _evade_enemies(self, agent, dt: float) -> None:
        """
        Evade enemies while moving toward goal.
        
        Args:
            agent: Agent instance.
            dt: Delta time.
        """
        if not agent.detected_enemies:
            return
        
        # Find closest enemy
        target_id = agent.get_closest_enemy()
        if not target_id or target_id not in agent.agents_dict:
            return
        
        enemy = agent.agents_dict[target_id].state
        
        # Move at angle away from enemy
        dx = agent.state.x - enemy.x
        dy = agent.state.y - enemy.y
        
        # Add perpendicular component for strafing
        angle_away = math.atan2(dy, dx)
        strafe_angle = angle_away + math.pi / 4 * random.choice([-1, 1])
        
        direction = self._angle_to_direction(strafe_angle)
        agent.move(dt, direction)
    
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
    
    def _angle_to_direction(self, angle: float) -> Direction:
        """Convert angle to nearest 8-direction."""
        angle = angle % (2 * math.pi)
        section = int((angle + math.pi / 8) / (math.pi / 4)) % 8
        
        directions = [
            Direction.EAST,
            Direction.NORTH_EAST,
            Direction.NORTH,
            Direction.NORTH_WEST,
            Direction.WEST,
            Direction.SOUTH_WEST,
            Direction.SOUTH,
            Direction.SOUTH_EAST,
        ]
        
        return directions[section]
