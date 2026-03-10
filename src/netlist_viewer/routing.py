"""Wire routing module.

Computes wire waypoints between components using A* grid-based pathfinding.
"""

from __future__ import annotations
import logging
import time

import heapq
from dataclasses import dataclass, field
from typing import Iterator

from netlist_viewer.core_types import NodeReference
from netlist_viewer.layout import PlacedNetlist, PlacedInstance, PlacedNet, Point, Edge
from netlist_viewer.spice_parser import Netlist


@dataclass(frozen=True)
class RoutedWire:
    """A wire with pre-computed waypoints."""

    start: NodeReference  # int (instance idx) or str (net node key)
    end: NodeReference
    start_pin: str | None  # Pin name on start, None for net nodes
    end_pin: str | None  # Pin name on end, None for net nodes
    net: str
    points: tuple[Point, ...]  # Waypoints from start to end


@dataclass(frozen=True)
class BBox:
    """Axis-aligned bounding box."""

    left: float
    top: float
    right: float
    bottom: float

    def contains_point(self, x: float, y: float, margin: float = 2.0) -> bool:
        """Check if a point is inside the bbox (with margin)."""
        inner_left = self.left + margin
        inner_right = self.right - margin
        inner_top = self.top + margin
        inner_bottom = self.bottom - margin
        return inner_left < x < inner_right and inner_top < y < inner_bottom


# Default symbol dimensions (used for bbox estimation)
DEFAULT_SYMBOL_WIDTH = 40.0
DEFAULT_SYMBOL_HEIGHT = 60.0
LAYOUT_SCALE = 300.0

# Routing grid configuration
DEFAULT_GRID_RESOLUTION = 10.0  # Grid cell size in scene units
WIRE_COST_MULTIPLIER = 5.0  # Cost multiplier for cells with other-net wires
SAME_NET_BONUS = 0.75  # Cost reduction for following same-net wires (negative = bonus)
BEND_COST = 2.0  # Additional cost for changing direction


@dataclass(frozen=True)
class GridCell:
    """A cell in the routing grid."""

    gx: int  # Grid x coordinate
    gy: int  # Grid y coordinate


@dataclass(order=True)
class PriorityEntry:
    """Entry for the A* priority queue."""

    priority: float
    cell: GridCell = field(compare=False)
    came_from: GridCell | None = field(compare=False)
    direction: tuple[int, int] | None = field(compare=False)  # Movement direction


class RoutingGrid:
    """Grid for A* pathfinding."""

    def __init__(
        self,
        min_x: float,
        min_y: float,
        max_x: float,
        max_y: float,
        resolution: float = DEFAULT_GRID_RESOLUTION,
        current_net: str | None = None,
    ):
        self.resolution = resolution
        self.min_x = min_x
        self.min_y = min_y
        self.max_x = max_x
        self.max_y = max_y
        self.current_net = current_net  # Net being routed (for same-net bonus)

        # Grid dimensions
        self.width = int((max_x - min_x) / resolution) + 1
        self.height = int((max_y - min_y) / resolution) + 1

        # Cost grid: blocked cells and wire costs by net
        self._blocked: set[tuple[int, int]] = set()
        # Maps cell -> set of nets that have wires through it
        self._wire_nets: dict[tuple[int, int], set[str]] = {}

    def world_to_grid(self, x: float, y: float) -> GridCell:
        """Convert world coordinates to grid cell."""
        gx = int((x - self.min_x) / self.resolution)
        gy = int((y - self.min_y) / self.resolution)
        # Clamp to grid bounds
        gx = max(0, min(gx, self.width - 1))
        gy = max(0, min(gy, self.height - 1))
        return GridCell(gx, gy)

    def grid_to_world(self, cell: GridCell) -> Point:
        """Convert grid cell to world coordinates (cell center)."""
        x = self.min_x + (cell.gx + 0.5) * self.resolution
        y = self.min_y + (cell.gy + 0.5) * self.resolution
        return Point(x, y)

    def mark_bbox_blocked(self, bbox: BBox, margin: float = 2.0) -> None:
        """Mark all grid cells overlapping a bbox as blocked."""
        # Convert bbox to grid coordinates
        left_cell = int((bbox.left - margin - self.min_x) / self.resolution)
        right_cell = int((bbox.right + margin - self.min_x) / self.resolution)
        top_cell = int((bbox.top - margin - self.min_y) / self.resolution)
        bottom_cell = int((bbox.bottom + margin - self.min_y) / self.resolution)

        # Mark cells as blocked
        for gx in range(max(0, left_cell), min(self.width, right_cell + 1)):
            for gy in range(max(0, top_cell), min(self.height, bottom_cell + 1)):
                self._blocked.add((gx, gy))

    def mark_wire_segment(self, p1: Point, p2: Point, net: str | None = None) -> None:
        """Mark grid cells along a wire segment as occupied by a net."""
        cell1 = self.world_to_grid(p1.x, p1.y)
        cell2 = self.world_to_grid(p2.x, p2.y)

        def mark_cell(gx: int, gy: int) -> None:
            key = (gx, gy)
            if key not in self._blocked and net is not None:
                if key not in self._wire_nets:
                    self._wire_nets[key] = set()
                self._wire_nets[key].add(net)

        # Bresenham-like line rasterization
        dx = abs(cell2.gx - cell1.gx)
        dy = abs(cell2.gy - cell1.gy)
        sx = 1 if cell1.gx < cell2.gx else -1
        sy = 1 if cell1.gy < cell2.gy else -1

        gx, gy = cell1.gx, cell1.gy
        if dx > dy:
            err = dx / 2
            while gx != cell2.gx:
                mark_cell(gx, gy)
                err -= dy
                if err < 0:
                    gy += sy
                    err += dx
                gx += sx
        else:
            err = dy / 2
            while gy != cell2.gy:
                mark_cell(gx, gy)
                err -= dx
                if err < 0:
                    gx += sx
                    err += dy
                gy += sy
        # Mark final cell
        mark_cell(cell2.gx, cell2.gy)

    def is_blocked(self, cell: GridCell) -> bool:
        """Check if a cell is blocked."""
        return (cell.gx, cell.gy) in self._blocked

    def get_cost(self, cell: GridCell) -> float:
        """Get the cost to traverse a cell.

        Base cost is 1.0. Cells with wires from other nets have higher cost.
        Cells with wires from the same net have lower cost (bonus for bundling).
        """
        if self.is_blocked(cell):
            return float("inf")

        key = (cell.gx, cell.gy)
        nets_in_cell = self._wire_nets.get(key)

        if not nets_in_cell:
            return 1.0  # Empty cell

        # Check if current net passes through this cell
        has_same_net = self.current_net is not None and self.current_net in nets_in_cell
        has_other_nets = len(nets_in_cell) > 1 or (
            len(nets_in_cell) == 1 and not has_same_net
        )

        cost = 1.0
        if has_same_net:
            cost -= SAME_NET_BONUS  # Bonus for following same net
        if has_other_nets:
            cost += WIRE_COST_MULTIPLIER  # Penalty for crossing other nets

        return max(0.1, cost)  # Ensure cost stays positive

    def neighbors(self, cell: GridCell) -> Iterator[tuple[GridCell, tuple[int, int]]]:
        """Yield valid neighboring cells and their movement directions."""
        # 4-connected grid (orthogonal moves only for Manhattan routing)
        for dx, dy in [(0, -1), (0, 1), (-1, 0), (1, 0)]:
            nx, ny = cell.gx + dx, cell.gy + dy
            if 0 <= nx < self.width and 0 <= ny < self.height:
                neighbor = GridCell(nx, ny)
                if not self.is_blocked(neighbor):
                    yield neighbor, (dx, dy)

    def clear_cell(self, cell: GridCell) -> None:
        """Ensure a cell is not blocked (for start/end points)."""
        key = (cell.gx, cell.gy)
        self._blocked.discard(key)


def _heuristic(a: GridCell, b: GridCell) -> int:
    """Manhattan distance heuristic for A*."""
    return abs(a.gx - b.gx) + abs(a.gy - b.gy)


def _astar_search(
    grid: RoutingGrid,
    start: GridCell,
    goal: GridCell,
) -> list[GridCell] | None:
    """A* pathfinding on the routing grid.

    Returns list of cells from start to goal, or None if no path exists.
    """
    # Ensure start and goal are passable
    grid.clear_cell(start)
    grid.clear_cell(goal)

    # Priority queue: (priority, cell, came_from, direction)
    open_set: list[PriorityEntry] = []
    heapq.heappush(open_set, PriorityEntry(0.0, start, None, None))

    # Best known cost to reach each cell
    g_score: dict[GridCell, float] = {start: 0.0}

    # Track path
    came_from: dict[GridCell, GridCell] = {}
    direction_to: dict[GridCell, tuple[int, int] | None] = {start: None}

    while open_set:
        entry = heapq.heappop(open_set)
        current = entry.cell
        current_dir = entry.direction

        if current == goal:
            # Reconstruct path
            path = [current]
            while current in came_from:
                current = came_from[current]
                path.append(current)
            path.reverse()
            return path

        for neighbor, move_dir in grid.neighbors(current):
            # Base cost to move to neighbor
            move_cost = grid.get_cost(neighbor)

            # Add bend penalty if direction changes
            if current_dir is not None and move_dir != current_dir:
                move_cost += BEND_COST

            tentative_g = g_score[current] + move_cost

            if neighbor not in g_score or tentative_g < g_score[neighbor]:
                g_score[neighbor] = tentative_g
                came_from[neighbor] = current
                direction_to[neighbor] = move_dir
                f_score = tentative_g + float(_heuristic(neighbor, goal))
                heapq.heappush(
                    open_set, PriorityEntry(f_score, neighbor, current, move_dir)
                )

    return None  # No path found


def _simplify_path(points: list[Point]) -> tuple[Point, ...]:
    """Remove redundant waypoints from a path (keep only corners)."""
    if len(points) <= 2:
        return tuple(points)

    result = [points[0]]
    for i in range(1, len(points) - 1):
        prev, curr, next_pt = points[i - 1], points[i], points[i + 1]
        # Keep point if direction changes
        dx1 = curr.x - prev.x
        dy1 = curr.y - prev.y
        dx2 = next_pt.x - curr.x
        dy2 = next_pt.y - curr.y
        # Normalize directions to signs
        dir1 = (
            1 if dx1 > 0 else (-1 if dx1 < 0 else 0),
            1 if dy1 > 0 else (-1 if dy1 < 0 else 0),
        )
        dir2 = (
            1 if dx2 > 0 else (-1 if dx2 < 0 else 0),
            1 if dy2 > 0 else (-1 if dy2 < 0 else 0),
        )
        if dir1 != dir2:
            result.append(curr)
    result.append(points[-1])
    return tuple(result)


def _compute_instance_bbox(placed_inst: PlacedInstance) -> BBox:
    """Compute bounding box for a placed instance."""
    x = placed_inst.location.x * LAYOUT_SCALE
    y = placed_inst.location.y * LAYOUT_SCALE
    half_w = DEFAULT_SYMBOL_WIDTH / 2
    half_h = DEFAULT_SYMBOL_HEIGHT / 2
    return BBox(
        left=x - half_w,
        top=y - half_h,
        right=x + half_w,
        bottom=y + half_h,
    )


def _get_pin_position(
    placed: PlacedNetlist,
    node: NodeReference,
    net: str,
) -> tuple[Point, str | None]:
    """Get position of a pin and the pin name.

    Returns (position, pin_name) where pin_name is None for net nodes.
    """
    if isinstance(node, int):
        placed_inst = placed.instances[node]
        x = placed_inst.location.x * LAYOUT_SCALE
        y = placed_inst.location.y * LAYOUT_SCALE

        # Find which pin connects to this net
        try:
            pin_index = placed_inst.instance.nets.index(net)
            pin_name = str(pin_index + 1)
        except ValueError:
            pin_name = "1"  # Fallback

        return Point(x, y), pin_name
    else:
        # Net node
        placed_net = placed.net_nodes[node]
        x = placed_net.location.x * LAYOUT_SCALE
        y = placed_net.location.y * LAYOUT_SCALE
        return Point(x, y), None


def _route_edge(
    start_pos: Point,
    end_pos: Point,
    all_bboxes: list[BBox],
    prefer_horizontal: bool = True,
    existing_wires: list[tuple[tuple[Point, ...], str | None]] | None = None,
    grid_resolution: float = DEFAULT_GRID_RESOLUTION,
    current_net: str | None = None,
) -> tuple[Point, ...]:
    """Route a wire between two points using A* pathfinding.

    Args:
        start_pos: Starting point
        end_pos: Ending point
        all_bboxes: Component bounding boxes to avoid
        prefer_horizontal: Hint for preferred initial direction (unused in A*)
        existing_wires: List of (waypoints, net_name) for previously routed wires
        grid_resolution: Size of each grid cell
        current_net: Net name of the wire being routed (for same-net bonus)

    Returns:
        Tuple of waypoints from start to end.
    """
    # Quick check for nearly aligned points
    dx = abs(end_pos.x - start_pos.x)
    dy = abs(end_pos.y - start_pos.y)
    if dx < 2 or dy < 2:
        return (start_pos, end_pos)

    # Compute grid bounds with padding
    padding = grid_resolution * 5
    if all_bboxes:
        min_x = min(min(b.left for b in all_bboxes), start_pos.x, end_pos.x) - padding
        max_x = max(max(b.right for b in all_bboxes), start_pos.x, end_pos.x) + padding
        min_y = min(min(b.top for b in all_bboxes), start_pos.y, end_pos.y) - padding
        max_y = max(max(b.bottom for b in all_bboxes), start_pos.y, end_pos.y) + padding
    else:
        min_x = min(start_pos.x, end_pos.x) - padding
        max_x = max(start_pos.x, end_pos.x) + padding
        min_y = min(start_pos.y, end_pos.y) - padding
        max_y = max(start_pos.y, end_pos.y) + padding

    # Create routing grid with current net for same-net bonus
    grid = RoutingGrid(min_x, min_y, max_x, max_y, grid_resolution, current_net)

    # Mark bboxes as blocked
    for bbox in all_bboxes:
        grid.mark_bbox_blocked(bbox)

    # Mark existing wires (same-net = bonus, other-net = penalty)
    if existing_wires:
        for wire_points, wire_net in existing_wires:
            for i in range(len(wire_points) - 1):
                grid.mark_wire_segment(wire_points[i], wire_points[i + 1], wire_net)

    # Convert start/end to grid cells
    start_cell = grid.world_to_grid(start_pos.x, start_pos.y)
    goal_cell = grid.world_to_grid(end_pos.x, end_pos.y)

    # Run A* search
    path = _astar_search(grid, start_cell, goal_cell)

    if path is None:
        # Fallback to simple L-route if A* fails
        if prefer_horizontal:
            bend = Point(end_pos.x, start_pos.y)
        else:
            bend = Point(start_pos.x, end_pos.y)
        return (start_pos, bend, end_pos)

    # Convert path to world coordinates
    world_path = [start_pos]  # Start with exact start position
    for cell in path[1:-1]:  # Skip first and last (we use exact positions)
        world_path.append(grid.grid_to_world(cell))
    world_path.append(end_pos)  # End with exact end position

    # Simplify path to remove redundant waypoints
    return _simplify_path(world_path)


def route_netlist(
    placed: PlacedNetlist,
    grid_resolution: float = DEFAULT_GRID_RESOLUTION,
) -> RoutedNetlist:
    """Compute wire routes for a placed netlist.

    Takes a PlacedNetlist and returns a RoutedNetlist with pre-computed
    wire waypoints that avoid component bounding boxes.

    Args:
        placed: The placed netlist with component positions
        grid_resolution: Size of each grid cell for A* routing
    """
    start_time = time.time()
    # Compute bboxes for all instances
    all_bboxes = [_compute_instance_bbox(inst) for inst in placed.instances]

    wires: list[RoutedWire] = []
    # Track existing wires with their net names for same-net bonus
    existing_wire_paths: list[tuple[tuple[Point, ...], str | None]] = []

    for edge in placed.edges:
        start_pos, start_pin = _get_pin_position(placed, edge.start, edge.net)
        end_pos, end_pin = _get_pin_position(placed, edge.end, edge.net)

        # Route the edge, with same-net bonus and other-net penalty
        waypoints = _route_edge(
            start_pos,
            end_pos,
            all_bboxes,
            existing_wires=existing_wire_paths,
            grid_resolution=grid_resolution,
            current_net=edge.net,
        )

        wires.append(
            RoutedWire(
                start=edge.start,
                end=edge.end,
                start_pin=start_pin,
                end_pin=end_pin,
                net=edge.net,
                points=waypoints,
            )
        )

        # Add this wire's path with net name for subsequent routes
        existing_wire_paths.append((waypoints, edge.net))

    end_time = time.time()
    logging.info("Calculated routing in %f s", end_time - start_time)
    return RoutedNetlist(
        source=placed.source,
        instances=placed.instances,
        net_nodes=placed.net_nodes,
        edges=placed.edges,
        wires=wires,
    )


@dataclass(frozen=True)
class RoutedNetlist:
    """PlacedNetlist with pre-computed wire routes."""

    source: Netlist
    instances: list[PlacedInstance]
    net_nodes: dict[str, PlacedNet]
    edges: list[Edge]  # Keep original edges for reference
    wires: list[RoutedWire]  # Routed wires with waypoints

    def get_node(self, key: NodeReference) -> PlacedInstance | PlacedNet:
        """Get a placed node by its key."""
        if isinstance(key, int):
            return self.instances[key]
        elif isinstance(key, str):
            return self.net_nodes[key]
        else:
            raise IndexError("Bad index")
