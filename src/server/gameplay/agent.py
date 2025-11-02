# server/logic/agent.py
from common.states.state_entity import StateEntity
from common.states.state_walls import StateWalls
from common.config import FOV_RATIO, FOV_OPENING, FOV_NUM_RAYS
from common.config import RAY_STEP_DIVISOR
import math


class Agent:
    """
    Server-side agent logic with vision/detection system.
    Uses StateEntity for state management, adds detection capabilities.
    """

    def __init__(self, entity_state: StateEntity, walls_state: StateWalls):
        """
        Args:
            entity_state: The entity's state (position, angle, radius)
            walls_state: World walls for ray casting
        """
        self.state = entity_state
        self.walls_state = walls_state
        self.detected_enemies = set()

    def cast_ray(self, start_x, start_y, angle, max_distance, agents_dict):
        """
        Cast ray and return first obstacle hit (wall or agent).
        Agents don't block each other (transparent), only walls block.
        
        Returns:
            (distance, hit_type, hit_id) or None
            hit_type: 'agent' or 'wall'
        """
        dx = math.cos(angle)
        dy = -math.sin(angle)  # Negate for Pyglet Y-axis
        
        step_size = self.walls_state.grid_unit / RAY_STEP_DIVISOR
        current_x = start_x
        current_y = start_y
        traveled = 0
        
        # Pre-filter: collect agents within FOV range (bounding box optimization)
        fov_radius = FOV_RATIO * self.state.radius
        candidates = []
        
        for agent_id, agent in agents_dict.items():
            if agent_id == self.state.id_entity:
                continue
            
            # Squared distance avoids expensive sqrt()
            dx_agent = agent.state.x - start_x
            dy_agent = agent.state.y - start_y
            dist_sq = dx_agent * dx_agent + dy_agent * dy_agent
            
            # Include if within FOV range + agent radius buffer
            if dist_sq < (fov_radius + agent.state.radius) ** 2:
                candidates.append((agent_id, agent))
        
        # Ray march - check for collisions along ray path
        while traveled < max_distance:
            current_x += dx * step_size
            current_y += dy * step_size
            traveled += step_size
            
            # Check walls first - they block everything
            if self.walls_state.has_wall_at_pos(current_x, current_y):
                return (traveled, 'wall', None)
            
            # Check candidate agents (agents don't block each other)
            for agent_id, agent in candidates:
                dist_sq = (current_x - agent.state.x) ** 2 + (current_y - agent.state.y) ** 2
                if dist_sq < agent.state.radius ** 2:
                    return (traveled, 'agent', agent_id)
        
        return None

    def detect_enemies(self, agents_dict):
        """
        Scan FOV cone and detect all visible enemies.
        Casts FOV_NUM_RAYS rays; walls block, agents don't.
        
        Returns:
            Set of detected agent IDs
        """
        fov_radius = FOV_RATIO * self.state.radius
        center_angle = self.state.gun_angle
        half_opening = FOV_OPENING / 2
        start_angle = center_angle - half_opening
        
        detected = set()
        angle_step = FOV_OPENING / FOV_NUM_RAYS
        
        # Cast rays across entire FOV cone
        for i in range(FOV_NUM_RAYS + 1):
            angle = start_angle + i * angle_step
            hit = self.cast_ray(self.state.x, self.state.y, angle, fov_radius, agents_dict)
            
            # Add any detected agents to set
            if hit and hit[1] == 'agent':
                detected.add(hit[2])
        
        self.detected_enemies = detected
        return detected

    def can_see(self, target_id) -> bool:
        """Quick check if specific agent is currently detected."""
        return target_id in self.detected_enemies
