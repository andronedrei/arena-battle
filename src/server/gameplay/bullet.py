"""
server/gameplay/bullet.py
Server-side bullet with physics and gameplay logic.
"""

from common.states.state_bullet import StateBullet


class Bullet:
    """
    Server-side bullet with velocity, damage, and lifetime.
    Wraps StateBullet for network transmission.
    """

    def __init__(self, id_bullet: int, x: float, y: float,
                 vx: float, vy: float, owner_id: int, team: int,
                 damage: float = 10.0, lifetime: float = 5.0,
                 radius: float = 5.0):
        """
        Initialize bullet.

        Args:
            id_bullet: Unique bullet identifier
            x, y: Initial position
            vx, vy: Velocity components (pixels per second)
            owner_id: ID of agent that fired this bullet
            team: Team that owns this bullet
            damage: Damage dealt on hit
            lifetime: Time in seconds before bullet expires
            radius: Collision radius
        """
        self.state = StateBullet(id_bullet, x, y, radius, owner_id, team)
        self.vx = vx
        self.vy = vy
        self.damage = damage
        self.lifetime = lifetime
        self.age = 0.0

    def update(self, dt: float):
        """
        Update bullet position and age.

        Args:
            dt: Delta time in seconds
        """
        self.state.x += self.vx * dt
        self.state.y += self.vy * dt
        self.age += dt

    def is_alive(self) -> bool:
        """Check if bullet should still exist."""
        return self.age < self.lifetime

    def __repr__(self) -> str:
        """String representation."""
        return (
            f"Bullet(id={self.state.id_bullet}, pos=({self.state.x:.1f}, {self.state.y:.1f}), "
            f"vel=({self.vx:.1f}, {self.vy:.1f}), dmg={self.damage}, "
            f"age={self.age:.2f}/{self.lifetime})"
        )
