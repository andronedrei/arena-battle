"""
Visual representation of CTF flags.

Renders flags with team colors and carrier indicators.
"""

from pyglet.graphics import Batch, Group
from pyglet.shapes import Circle, Star
from pyglet.text import Label

from client.display.batch_object import BatchObject
from client.config import TEAM_COLORS


class DisplayCTFFlag(BatchObject):
    """
    Visual representation of a CTF flag.
    
    Displays flag position, team color, and carrier status.
    """
    
    def __init__(
        self,
        batch: Batch,
        team: int,
        x: float,
        y: float,
        group_order: int = 2,
    ) -> None:
        """
        Initialize CTF flag display.
        
        Args:
            batch: Pyglet batch for rendering.
            team: Team ID (1=Team A, 2=Team B).
            x: Initial X position.
            y: Initial Y position.
            group_order: Rendering layer order.
        """
        super().__init__(batch)
        
        self.team = team
        self.x = x
        self.y = y
        self.carrier_id = None
        
        # Get team color
        color = TEAM_COLORS.get(team, (255, 255, 255))
        
        # Flag pole (circle base)
        self.pole_base = self.register_sub_object(
            Circle(
                x=x,
                y=y,
                radius=8,
                color=color,
                batch=batch,
                group=Group(order=group_order),
            )
        )
        self.pole_base.opacity = 200
        
        # Flag itself (star shape)
        self.flag_shape = self.register_sub_object(
            Star(
                x=x,
                y=y + 15,
                outer_radius=12,
                inner_radius=6,
                num_spikes=5,
                rotation=0,
                color=color,
                batch=batch,
                group=Group(order=group_order),
            )
        )
        self.flag_shape.opacity = 255
        
        # Carrier indicator (hidden by default)
        self.carrier_label = self.register_sub_object(
            Label(
                "",
                x=x,
                y=y - 20,
                anchor_x="center",
                anchor_y="center",
                font_size=10,
                color=(255, 255, 100, 255),
                batch=batch,
                group=Group(order=group_order + 1),
            )
        )
    
    def update_position(self, x: float, y: float) -> None:
        """
        Update flag position.
        
        Args:
            x: New X position.
            y: New Y position.
        """
        self.x = x
        self.y = y
        
        # Update pole and flag positions
        self.pole_base.x = x
        self.pole_base.y = y
        
        self.flag_shape.x = x
        self.flag_shape.y = y + 15
        
        self.carrier_label.x = x
        self.carrier_label.y = y - 20
    
    def set_carrier(self, agent_id: int | None) -> None:
        """
        Update carrier status.
        
        Args:
            agent_id: ID of carrying agent, or None if flag is not carried.
        """
        self.carrier_id = agent_id
        
        if agent_id is not None:
            # Show carrier indicator
            self.carrier_label.text = f"↑ #{agent_id}"
            self.flag_shape.opacity = 180  # Dim flag slightly when carried
        else:
            # Hide carrier indicator
            self.carrier_label.text = ""
            self.flag_shape.opacity = 255
    
    def set_dropped(self, is_dropped: bool) -> None:
        """
        Visually indicate if flag is dropped.
        
        Args:
            is_dropped: True if flag is dropped on ground.
        """
        if is_dropped:
            # Pulse effect for dropped flag
            self.flag_shape.opacity = 150
            self.pole_base.opacity = 150
        else:
            self.flag_shape.opacity = 255
            self.pole_base.opacity = 200
    
    def delete(self) -> None:
        """Clean up rendering resources."""
        super().delete()
