# server/logic/agent.py
from common.states.state_entity import StateEntity, Team, MAX_ENTITY_ID
from common.states.state_walls import StateWalls
from common.config import FOV_RATIO, FOV_OPENING, FOV_NUM_RAYS, DEFAULT_ENTITY_RADIUS
from common.config import RAY_STEP_DIVISOR, LOGICAL_SCREEN_WIDTH
from server.gameplay.bullet import Bullet
from server.gameplay.collision import check_move_validity, CollisionType
from server.strategy.base import Strategy
import math
from enum import IntEnum


class Direction(IntEnum):
    """8-directional movement."""
    NORTH = 0
    NORTH_EAST = 1
    EAST = 2
    SOUTH_EAST = 3
    SOUTH = 4
    SOUTH_WEST = 5
    WEST = 6
    NORTH_WEST = 7


SQRT2_OVER_2 = math.sqrt(2) / 2

DIRECTION_VECTORS = {
    Direction.NORTH: (0.0, 1.0),
    Direction.NORTH_EAST: (SQRT2_OVER_2, SQRT2_OVER_2),
    Direction.EAST: (1.0, 0.0),
    Direction.SOUTH_EAST: (SQRT2_OVER_2, -SQRT2_OVER_2),
    Direction.SOUTH: (0.0, -1.0),
    Direction.SOUTH_WEST: (-SQRT2_OVER_2, -SQRT2_OVER_2),
    Direction.WEST: (-1.0, 0.0),
    Direction.NORTH_WEST: (-SQRT2_OVER_2, SQRT2_OVER_2),
}

NO_SHOOT = -1.0


class Agent:
    """Server-side agent logic with vision/detection system."""
    
    _next_id = 0

    @staticmethod
    def get_next_id() -> int:
        """Get next agent ID and increment counter."""
        agent_id = Agent._next_id
        Agent._next_id = (Agent._next_id + 1) % (MAX_ENTITY_ID + 1)
        return agent_id

    def __init__(self, walls_state: StateWalls, agents_dict: dict, bullets_dict: dict,
                 strategy: Strategy, x: float = 0.0, y: float = 0.0, 
                 team: int = Team.NEUTRAL, health: float = 100.0, 
                 damage: float = 55.0, speed: float = 50.0, shoot_duration: float = 1,
                 gun_angle: float | None = None):
        """
        Initialize agent (creates StateEntity with auto-generated ID).
        
        Args:
            walls_state: World walls for ray casting
            agents_dict: Reference to all agents
            bullets_dict: Reference to all bullets
            strategy: Strategy instance for AI behavior
            x, y: Initial position
            team: Team ownership
            health: Agent health points
            damage: Damage dealt per bullet
            speed: Movement speed (pixels/sec)
            shoot_duration: Cooldown between shots (seconds)
            gun_angle: Initial gun angle in radians. If None, auto-set based on x position.
        """
        # Auto-set gun angle based on x position
        if gun_angle is None:
            map_mid = LOGICAL_SCREEN_WIDTH / 2
            gun_angle = 0.0 if x < map_mid else math.pi
        
        # Create state with auto-generated ID
        self.state = StateEntity(
            id_entity=Agent.get_next_id(),
            x=x,
            y=y,
            radius=DEFAULT_ENTITY_RADIUS,
            team=team,
            gun_angle=gun_angle
        )
        
        self.walls_state = walls_state
        self.agents_dict = agents_dict
        self.bullets_dict = bullets_dict
        self.strategy = strategy
        self.detected_enemies = set()
        
        self.health = health
        self.damage = damage
        self.speed = speed
        self.time_alive = 0.0
        self.shoot_duration = shoot_duration
        self.shoot_timer = NO_SHOOT
        self.gun_rotation_speed = 2.0 * math.pi / 5.0
        self.target_gun_angle = self.state.gun_angle
        self.blocked = None

    # === FRAME UPDATE ===

    def update_strategy(self, dt: float):
        """
        Called each frame by GameManager.
        Executes: system tick → strategy logic.
        
        Args:
            dt: Delta time in seconds
        """
        self._update_tick_before_strategy(dt)
        self.strategy.execute(self, dt)

    def _update_tick_before_strategy(self, dt: float):
        """
        Core systems updated each frame before strategy runs.
        
        Systems:
        - Lifetime tracking
        - Gun rotation towards target
        - Weapon cooldown + firing
        """
        self.time_alive += dt
        self._rotate_gun_towards_target(dt)
        
        if self.shoot_timer >= 0:
            self.shoot_timer -= dt
            if self.shoot_timer <= 0:
                self._fire_bullet()

    # === MOVEMENT ===

    def move(self, dt: float, direction: Direction):
        """
        Move agent in given direction.
        Sets self.blocked if collision detected.
        
        Args:
            dt: Delta time in seconds
            direction: Direction enum (NORTH, EAST, etc.)
        """
        dx, dy = DIRECTION_VECTORS[direction]
        new_x = self.state.x + dx * self.speed * dt
        new_y = self.state.y + dy * self.speed * dt
        
        collision_type, obstacle_id = check_move_validity(
            new_x, new_y, self.state.radius,
            self.agents_dict, self.walls_state,
            exclude_id=self.state.id_entity
        )
        
        if collision_type == CollisionType.NONE:
            self.state.set_position(new_x, new_y)
            self.blocked = None
        else:
            self.blocked = (collision_type, obstacle_id)
            print(f"[BLOCK] Agent {self.state.id_entity} blocked by {collision_type.name} at ({new_x:.1f}, {new_y:.1f})")

    def move_towards(self, dt: float, target_x: float, target_y: float):
        """
        Move towards target coordinates.
        Automatically picks best 8-direction towards target.
        
        Args:
            dt: Delta time in seconds
            target_x, target_y: Target coordinates
        """
        dx = target_x - self.state.x
        dy = target_y - self.state.y
        
        # Pick best 8-direction
        if abs(dx) > abs(dy):
            direction = Direction.EAST if dx > 0 else Direction.WEST
        else:
            direction = Direction.SOUTH if dy > 0 else Direction.NORTH
        
        self.move(dt, direction)

    def is_blocked(self) -> bool:
        """Check if agent is currently blocked from moving."""
        return self.blocked is not None

    def blocked_by(self) -> tuple | None:
        """
        Get what's blocking agent.
        Returns: (CollisionType, obstacle_id) or None
        """
        return self.blocked

    # === GUN/WEAPON SYSTEM ===

    def set_target_gun_angle(self, angle: float):
        """
        Set desired gun angle.
        Gun rotates smoothly towards this target each frame.
        
        Args:
            angle: Target angle in radians
        """
        self.target_gun_angle = angle

    def point_gun_at(self, target_x: float, target_y: float):
        """
        Calculate angle to target coordinates and set as gun target.
        Gun will smoothly rotate towards target.
        
        Args:
            target_x, target_y: Target world coordinates
        """
        dx = target_x - self.state.x
        dy = target_y - self.state.y
        
        angle = math.atan2(-dy, dx)
        self.set_target_gun_angle(angle)

    def _rotate_gun_towards_target(self, dt: float):
        """
        Update gun angle, smoothly rotating towards target.
        Called automatically each frame by _update_tick_before_strategy().
        """
        current = self.state.gun_angle
        delta = self.target_gun_angle - current
        
        # Normalize delta to [-pi, pi]
        while delta > math.pi:
            delta -= 2 * math.pi
        while delta < -math.pi:
            delta += 2 * math.pi
        
        max_rotation = self.gun_rotation_speed * dt
        new_angle = current + math.copysign(min(abs(delta), max_rotation), delta)
        
        self.state.set_gun_angle(new_angle)

    def load_bullet(self):
        """
        Load weapon - starts cooldown timer if not already loaded.
        Called by strategy when agent should fire.
        """
        if self.shoot_timer == NO_SHOOT:
            self.shoot_timer = self.shoot_duration

    def _fire_bullet(self):
        """Internal: spawn bullet."""
        offset = self.state.radius + 5.0
        spawn_x = self.state.x + math.cos(self.state.gun_angle) * offset
        spawn_y = self.state.y - math.sin(self.state.gun_angle) * offset
        
        print(f"[FIRE] Agent {self.state.id_entity} firing bullet at ({spawn_x:.1f}, {spawn_y:.1f})")  # DEBUG
        
        bullet = Bullet(
            x=spawn_x,
            y=spawn_y,
            speed=100.0,
            angle=self.state.gun_angle,
            owner_id=self.state.id_entity,
            team=self.state.team,
            damage=self.damage
        )
        
        self.bullets_dict[bullet.state.id_bullet] = bullet
        self.shoot_timer = NO_SHOOT
        
        print(f"[FIRE] Bullet {bullet.state.id_bullet} created, total bullets: {len(self.bullets_dict)}")  # DEBUG


    # === VISION/DETECTION ===

    def detect_enemies(self):
        """Scan FOV cone and detect all visible enemies."""
        fov_radius = FOV_RATIO * self.state.radius
        center_angle = self.state.gun_angle
        half_opening = FOV_OPENING / 2
        start_angle = center_angle - half_opening
        
        detected = set()
        angle_step = FOV_OPENING / FOV_NUM_RAYS
        
        for i in range(FOV_NUM_RAYS + 1):
            angle = start_angle + i * angle_step
            hit = self._cast_ray(self.state.x, self.state.y, angle, fov_radius)
            
            if hit and hit[1] == 'agent':
                detected.add(hit[2])
        
        self.detected_enemies = detected
        return detected

    def _cast_ray(self, start_x, start_y, angle, max_distance):
        """
        Cast ray and return first obstacle hit (wall or agent).
        Agents don't block each other (transparent), only walls block.
        
        Returns:
            (distance, hit_type, hit_id) or None
            hit_type: 'agent' or 'wall'
        """
        dx = math.cos(angle)
        dy = -math.sin(angle)
        
        step_size = self.walls_state.grid_unit / RAY_STEP_DIVISOR
        current_x = start_x
        current_y = start_y
        traveled = 0
        
        fov_radius = FOV_RATIO * self.state.radius
        candidates = []
        
        for agent_id, agent in self.agents_dict.items():
            if agent_id == self.state.id_entity:
                continue
            
            dx_agent = agent.state.x - start_x
            dy_agent = agent.state.y - start_y
            dist_sq = dx_agent * dx_agent + dy_agent * dy_agent
            
            if dist_sq < (fov_radius + agent.state.radius) ** 2:
                candidates.append((agent_id, agent))
        
        while traveled < max_distance:
            current_x += dx * step_size
            current_y += dy * step_size
            traveled += step_size
            
            if self.walls_state.has_wall_at_pos(current_x, current_y):
                return (traveled, 'wall', None)
            
            for agent_id, agent in candidates:
                dist_sq = (current_x - agent.state.x) ** 2 + (current_y - agent.state.y) ** 2
                if dist_sq < agent.state.radius ** 2:
                    return (traveled, 'agent', agent_id)
        
        return None

    def can_see(self, target_id) -> bool:
        """Quick check if specific agent is currently detected."""
        return target_id in self.detected_enemies

    def get_closest_enemy(self) -> int | None:
        """Get ID of closest detected enemy (alive only)."""
        if not self.detected_enemies:
            return None
        
        # Filter out dead agents
        alive_enemies = [aid for aid in self.detected_enemies if aid in self.agents_dict and self.agents_dict[aid].is_alive()]
        
        if not alive_enemies:
            return None
        
        return min(alive_enemies,
                key=lambda aid: (self.agents_dict[aid].state.x - self.state.x)**2 +
                                (self.agents_dict[aid].state.y - self.state.y)**2)

    # === HEALTH/ALIVE ===

    def take_damage(self, amount: float):
        """Reduce health."""
        self.health = max(0.0, self.health - amount)

    def is_alive(self) -> bool:
        """Check if agent is still alive."""
        return self.health > 0
