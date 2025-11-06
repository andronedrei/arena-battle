# External libraries
from abc import ABC, abstractmethod


class Strategy(ABC):
    """
    Base class for agent behavior strategies.

    Subclasses implement custom decision-making logic for agents
    using the provided agent API.
    """

    @abstractmethod
    def execute(self, agent, dt: float) -> None:
        """
        Execute strategy logic for one frame.

        Called each simulation frame. Strategy has full access to agent
        API for perception (detect_enemies, can_see) and actions
        (move, load_bullet, point_gun_at, etc.).

        Args:
            agent: Agent instance to control.
            dt: Delta time in seconds.
        """
        pass
