# External libraries
import math


# Internal libraries
from common.config import MAX_BULLET_ID
from common.states.state_bullet import StateBullet


class Bullet:
    """
    Server-side bullet with physics simulation.

    Manages velocity, damage, and lifetime. Wraps StateBullet for
    network transmission.
    """

    # Class-level ID counter with wraparound
    _next_id = 0

    @staticmethod
    def get_next_id() -> int:
        """
        Get next unique bullet ID and increment counter.

        Wraps around at MAX_BULLET_ID to prevent overflow.

        Returns:
            Next available bullet ID.
        """
        bullet_id = Bullet._next_id
        Bullet._next_id = (Bullet._next_id + 1) % (MAX_BULLET_ID + 1)
        return bullet_id

    # Initialization

    def __init__(
        self,
        x: float,
        y: float,
        speed: float,
        angle: float,
        owner_id: int,
        team: int,
        damage: float = 10.0,
        lifetime: float = 10.0,
        radius: float = 5.0,
    ) -> None:
        """
        Initialize a bullet with auto-generated ID.

        Args:
            x: Initial X position in pixels.
            y: Initial Y position in pixels.
            speed: Velocity magnitude in pixels/second.
            angle: Direction angle in radians.
            owner_id: ID of the entity that fired this bullet.
            team: Team affiliation.
            damage: Damage dealt on hit.
            lifetime: Time in seconds before expiration.
            radius: Collision radius in pixels.
        """
        id_bullet = Bullet.get_next_id()
        self.state = StateBullet(id_bullet, x, y, radius, owner_id, team)

        self.vx = speed * math.cos(angle)
        self.vy = -speed * math.sin(angle)

        self.damage = damage
        self.lifetime = lifetime
        self.age = 0.0

    # Updates

    def update(self, dt: float) -> None:
        """
        Update bullet position and age.

        Args:
            dt: Delta time in seconds.
        """
        self.state.x += self.vx * dt
        self.state.y += self.vy * dt
        self.age += dt

    # Queries

    def is_alive(self) -> bool:
        """
        Check if bullet is still active.

        Returns:
            True if age is within lifetime, False otherwise.
        """
        return self.age < self.lifetime

    # Representation

    def __repr__(self) -> str:
        """Return a string representation of the bullet."""
        return (
            f"Bullet(id={self.state.id_bullet}, "
            f"pos=({self.state.x:.1f}, {self.state.y:.1f}), "
            f"vel=({self.vx:.1f}, {self.vy:.1f}), "
            f"dmg={self.damage}, age={self.age:.2f}/{self.lifetime})"
        )
