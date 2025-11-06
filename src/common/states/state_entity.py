"""
state_entity.py
Pure entity state for network transmission only.
"""

from enum import IntEnum
import struct
from common.config import DEFAULT_ENTITY_RADIUS


# Network protocol constants
MAX_ENTITY_ID = 65535
MAX_ENTITIES_COUNT = 65535
ENTITY_PACKED_SIZE = 19  # 2+4+4+4+4+1


class Team(IntEnum):
    """Team/ownership identifiers for entities."""
    NEUTRAL = 0
    TEAM_A = 1
    TEAM_B = 2


class StateEntity:
    """
    Pure entity data for network transmission.
    Stores position, radius, team, gun angle for rendering.
    """

    def __init__(self, id_entity: int, x: float, y: float,
                 radius: float = DEFAULT_ENTITY_RADIUS,
                 team: int = Team.NEUTRAL, gun_angle: float = 0.0):
        """Constructor."""
        self.id_entity = id_entity
        self.x = x
        self.y = y
        self.radius = radius
        self.team = team
        self.gun_angle = gun_angle

    def set_position(self, x: float, y: float):
        """Set entity position."""
        self.x = x
        self.y = y

    def set_gun_angle(self, angle: float):
        """Set gun angle in radians."""
        self.gun_angle = angle

    def pack(self) -> bytes:
        """
        Pack entity state into binary format.

        Format:
        [2 bytes: id (uint16)]
        [4 bytes: x (float)]
        [4 bytes: y (float)]
        [4 bytes: radius (float)]
        [4 bytes: gun_angle (float)]
        [1 byte: team (uint8)]
        """
        return struct.pack('!HffffB', self.id_entity, self.x, self.y,
                           self.radius, self.gun_angle, self.team)

    @staticmethod
    def pack_entities(entities: list['StateEntity']) -> bytes:
        """Pack multiple entities. Always returns bytes (empty if no entities)."""
        num_entities = len(entities)
        if num_entities > MAX_ENTITIES_COUNT:
            raise ValueError(f"Too many entities: {num_entities}")

        data = bytearray()
        data.extend(struct.pack('!H', num_entities))

        for entity in entities:
            data.extend(entity.pack())

        return bytes(data)

    @staticmethod
    def unpack_entities(data: bytes) -> list['StateEntity']:
        """Unpack entities from network data."""
        if len(data) < 2:
            return []

        offset = 0
        num_entities = struct.unpack('!H', data[offset:offset+2])[0]
        offset += 2

        expected_size = 2 + (num_entities * ENTITY_PACKED_SIZE)
        if len(data) != expected_size:
            raise ValueError(f"Invalid packet size")

        entities = []
        for _ in range(num_entities):
            id_entity, x, y, radius, gun_angle, team = struct.unpack(
                '!HffffB', data[offset:offset + ENTITY_PACKED_SIZE]
            )
            offset += ENTITY_PACKED_SIZE

            if radius <= 0:
                raise ValueError(f"Invalid radius: {radius}")
            if not (0 <= id_entity <= MAX_ENTITY_ID):
                raise ValueError(f"Invalid entity ID: {id_entity}")
            if team not in [t.value for t in Team]:
                raise ValueError(f"Invalid team: {team}")

            entity = StateEntity(id_entity, x, y, radius, team, gun_angle)
            entities.append(entity)

        return entities

    def __repr__(self) -> str:
        """String representation."""
        team_names = {
            Team.NEUTRAL: "neutral",
            Team.TEAM_A: "team_A",
            Team.TEAM_B: "team_B"
        }
        team_name = team_names.get(self.team, f"team_{self.team}")
        return (
            f"StateEntity(id={self.id_entity}, pos=({self.x:.1f}, {self.y:.1f}), "
            f"r={self.radius}, angle={self.gun_angle:.2f}, team={team_name})"
        )
