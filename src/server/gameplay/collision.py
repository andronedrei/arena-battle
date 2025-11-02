# === INTERNAL HELPERS ===

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

def agent_can_move_to(x: float, y: float, radius: float,
                     agents_dict, bullets_dict, walls_state, 
                     exclude_id: int = None) -> bool:
    """Check if agent can move to position without collision."""
    if _circle_hits_wall(x, y, radius, walls_state):
        return False
    
    for agent_id, agent in agents_dict.items():
        if exclude_id and agent_id == exclude_id:
            continue
        if _circles_overlap(x, y, radius, agent.state.x, agent.state.y, agent.state.radius):
            return False
    
    for bullet in bullets_dict.values():
        if _circles_overlap(x, y, radius, bullet.state.x, bullet.state.y, bullet.state.radius):
            return False
    
    return True


def find_agent_agent_collisions(agents_dict) -> list[tuple[int, int]]:
    """Find all agent-agent collisions."""
    collisions = []
    agent_list = list(agents_dict.items())
    
    for i in range(len(agent_list)):
        for j in range(i + 1, len(agent_list)):
            id1, agent1 = agent_list[i]
            id2, agent2 = agent_list[j]
            
            if _circles_overlap(agent1.state.x, agent1.state.y, agent1.state.radius,
                               agent2.state.x, agent2.state.y, agent2.state.radius):
                collisions.append((id1, id2))
    
    return collisions


def find_bullet_agent_collisions(bullets_dict, agents_dict) -> dict:
    """Find all bullet-agent collisions."""
    hits = {}
    
    for bullet_id, bullet in bullets_dict.items():
        hits[bullet_id] = []
        
        for agent_id, agent in agents_dict.items():
            # FIX: Use bullet.state.owner_id instead of bullet.owner_id
            if agent_id == bullet.state.owner_id:
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
