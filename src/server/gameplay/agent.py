# External libraries
import math


# Internal libraries
from common.config import (
    Direction,
    DEFAULT_ENTITY_RADIUS,
    FOV_NUM_RAYS,
    FOV_OPENING,
    FOV_RATIO,
    LOGICAL_SCREEN_WIDTH,
    RAY_STEP_DIVISOR,
)
from common.config import AMMO_INFINITE
from common.states.state_entity import MAX_ENTITY_ID, StateEntity, Team
from common.states.state_walls import StateWalls
from server.config import (
    AGENT_GUN_ROTATION_SPEED,
    BULLET_SPEED,
    BULLET_SPAWN_OFFSET_RATIO,
    DEFAULT_AGENT_DAMAGE,
    DEFAULT_AGENT_HEALTH,
    DEFAULT_AGENT_SPEED,
    DEFAULT_SHOOT_DURATION,
    NO_SHOOT,
)
from server.config import DEFAULT_MAGAZINE_SIZE, DEFAULT_RELOAD_DURATION
from server.gameplay.bullet import Bullet
from server.gameplay.collision import (
    CollisionType,
    check_move_validity,
)
from server.strategy.base import Strategy


# Normalized direction vectors
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


class Agent:
    """
    Server-side agent with movement, weapon, and vision systems.

    Manages physics, collision detection, and AI strategy execution.
    Wraps StateEntity for network transmission.
    """

    # Class-level ID counter with wraparound
    _next_id = 0

    @staticmethod
    def get_next_id() -> int:
        """
        Get next unique agent ID and increment counter.

        Wraps around at MAX_ENTITY_ID to prevent overflow.

        Returns:
            Next available agent ID.
        """
        agent_id = Agent._next_id
        Agent._next_id = (Agent._next_id + 1) % (MAX_ENTITY_ID + 1)
        return agent_id

    # Initialization

    def __init__(
        self,
        walls_state: StateWalls,
        agents_dict: dict,
        bullets_dict: dict,
        strategy: Strategy,
        x: float = 0.0,
        y: float = 0.0,
        team: int = Team.NEUTRAL,
        health: float = DEFAULT_AGENT_HEALTH,
        damage: float = DEFAULT_AGENT_DAMAGE,
        speed: float = DEFAULT_AGENT_SPEED,
        shoot_duration: float = DEFAULT_SHOOT_DURATION,
        gun_angle: float | None = None,
        ammo: int | None = None,
    ) -> None:
        """
        Initialize agent with auto-generated ID.

        Args:
            walls_state: World walls for collision and ray casting.
            agents_dict: Reference to all active agents.
            bullets_dict: Reference to all active bullets.
            strategy: Strategy instance for AI behavior.
            x: Initial X position in pixels.
            y: Initial Y position in pixels.
            team: Team affiliation.
            health: Health points (starts alive if > 0).
            damage: Damage dealt per bullet fired.
            speed: Movement speed in pixels/second.
            shoot_duration: Cooldown between shots in seconds.
            gun_angle: Initial gun angle in radians. If None, set based
                on starting X position.
        """
        # Auto-set gun angle based on position
        if gun_angle is None:
            map_mid = LOGICAL_SCREEN_WIDTH / 2
            gun_angle = 0.0 if x < map_mid else math.pi

        # Ammo: None means infinite -> use AMMO_INFINITE sentinel
        from common.config import AMMO_INFINITE

        ammo_val = AMMO_INFINITE if ammo is None else int(ammo)

        self.state = StateEntity(
            id_entity=Agent.get_next_id(),
            x=x,
            y=y,
            radius=DEFAULT_ENTITY_RADIUS,
            team=team,
            gun_angle=gun_angle,
            health=health,
            ammo=ammo_val,
        )

        self.walls_state = walls_state
        self.agents_dict = agents_dict
        self.bullets_dict = bullets_dict
        self.strategy = strategy
        self.detected_enemies: set[int] = set()

        self.health = health
        self.damage = damage
        self.speed = speed
        self.ammo = ammo
        # Magazine and reload state
        self.magazine_size = DEFAULT_MAGAZINE_SIZE
        self.reload_duration = DEFAULT_RELOAD_DURATION
        # current_ammo mirrors the bullets remaining in the magazine
        # Use AMMO_INFINITE sentinel for infinite ammo
        self.current_ammo = (
            AMMO_INFINITE if ammo is None else int(ammo_val if ammo_val != AMMO_INFINITE else AMMO_INFINITE)
        )
        # If current_ammo is not infinite but greater than magazine_size, clamp it to magazine_size
        if self.current_ammo != AMMO_INFINITE and self.current_ammo > self.magazine_size:
            self.current_ammo = self.magazine_size
        # Reload timer in seconds (None when not reloading)
        self.reload_timer: float | None = None
        self.time_alive = 0.0
        self.shoot_timer = NO_SHOOT
        self.gun_rotation_speed = AGENT_GUN_ROTATION_SPEED
        self.target_gun_angle = self.state.gun_angle
        self.blocked: tuple[CollisionType, int] | None = None

    # Frame update

    def update_strategy(self, dt: float) -> None:
        """
        Execute core systems and strategy each frame.

        Args:
            dt: Delta time in seconds.
        """
        self._update_tick_before_strategy(dt)
        self.strategy.execute(self, dt)

    def _update_tick_before_strategy(self, dt: float) -> None:
        """
        Update core systems before strategy execution.

        Systems: lifetime tracking, gun rotation, weapon cooldown.

        Args:
            dt: Delta time in seconds.
        """
        self.time_alive += dt
        self._rotate_gun_towards_target(dt)

        if self.shoot_timer >= 0:
            self.shoot_timer -= dt
            if self.shoot_timer <= 0:
                self._fire_bullet()

        # Handle reload timer if active
        if self.reload_timer is not None:
            self.reload_timer -= dt
            if self.reload_timer <= 0:
                # Finish reload: refill magazine
                if self.current_ammo != AMMO_INFINITE:
                    self.current_ammo = self.magazine_size
                    # Update network-visible state ammo
                    self.state.ammo = int(self.current_ammo)
                self.reload_timer = None

    # Movement

    def move(self, dt: float, direction: Direction) -> None:
        """
        Move agent in given direction.

        Sets self.blocked if movement is obstructed.

        Args:
            dt: Delta time in seconds.
            direction: Direction enum (NORTH, EAST, etc.).
        """
        dx, dy = DIRECTION_VECTORS[direction]
        new_x = self.state.x + dx * self.speed * dt
        new_y = self.state.y + dy * self.speed * dt

        collision_type, obstacle_id = check_move_validity(
            new_x,
            new_y,
            self.state.radius,
            self.agents_dict,
            self.walls_state,
            exclude_id=self.state.id_entity,
        )

        if collision_type == CollisionType.NONE:
            self.state.set_position(new_x, new_y)
            self.blocked = None
        else:
            self.blocked = (collision_type, obstacle_id)

    def move_towards(
        self, dt: float, target_x: float, target_y: float
    ) -> None:
        """
        Move towards target using best 8-directional approach.

        Args:
            dt: Delta time in seconds.
            target_x: Target X coordinate.
            target_y: Target Y coordinate.
        """
        dx = target_x - self.state.x
        dy = target_y - self.state.y

        # Pick best 8-direction
        if abs(dx) > abs(dy):
            direction = Direction.EAST if dx > 0 else Direction.WEST
        else:
            direction = Direction.SOUTH if dy < 0 else Direction.NORTH

        self.move(dt, direction)

    def is_blocked(self) -> bool:
        """
        Check if agent is currently blocked from moving.

        Returns:
            True if blocked, False otherwise.
        """
        return self.blocked is not None

    def blocked_by(self) -> tuple[CollisionType, int] | None:
        """
        Get what is blocking agent movement.

        Returns:
            Tuple of (CollisionType, obstacle_id) or None if unblocked.
        """
        return self.blocked

    # Gun and weapon system

    def set_target_gun_angle(self, angle: float) -> None:
        """
        Set desired gun angle for smooth rotation.

        Gun will rotate towards this target each frame.

        Args:
            angle: Target angle in radians.
        """
        self.target_gun_angle = angle

    def point_gun_at(self, target_x: float, target_y: float) -> None:
        """
        Point gun at target coordinates.

        Args:
            target_x: Target X coordinate.
            target_y: Target Y coordinate.
        """
        dx = target_x - self.state.x
        dy = target_y - self.state.y

        angle = math.atan2(-dy, dx)
        self.set_target_gun_angle(angle)

    def _rotate_gun_towards_target(self, dt: float) -> None:
        """
        Smoothly rotate gun towards target angle.

        Called automatically each frame by update_strategy().

        Args:
            dt: Delta time in seconds.
        """
        current = self.state.gun_angle
        delta = self.target_gun_angle - current

        # Normalize delta to [-pi, pi]
        while delta > math.pi:
            delta -= 2 * math.pi
        while delta < -math.pi:
            delta += 2 * math.pi

        max_rotation = self.gun_rotation_speed * dt
        new_angle = current + math.copysign(
            min(abs(delta), max_rotation), delta
        )

        self.state.set_gun_angle(new_angle)

    def load_bullet(self) -> None:
        """
        Load weapon and start cooldown timer.

        Called by strategy when agent should fire.
        """
        # If currently reloading, ignore trigger
        if self.reload_timer is not None:
            return

        # If infinite ammo, allow shooting
        from common.config import AMMO_INFINITE

        if self.current_ammo == AMMO_INFINITE:
            if self.shoot_timer == NO_SHOOT:
                self.shoot_timer = DEFAULT_SHOOT_DURATION
            return

        # If we have bullets in magazine, set shoot timer
        if self.current_ammo > 0:
            if self.shoot_timer == NO_SHOOT:
                self.shoot_timer = DEFAULT_SHOOT_DURATION
            return

        # No bullets: start reload
        self.start_reload()

    def _fire_bullet(self) -> None:
        """Spawn bullet at gun muzzle position."""
        offset = self.state.radius * BULLET_SPAWN_OFFSET_RATIO
        spawn_x = (
            self.state.x + math.cos(self.state.gun_angle) * offset
        )
        spawn_y = (
            self.state.y - math.sin(self.state.gun_angle) * offset
        )
        from common.config import AMMO_INFINITE

        # If out of ammo and not infinite, do not fire (start reload instead)
        if self.current_ammo != AMMO_INFINITE and self.current_ammo <= 0:
            self.start_reload()
            self.shoot_timer = NO_SHOOT
            return

        bullet = Bullet(
            x=spawn_x,
            y=spawn_y,
            speed=BULLET_SPEED,
            angle=self.state.gun_angle,
            owner_id=self.state.id_entity,
            team=self.state.team,
            damage=self.damage,
        )

        self.bullets_dict[bullet.state.id_bullet] = bullet

        # Consume ammo if not infinite
        if self.current_ammo != AMMO_INFINITE:
            self.current_ammo = max(0, int(self.current_ammo - 1))
            self.state.ammo = int(self.current_ammo)
            # If magazine now empty, start reload
            if self.current_ammo == 0:
                self.start_reload()

        self.shoot_timer = NO_SHOOT

    def start_reload(self) -> None:
        """Begin reloading magazine if not already reloading."""
        # If already reloading or infinite ammo, no-op
        from common.config import AMMO_INFINITE

        if self.reload_timer is not None or self.current_ammo == AMMO_INFINITE:
            return

        self.reload_timer = self.reload_duration

    # Vision and detection

    def detect_enemies(self) -> set[int]:
        """
        Scan FOV cone and detect all visible enemies.

        Returns:
            Set of detected enemy agent IDs (opposite team only).
        """
        fov_radius = FOV_RATIO * self.state.radius
        center_angle = self.state.gun_angle
        half_opening = FOV_OPENING / 2
        start_angle = center_angle - half_opening

        detected: set[int] = set()
        angle_step = FOV_OPENING / FOV_NUM_RAYS

        for i in range(FOV_NUM_RAYS + 1):
            angle = start_angle + i * angle_step
            hit = self._cast_ray(
                self.state.x, self.state.y, angle, fov_radius
            )

            if hit and hit[1] == "agent":
                agent_id = hit[2]
                # Only detect opposite team agents
                if (
                    agent_id in self.agents_dict
                    and self.agents_dict[agent_id].state.team != self.state.team
                ):
                    detected.add(agent_id)

        self.detected_enemies = detected
        return detected

    def _cast_ray(
        self, start_x: float, start_y: float, angle: float, max_distance: float
    ) -> tuple[float, str, int] | None:
        """
        Cast ray and return first obstacle hit.

        Walls block rays. Agents are transparent to ray casting (only
        checked after ray reaches them).

        Args:
            start_x: Ray origin X.
            start_y: Ray origin Y.
            angle: Ray direction angle in radians.
            max_distance: Maximum ray distance.

        Returns:
            Tuple of (distance, hit_type, hit_id) or None.
            hit_type: "agent" or "wall".
        """
        dx = math.cos(angle)
        dy = -math.sin(angle)

        step_size = self.walls_state.grid_unit / RAY_STEP_DIVISOR
        current_x = start_x
        current_y = start_y
        traveled = 0.0

        fov_radius = FOV_RATIO * self.state.radius
        candidates: list[tuple[int, "Agent"]] = []

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
                return (traveled, "wall", None)

            for agent_id, agent in candidates:
                dist_sq = (current_x - agent.state.x) ** 2 + (
                    current_y - agent.state.y
                ) ** 2
                if dist_sq < agent.state.radius ** 2:
                    return (traveled, "agent", agent_id)

        return None

    def can_see(self, target_id: int) -> bool:
        """
        Quick check if specific agent is currently detected.

        Args:
            target_id: Agent ID to check.

        Returns:
            True if agent is in detected_enemies, False otherwise.
        """
        return target_id in self.detected_enemies

    def get_closest_enemy(self) -> int | None:
        """
        Get ID of closest detected alive enemy.

        Returns:
            Agent ID of closest enemy or None if no alive enemies detected.
        """
        if not self.detected_enemies:
            return None

        # Filter out dead agents
        alive_enemies = [
            aid
            for aid in self.detected_enemies
            if aid in self.agents_dict and self.agents_dict[aid].is_alive()
        ]

        if not alive_enemies:
            return None

        return min(
            alive_enemies,
            key=lambda aid: (
                self.agents_dict[aid].state.x - self.state.x
            ) ** 2
            + (self.agents_dict[aid].state.y - self.state.y) ** 2,
        )

    # Health and alive state

    def take_damage(self, amount: float) -> None:
        """
        Reduce agent health.

        Args:
            amount: Damage amount to apply.
        """
        self.health = max(0.0, self.health - amount)
        # Mirror to network-visible state so clients see updated health
        try:
            self.state.health = float(self.health)
        except Exception:
            pass

    def is_alive(self) -> bool:
        """
        Check if agent is still alive.

        Returns:
            True if health > 0, False otherwise.
        """
        return self.health > 0
