# External libraries
from enum import IntEnum


class CollisionType(IntEnum):
    """Collision obstacle types."""

    NONE = 0
    WALL = 1
    AGENT = 2
    BULLET = 3


# Internal helpers


def _circles_overlap(
    x1: float, y1: float, r1: float, x2: float, y2: float, r2: float
) -> bool:
    """
    Check if two circles overlap via distance comparison.

    Args:
        x1: Circle 1 center X.
        y1: Circle 1 center Y.
        r1: Circle 1 radius.
        x2: Circle 2 center X.
        y2: Circle 2 center Y.
        r2: Circle 2 radius.

    Returns:
        True if circles overlap, False otherwise.
    """
    dx = x1 - x2
    dy = y1 - y2
    distance_squared = dx * dx + dy * dy
    min_distance = r1 + r2
    return distance_squared < min_distance * min_distance


def _circle_hits_wall(
    x: float, y: float, radius: float, walls_state
) -> bool:
    """
    Check if circle overlaps any wall cells.

    Checks all wall cells within circle bounds.

    Args:
        x: Circle center X.
        y: Circle center Y.
        radius: Circle radius.
        walls_state: StateWalls instance.

    Returns:
        True if circle overlaps any wall, False otherwise.
    """
    cx_min, cy_min = walls_state.to_cell(x - radius, y - radius)
    cx_max, cy_max = walls_state.to_cell(x + radius, y + radius)

    for cx in range(cx_min, cx_max + 1):
        for cy in range(cy_min, cy_max + 1):
            if walls_state.has_wall(cx, cy):
                return True

    return False


# Collision checks


def check_move_validity(
    x: float,
    y: float,
    radius: float,
    agents_dict: dict,
    walls_state,
    exclude_id: int | None = None,
) -> tuple[CollisionType, int | None]:
    """
    Check if position is valid (no collisions).

    Checks for wall and agent collisions.

    Args:
        x: Position X coordinate.
        y: Position Y coordinate.
        radius: Collision radius.
        agents_dict: Dictionary of all agents.
        walls_state: StateWalls instance.
        exclude_id: Agent ID to ignore in collision check.

    Returns:
        Tuple of (CollisionType, obstacle_id) where obstacle_id is
        agent_id for AGENT collisions, None for WALL or NONE.
    """
    # Check walls
    if _circle_hits_wall(x, y, radius, walls_state):
        return (CollisionType.WALL, None)

    # Check agents
    for agent_id, agent in agents_dict.items():
        if exclude_id == agent_id:
            continue
        if _circles_overlap(
            x,
            y,
            radius,
            agent.state.x,
            agent.state.y,
            agent.state.radius,
        ):
            return (CollisionType.AGENT, agent_id)

    return (CollisionType.NONE, None)


def find_bullet_agent_collisions(
    bullets_dict: dict, agents_dict: dict
) -> dict[int, list[int]]:
    """
    Find all bullet-agent collisions (opposite team only).

    Bullets don't damage their owner or same-team agents.

    Args:
        bullets_dict: Dictionary of all bullets.
        agents_dict: Dictionary of all agents.

    Returns:
        Dictionary mapping bullet_id to list of hit agent_ids.
    """
    hits: dict[int, list[int]] = {}

    for bullet_id, bullet in bullets_dict.items():
        hits[bullet_id] = []

        for agent_id, agent in agents_dict.items():
            # Skip owner and same team
            if agent_id == bullet.state.owner_id:
                continue
            if agent.state.team == bullet.state.team:
                continue

            if _circles_overlap(
                bullet.state.x,
                bullet.state.y,
                bullet.state.radius,
                agent.state.x,
                agent.state.y,
                agent.state.radius,
            ):
                hits[bullet_id].append(agent_id)

    return hits


def find_bullet_wall_collisions(
    bullets_dict: dict, walls_state
) -> list[int]:
    """
    Find all bullet-wall collisions.

    Args:
        bullets_dict: Dictionary of all bullets.
        walls_state: StateWalls instance.

    Returns:
        List of bullet_ids that hit walls.
    """
    destroyed_bullets: list[int] = []

    for bullet_id, bullet in bullets_dict.items():
        if _circle_hits_wall(
            bullet.state.x,
            bullet.state.y,
            bullet.state.radius,
            walls_state,
        ):
            destroyed_bullets.append(bullet_id)

    return destroyed_bullets
