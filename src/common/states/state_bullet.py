# External libraries
import struct


# Internal libraries
from common.config import (
    BULLET_PACKED_SIZE,
    MAX_BULLETS_COUNT,
)


class StateBullet:
    """
    Pure bullet state for network transmission.

    Contains only rendering data needed by clients. Game logic
    is handled server-side.
    """

    def __init__(
        self,
        id_bullet: int,
        x: float,
        y: float,
        radius: float = 5.0,
        owner_id: int = 0,
        team: int = 0,
    ) -> None:
        """
        Initialize bullet state.

        Args:
            id_bullet: Unique bullet identifier.
            x: X position in pixels.
            y: Y position in pixels.
            radius: Collision radius in pixels.
            owner_id: ID of entity that fired this bullet.
            team: Team affiliation.
        """
        self.id_bullet = id_bullet
        self.x = x
        self.y = y
        self.radius = radius
        self.owner_id = owner_id
        self.team = team

    # State modification

    def set_position(self, x: float, y: float) -> None:
        """
        Update bullet position.

        Args:
            x: New X position in pixels.
            y: New Y position in pixels.
        """
        self.x = x
        self.y = y

    # Serialization

    def pack(self) -> bytes:
        """
        Serialize bullet to binary format.

        Format: [id:uint16][x:float][y:float][radius:float]
                [owner_id:uint16][team:uint8]

        Returns:
            Packed binary data (17 bytes).
        """
        return struct.pack(
            "!HfffHB",
            self.id_bullet,
            self.x,
            self.y,
            self.radius,
            self.owner_id,
            self.team,
        )

    @staticmethod
    def pack_bullets(bullets: list["StateBullet"]) -> bytes:
        """
        Serialize multiple bullets.

        Args:
            bullets: List of StateBullet objects to pack.

        Returns:
            Packed binary data with bullet count header.

        Raises:
            ValueError: If too many bullets to fit in packet.
        """
        num_bullets = len(bullets)
        if num_bullets > MAX_BULLETS_COUNT:
            raise ValueError(
                f"Too many bullets: {num_bullets} "
                f"(max {MAX_BULLETS_COUNT})"
            )

        data = bytearray()
        data.extend(struct.pack("!H", num_bullets))

        for bullet in bullets:
            data.extend(bullet.pack())

        return bytes(data)

    @staticmethod
    def unpack_bullets(data: bytes) -> list["StateBullet"]:
        """
        Deserialize bullets from binary data.

        Args:
            data: Packed binary data from network.

        Returns:
            List of StateBullet objects.

        Raises:
            ValueError: If packet format or data is invalid.
        """
        if len(data) < 2:
            return []

        offset = 0
        num_bullets = struct.unpack("!H", data[offset: offset + 2])[0]
        offset += 2

        expected_size = 2 + (num_bullets * BULLET_PACKED_SIZE)
        if len(data) != expected_size:
            raise ValueError(
                f"Invalid packet size: expected {expected_size}, "
                f"got {len(data)}"
            )

        bullets = []
        for _ in range(num_bullets):
            (
                id_bullet,
                x,
                y,
                radius,
                owner_id,
                team,
            ) = struct.unpack(
                "!HfffHB", data[offset: offset + BULLET_PACKED_SIZE]
            )
            offset += BULLET_PACKED_SIZE

            if radius <= 0:
                raise ValueError(f"Invalid radius: {radius}")

            bullet = StateBullet(id_bullet, x, y, radius, owner_id, team)
            bullets.append(bullet)

        return bullets

    # Representation

    def __repr__(self) -> str:
        """Return a string representation of the bullet."""
        return (
            f"StateBullet(id={self.id_bullet}, "
            f"pos=({self.x:.1f}, {self.y:.1f}), "
            f"r={self.radius}, owner={self.owner_id}, team={self.team})"
        )
