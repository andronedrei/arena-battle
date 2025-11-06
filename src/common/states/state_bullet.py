"""
common/states/state_bullet.py
Bullet state for client-server communication (rendering only).
"""

import struct


# Network protocol constants
MAX_BULLET_ID = 65535
MAX_BULLETS_COUNT = 65535
BULLET_PACKED_SIZE = 17  # Bytes per bullet: 2+4+4+4+2+1


class StateBullet:
    """
    Pure bullet data for network transmission.
    Clients only need position and basic properties for rendering.
    """

    def __init__(self, id_bullet: int, x: float, y: float,
                 radius: float = 5.0, owner_id: int = 0, team: int = 0):
        """Constructor."""
        self.id_bullet = id_bullet
        self.x = x
        self.y = y
        self.radius = radius
        self.owner_id = owner_id
        self.team = team

    def set_position(self, x: float, y: float):
        """Set bullet position."""
        self.x = x
        self.y = y

    def pack(self) -> bytes:
        """
        Pack for network transmission.

        Format:
        [2 bytes: id (uint16)]
        [4 bytes: x (float)]
        [4 bytes: y (float)]
        [4 bytes: radius (float)]
        [2 bytes: owner_id (uint16)]
        [1 byte: team (uint8)]
        """
        return struct.pack('!HfffHB', self.id_bullet, self.x, self.y,
                          self.radius, self.owner_id, self.team)

    @staticmethod
    def pack_bullets(bullets: list['StateBullet']) -> bytes:
        """Pack multiple bullets. Always returns bytes (empty if no bullets)."""
        num_bullets = len(bullets)
        if num_bullets > MAX_BULLETS_COUNT:
            raise ValueError(f"Too many bullets: {num_bullets}")

        data = bytearray()
        data.extend(struct.pack('!H', num_bullets))

        for bullet in bullets:
            data.extend(bullet.pack())

        return bytes(data)

    @staticmethod
    def unpack_bullets(data: bytes) -> list['StateBullet']:
        """Unpack bullets from network data."""
        if len(data) < 2:
            return []

        offset = 0
        num_bullets = struct.unpack('!H', data[offset:offset+2])[0]
        offset += 2

        expected_size = 2 + (num_bullets * BULLET_PACKED_SIZE)
        if len(data) != expected_size:
            raise ValueError(f"Invalid packet size")

        bullets = []
        for _ in range(num_bullets):
            id_bullet, x, y, radius, owner_id, team = struct.unpack(
                '!HfffHB', data[offset:offset + BULLET_PACKED_SIZE]
            )
            offset += BULLET_PACKED_SIZE

            if radius <= 0:
                raise ValueError(f"Invalid radius: {radius}")

            bullet = StateBullet(id_bullet, x, y, radius, owner_id, team)
            bullets.append(bullet)

        return bullets

    def __repr__(self) -> str:
        """String representation."""
        return (
            f"StateBullet(id={self.id_bullet}, pos=({self.x:.1f}, {self.y:.1f}), "
            f"r={self.radius}, owner={self.owner_id}, team={self.team})"
        )
