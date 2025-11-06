# server/strategy/base.py
from abc import ABC, abstractmethod


class Strategy(ABC):
    """Base template class for agent behavior strategies."""
    
    @abstractmethod
    def execute(self, agent, dt: float):
        """
        Execute strategy logic.
        
        Args:
            agent: Agent instance with full API access
            dt: Delta time in seconds
        
        Strategy has access to:
        - agent.state (position, angle, team, etc.)
        - agent.detected_enemies (set of visible enemy IDs)
        - agent.move(dt, direction)
        - agent.load_bullet()
        - agent.can_see(target_id)
        - agent.detect_enemies()
        - And all other public methods
        """
        pass
