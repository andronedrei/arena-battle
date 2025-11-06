# server/gameplay/bullet.py
from common.states.state_bullet import StateBullet, MAX_BULLET_ID
import math


class Bullet:
    """
    Server-side bullet with velocity, damage, and lifetime.
    Wraps StateBullet for network transmission.
    """
    
    # Static counter for unique bullet IDs
    _next_id = 0

    @staticmethod
    def get_next_id() -> int:
        """Get next bullet ID and increment counter."""
        bullet_id = Bullet._next_id
        Bullet._next_id = (Bullet._next_id + 1) % (MAX_BULLET_ID + 1)
        return bullet_id

    def __init__(self, x: float, y: float,
                 speed: float, angle: float, owner_id: int, team: int,
                 damage: float = 10.0, lifetime: float = 10,
                 radius: float = 5.0):
        """
        Initialize bullet (ID auto-generated).

        Args:
            x, y: Initial position
            speed: Bullet velocity magnitude (pixels/sec)
            angle: Direction angle in radians
            owner_id: ID of agent that fired this bullet
            team: Team that owns this bullet
            damage: Damage dealt on hit
            lifetime: Time in seconds before bullet expires
            radius: Collision radius
        """
        id_bullet = Bullet.get_next_id()
        self.state = StateBullet(id_bullet, x, y, radius, owner_id, team)
        
        self.vx = speed * math.cos(angle)
        self.vy = -speed * math.sin(angle)
        
        self.damage = damage
        self.lifetime = lifetime
        self.age = 0.0

    def update(self, dt: float):
        """Update bullet position and age."""
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
