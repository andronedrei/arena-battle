"""
CTF game state for network transmission.

Tracks flag positions, carriers, captures, and game timer.
"""

import struct
import json
from typing import Optional


class StateCTFFlag:
    """
    State of a single CTF flag.
    
    Tracks position, carrier, and base status.
    """
    
    def __init__(
        self,
        x: float = 0.0,
        y: float = 0.0,
        carrier_id: Optional[int] = None,
        at_base: bool = True,
    ) -> None:
        """
        Initialize flag state.
        
        Args:
            x: Flag X position.
            y: Flag Y position.
            carrier_id: ID of agent carrying flag (None if not carried).
            at_base: Whether flag is at its base.
        """
        self.x = x
        self.y = y
        self.carrier_id = carrier_id
        self.at_base = at_base
    
    def to_dict(self) -> dict:
        """
        Convert flag state to dictionary.
        
        Returns:
            Dictionary representation of flag state.
        """
        return {
            "x": self.x,
            "y": self.y,
            "carrier": self.carrier_id,
            "at_base": self.at_base,
        }


class StateCTF:
    """
    Pure CTF game state for network transmission.
    
    Contains flag positions, captures, and timer information.
    """
    
    def __init__(
        self,
        team_a_captures: int = 0,
        team_b_captures: int = 0,
        flag_team_a: Optional[StateCTFFlag] = None,
        flag_team_b: Optional[StateCTFFlag] = None,
        time_elapsed: float = 0.0,
        max_time: float = 0.0,
        max_captures: int = 3,
        game_over: bool = False,
        winner_team: int = 0,
    ) -> None:
        """
        Initialize CTF state.
        
        Args:
            team_a_captures: Number of flags Team A has captured.
            team_b_captures: Number of flags Team B has captured.
            flag_team_a: State of Team A's flag.
            flag_team_b: State of Team B's flag.
            time_elapsed: Time elapsed since game start (seconds).
            max_time: Maximum game duration (seconds, 0 = unlimited).
            max_captures: Captures needed to win.
            game_over: Whether the game has ended.
            winner_team: Team ID of winner (0 if no winner yet).
        """
        self.team_a_captures = team_a_captures
        self.team_b_captures = team_b_captures
        self.flag_team_a = flag_team_a or StateCTFFlag()
        self.flag_team_b = flag_team_b or StateCTFFlag()
        self.time_elapsed = time_elapsed
        self.max_time = max_time
        self.max_captures = max_captures
        self.game_over = game_over
        self.winner_team = winner_team
    
    # Serialization (using JSON for flexibility with nullable carrier_id)
    
    def pack(self) -> bytes:
        """
        Serialize CTF state to JSON bytes.
        
        Returns:
            JSON-encoded binary data.
        """
        data = {
            "team_a_captures": self.team_a_captures,
            "team_b_captures": self.team_b_captures,
            "flag_team_a": self.flag_team_a.to_dict(),
            "flag_team_b": self.flag_team_b.to_dict(),
            "time_elapsed": self.time_elapsed,
            "max_time": self.max_time,
            "max_captures": self.max_captures,
            "game_over": self.game_over,
            "winner_team": self.winner_team,
        }
        return json.dumps(data).encode('utf-8')
    
    @staticmethod
    def unpack(data: bytes) -> "StateCTF":
        """
        Deserialize CTF state from JSON data.
        
        Args:
            data: JSON-encoded binary data from network.
        
        Returns:
            StateCTF object.
        
        Raises:
            ValueError: If packet format is invalid.
        """
        try:
            json_data = json.loads(data.decode('utf-8'))
            
            # Parse flag states
            flag_a_data = json_data.get("flag_team_a", {})
            flag_a = StateCTFFlag(
                x=flag_a_data.get("x", 0.0),
                y=flag_a_data.get("y", 0.0),
                carrier_id=flag_a_data.get("carrier"),
                at_base=flag_a_data.get("at_base", True),
            )
            
            flag_b_data = json_data.get("flag_team_b", {})
            flag_b = StateCTFFlag(
                x=flag_b_data.get("x", 0.0),
                y=flag_b_data.get("y", 0.0),
                carrier_id=flag_b_data.get("carrier"),
                at_base=flag_b_data.get("at_base", True),
            )
            
            return StateCTF(
                team_a_captures=json_data.get("team_a_captures", 0),
                team_b_captures=json_data.get("team_b_captures", 0),
                flag_team_a=flag_a,
                flag_team_b=flag_b,
                time_elapsed=json_data.get("time_elapsed", 0.0),
                max_time=json_data.get("max_time", 0.0),
                max_captures=json_data.get("max_captures", 3),
                game_over=json_data.get("game_over", False),
                winner_team=json_data.get("winner_team", 0),
            )
        
        except (json.JSONDecodeError, KeyError, TypeError) as e:
            raise ValueError(f"Invalid CTF packet: {e}")
    
    # Representation
    
    def __repr__(self) -> str:
        """Return string representation of CTF state."""
        return (
            f"StateCTF(A={self.team_a_captures}, B={self.team_b_captures}, "
            f"time={self.time_elapsed:.1f}s, over={self.game_over})"
        )
