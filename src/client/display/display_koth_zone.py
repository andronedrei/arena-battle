"""
Visual representation of KOTH hill zone.

Renders the hill zone with color based on control status.
"""

from pyglet.graphics import Batch, Group
from pyglet.shapes import Circle, Rectangle, BorderedRectangle

from client.display.batch_object import BatchObject

from common.koth_config import (
    KOTH_ZONE_CENTER_X,
    KOTH_ZONE_CENTER_Y,
    KOTH_ZONE_RADIUS,
    KOTH_ZONE_RECT_X,
    KOTH_ZONE_RECT_Y,
    KOTH_ZONE_RECT_WIDTH,
    KOTH_ZONE_RECT_HEIGHT,
    KOTH_ZONE_SHAPE,
    KOTH_ZONE_NEUTRAL_COLOR,
    KOTH_ZONE_TEAM_A_COLOR,
    KOTH_ZONE_TEAM_B_COLOR,
    KOTH_ZONE_CONTESTED_COLOR,
    KOTH_ZONE_OPACITY,
    KOTH_ZONE_BORDER_WIDTH,
    KOTH_ZONE_BORDER_COLOR,
)
from common.states.state_koth import KOTHZoneStatus


class DisplayKOTHZone(BatchObject):
    """
    Visual representation of the KOTH hill zone.
    
    Renders zone shape and updates color based on control status.
    """
    
    def __init__(
        self,
        batch: Batch,
        group_order: int = 1,
    ) -> None:
        """
        Initialize KOTH zone display.
        
        Args:
            batch: Pyglet batch for rendering.
            group_order: Rendering layer order.
        """
        super().__init__(batch)
        
        self.zone_status = KOTHZoneStatus.NEUTRAL
        
        # Create zone shape
        if KOTH_ZONE_SHAPE == "circle":
            self.zone_shape = self.register_sub_object(
                Circle(
                    KOTH_ZONE_CENTER_X,
                    KOTH_ZONE_CENTER_Y,
                    KOTH_ZONE_RADIUS,
                    color=KOTH_ZONE_NEUTRAL_COLOR,
                    batch=batch,
                    group=Group(order=group_order),
                )
            )
            self.zone_shape.opacity = KOTH_ZONE_OPACITY
            
        elif KOTH_ZONE_SHAPE == "rectangle":
            self.zone_shape = self.register_sub_object(
                BorderedRectangle(
                    KOTH_ZONE_RECT_X,
                    KOTH_ZONE_RECT_Y,
                    KOTH_ZONE_RECT_WIDTH,
                    KOTH_ZONE_RECT_HEIGHT,
                    border=KOTH_ZONE_BORDER_WIDTH,
                    color=KOTH_ZONE_NEUTRAL_COLOR,
                    border_color=KOTH_ZONE_BORDER_COLOR,
                    batch=batch,
                    group=Group(order=group_order),
                )
            )
            self.zone_shape.opacity = KOTH_ZONE_OPACITY
    
    def update_status(self, zone_status: int) -> None:
        """
        Update zone visual based on control status.
        
        Args:
            zone_status: KOTHZoneStatus value.
        """
        if self.zone_status == zone_status:
            return
        
        self.zone_status = zone_status
        
        # Update color based on status
        if zone_status == KOTHZoneStatus.NEUTRAL:
            self.zone_shape.color = KOTH_ZONE_NEUTRAL_COLOR
        elif zone_status == KOTHZoneStatus.TEAM_A:
            self.zone_shape.color = KOTH_ZONE_TEAM_A_COLOR
        elif zone_status == KOTHZoneStatus.TEAM_B:
            self.zone_shape.color = KOTH_ZONE_TEAM_B_COLOR
        elif zone_status == KOTHZoneStatus.CONTESTED:
            self.zone_shape.color = KOTH_ZONE_CONTESTED_COLOR
    
    def delete(self) -> None:
        """Clean up rendering resources."""
        super().delete()