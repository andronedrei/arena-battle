# === INTERNAL HELPERS ===
from enum import IntEnum

class CollisionType(IntEnum):
    """Types of obstacles."""
    NONE = 0
    WALL = 1
    AGENT = 2
    BULLET = 3

def _circles_overlap(x1: float, y1: float, r1: float,
                    x2: float, y2: float, r2: float) -> bool:
    """Check if two circles overlap."""
    dx = x1 - x2
    dy = y1 - y2
    distance_squared = dx * dx + dy * dy
    min_distance = r1 + r2
    return distance_squared < min_distance * min_distance


def _circle_hits_wall(x: float, y: float, radius: float, 
                     walls_state) -> bool:
    """Check if circle overlaps any wall cells."""
    cx_min, cy_min = walls_state.to_cell(x - radius, y - radius)
    cx_max, cy_max = walls_state.to_cell(x + radius, y + radius)
    
    for cx in range(cx_min, cx_max + 1):
        for cy in range(cy_min, cy_max + 1):
            if walls_state.has_wall(cx, cy):
                return True
    
    return False


# === CALLED EXTERNALLY ===

def check_move_validity(x: float, y: float, radius: float,
                        agents_dict, walls_state, 
                        exclude_id: int = None) -> tuple[CollisionType, int | None]:
    """
    Check if move is valid. Returns collision type and obstacle ID.
    
    Returns:
        (CollisionType, obstacle_id_or_coord)
        - (NONE, None) if can move
        - (WALL, None) if wall collision
        - (AGENT, agent_id) if agent collision
    """
    # Check walls
    if _circle_hits_wall(x, y, radius, walls_state):
        return (CollisionType.WALL, None)
    
    # Check agents
    for agent_id, agent in agents_dict.items():
        if exclude_id == agent_id:
            continue
        if _circles_overlap(x, y, radius, agent.state.x, agent.state.y, agent.state.radius):
            return (CollisionType.AGENT, agent_id)
    
    return (CollisionType.NONE, None)


def find_bullet_agent_collisions(bullets_dict, agents_dict) -> dict:
    """Find all bullet-agent collisions (opposite team only)."""
    hits = {}
    
    for bullet_id, bullet in bullets_dict.items():
        hits[bullet_id] = []
        
        for agent_id, agent in agents_dict.items():
            # Skip owner
            if agent_id == bullet.state.owner_id:
                continue
            
            # Skip same team - only opposite team collides
            if agent.state.team == bullet.state.team:
                continue
            
            if _circles_overlap(bullet.state.x, bullet.state.y, bullet.state.radius,
                               agent.state.x, agent.state.y, agent.state.radius):
                hits[bullet_id].append(agent_id)
    
    return hits


def find_bullet_wall_collisions(bullets_dict, walls_state) -> list[int]:
    """Find all bullet-wall collisions."""
    destroyed_bullets = []
    
    for bullet_id, bullet in bullets_dict.items():
        if _circle_hits_wall(bullet.state.x, bullet.state.y, bullet.state.radius, walls_state):
            destroyed_bullets.append(bullet_id)
    
    return destroyed_bullets
