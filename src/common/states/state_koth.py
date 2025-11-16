"""
KOTH game state for network transmission.

Tracks team scores, zone control, and game timer.
"""

import struct
from enum import IntEnum


class KOTHZoneStatus(IntEnum):
    """Zone control status."""
    NEUTRAL = 0
    TEAM_A = 1
    TEAM_B = 2
    CONTESTED = 3


class StateKOTH:
    """
    Pure KOTH game state for network transmission.
    
    Contains scores, zone status, and timer information.
    """
    
    def __init__(
        self,
        team_a_score: float = 0.0,
        team_b_score: float = 0.0,
        zone_status: int = KOTHZoneStatus.NEUTRAL,
        time_elapsed: float = 0.0,
        game_over: bool = False,
        winner_team: int = 0,
    ) -> None:
        """
        Initialize KOTH state.
        
        Args:
            team_a_score: Team A's accumulated points.
            team_b_score: Team B's accumulated points.
            zone_status: Current zone control status.
            time_elapsed: Time elapsed since game start (seconds).
            game_over: Whether the game has ended.
            winner_team: Team ID of winner (0 if no winner yet).
        """
        self.team_a_score = team_a_score
        self.team_b_score = team_b_score
        self.zone_status = zone_status
        self.time_elapsed = time_elapsed
        self.game_over = game_over
        self.winner_team = winner_team
    
    # Serialization
    
    def pack(self) -> bytes:
        """
        Serialize KOTH state to binary format.
        
        Format: [team_a_score:float][team_b_score:float]
                [zone_status:uint8][time_elapsed:float]
                [game_over:uint8][winner_team:uint8]
        
        Returns:
            Packed binary data (18 bytes).
        """
        return struct.pack(
            "!ffBfBB",
            self.team_a_score,
            self.team_b_score,
            self.zone_status,
            self.time_elapsed,
            1 if self.game_over else 0,
            self.winner_team,
        )
    
    @staticmethod
    def unpack(data: bytes) -> "StateKOTH":
        """
        Deserialize KOTH state from binary data.
        
        Args:
            data: Packed binary data from network.
        
        Returns:
            StateKOTH object.
        
        Raises:
            ValueError: If packet format is invalid.
        """
        if len(data) != 18:
            raise ValueError(
                f"Invalid KOTH packet size: expected 18, got {len(data)}"
            )
        
        (
            team_a_score,
            team_b_score,
            zone_status,
            time_elapsed,
            game_over_byte,
            winner_team,
        ) = struct.unpack("!ffBfBB", data)
        
        return StateKOTH(
            team_a_score=team_a_score,
            team_b_score=team_b_score,
            zone_status=zone_status,
            time_elapsed=time_elapsed,
            game_over=bool(game_over_byte),
            winner_team=winner_team,
        )
    
    # Representation
    
    def __repr__(self) -> str:
        """Return string representation of KOTH state."""
        return (
            f"StateKOTH(A={self.team_a_score:.1f}, B={self.team_b_score:.1f}, "
            f"zone={KOTHZoneStatus(self.zone_status).name}, "
            f"time={self.time_elapsed:.1f}s, over={self.game_over})"
        )