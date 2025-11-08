# External libraries
import struct
from enum import IntEnum


# Internal libraries
from common.config import (
    DEFAULT_ENTITY_RADIUS,
    MAX_ENTITY_ID,
    MAX_ENTITIES_COUNT,
    ENTITY_PACKED_SIZE,
    AMMO_INFINITE,
)


class Team(IntEnum):
    """Team/ownership identifiers for entities."""

    NEUTRAL = 0
    TEAM_A = 1
    TEAM_B = 2


class StateEntity:
    """
    Pure entity state for network transmission.

    Stores position, radius, team, and gun angle for rendering.
    Does not contain game logic, only serializable state.
    """

    def __init__(
        self,
        id_entity: int,
        x: float,
        y: float,
        radius: float = DEFAULT_ENTITY_RADIUS,
        team: int = Team.NEUTRAL,
        gun_angle: float = 0.0,
        health: float = 0.0,
        ammo: int = AMMO_INFINITE,
    ) -> None:
        """
        Initialize entity state.

        Args:
            id_entity: Unique entity identifier.
            x: X position in pixels.
            y: Y position in pixels.
            radius: Collision radius in pixels.
            team: Team affiliation (Team enum value).
            gun_angle: Gun angle in radians.
        """
        self.id_entity = id_entity
        self.x = x
        self.y = y
        self.radius = radius
        self.team = team
        self.gun_angle = gun_angle
        # Gameplay state values (sent over network)
        self.health = health
        # Ammo is uint16 in network. Use AMMO_INFINITE as sentinel for unlimited.
        self.ammo = ammo

    # State modification

    def set_position(self, x: float, y: float) -> None:
        """
        Update entity position.

        Args:
            x: New X position in pixels.
            y: New Y position in pixels.
        """
        self.x = x
        self.y = y

    def set_gun_angle(self, angle: float) -> None:
        """
        Update gun angle.

        Args:
            angle: New angle in radians.
        """
        self.gun_angle = angle

    # Serialization

    def pack(self) -> bytes:
        """
        Serialize entity to binary format.

        Format: [id:uint16][x:float][y:float][radius:float]
                [gun_angle:float][team:uint8][health:float][ammo:uint16]

        Returns:
            Packed binary data (ENTITY_PACKED_SIZE bytes).
        """
        return struct.pack(
            "!HffffBfH",
            self.id_entity,
            self.x,
            self.y,
            self.radius,
            self.gun_angle,
            self.team,
            float(self.health),
            int(self.ammo),
        )

    @staticmethod
    def pack_entities(entities: list["StateEntity"]) -> bytes:
        """
        Serialize multiple entities.

        Args:
            entities: List of StateEntity objects to pack.

        Returns:
            Packed binary data with entity count header.

        Raises:
            ValueError: If too many entities to fit in packet.
        """
        num_entities = len(entities)
        if num_entities > MAX_ENTITIES_COUNT:
            raise ValueError(
                f"Too many entities: {num_entities} "
                f"(max {MAX_ENTITIES_COUNT})"
            )

        data = bytearray()
        data.extend(struct.pack("!H", num_entities))

        for entity in entities:
            data.extend(entity.pack())

        return bytes(data)

    @staticmethod
    def unpack_entities(data: bytes) -> list["StateEntity"]:
        """
        Deserialize entities from binary data.

        Args:
            data: Packed binary data from network.

        Returns:
            List of StateEntity objects.

        Raises:
            ValueError: If packet format or data is invalid.
        """
        if len(data) < 2:
            return []

        offset = 0
        num_entities = struct.unpack("!H", data[offset: offset + 2])[0]
        offset += 2

        expected_size = 2 + (num_entities * ENTITY_PACKED_SIZE)
        if len(data) != expected_size:
            raise ValueError(
                f"Invalid packet size: expected {expected_size}, "
                f"got {len(data)}"
            )

        entities = []
        for _ in range(num_entities):
            (
                id_entity,
                x,
                y,
                radius,
                gun_angle,
                team,
                health,
                ammo,
            ) = struct.unpack(
                "!HffffBfH", data[offset: offset + ENTITY_PACKED_SIZE]
            )
            offset += ENTITY_PACKED_SIZE

            # Validate unpacked values
            if radius <= 0:
                raise ValueError(f"Invalid radius: {radius}")
            if not (0 <= id_entity <= MAX_ENTITY_ID):
                raise ValueError(f"Invalid entity ID: {id_entity}")
            if team not in [t.value for t in Team]:
                raise ValueError(f"Invalid team: {team}")

            entity = StateEntity(
                id_entity,
                x,
                y,
                radius,
                team,
                gun_angle,
                health,
                ammo,
            )
            entities.append(entity)

        return entities

    # Representation

    def __repr__(self) -> str:
        """Return a string representation of the entity."""
        team_names = {
            Team.NEUTRAL: "neutral",
            Team.TEAM_A: "team_A",
            Team.TEAM_B: "team_B",
        }
        team_name = team_names.get(self.team, f"team_{self.team}")
        return (
            f"StateEntity(id={self.id_entity}, "
            f"pos=({self.x:.1f}, {self.y:.1f}), "
            f"r={self.radius}, angle={self.gun_angle:.2f}, "
            f"team={team_name})"
        )
