"""Wire routing module.

Computes wire waypoints between components, avoiding component bounding boxes.
"""

from __future__ import annotations

from dataclasses import dataclass

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


def _segment_crosses_rect(
    p1: Point, p2: Point, bbox: BBox | None, margin: float = 2.0
) -> bool:
    """Check if a line segment passes through a bbox's interior."""
    if bbox is None:
        return False

    # Shrink bbox slightly to avoid false positives at pin locations
    inner_left = bbox.left + margin
    inner_right = bbox.right - margin
    inner_top = bbox.top + margin
    inner_bottom = bbox.bottom - margin

    # Check if segment is vertical
    if abs(p1.x - p2.x) < 1:
        x = p1.x
        y_min, y_max = min(p1.y, p2.y), max(p1.y, p2.y)
        # Check if vertical line passes through bbox horizontally
        if inner_left < x < inner_right:
            if y_min < inner_bottom and y_max > inner_top:
                return True
    # Check if segment is horizontal
    elif abs(p1.y - p2.y) < 1:
        y = p1.y
        x_min, x_max = min(p1.x, p2.x), max(p1.x, p2.x)
        # Check if horizontal line passes through bbox vertically
        if inner_top < y < inner_bottom:
            if x_min < inner_right and x_max > inner_left:
                return True

    return False


def _l_route_crosses_bbox(
    start: Point,
    bend: Point,
    end: Point,
    start_bbox: BBox | None,
    end_bbox: BBox | None,
) -> bool:
    """Check if an L-route would cross through either endpoint's bbox."""
    if _segment_crosses_rect(start, bend, start_bbox):
        return True
    if _segment_crosses_rect(bend, end, end_bbox):
        return True
    return False


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

        # Estimate pin position based on pin index
        # For now, use center - actual pin offsets would need symbol info
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
    start_bbox: BBox | None,
    end_bbox: BBox | None,
    prefer_horizontal: bool = True,
) -> tuple[Point, ...]:
    """Route a wire between two points, avoiding bboxes.

    Returns a tuple of waypoints from start to end.
    """
    dx = end_pos.x - start_pos.x
    dy = end_pos.y - start_pos.y

    # If nearly aligned, draw straight line
    if abs(dx) < 2 or abs(dy) < 2:
        return (start_pos, end_pos)

    # Two possible L-bend points
    bend_h = Point(end_pos.x, start_pos.y)  # horizontal first
    bend_v = Point(start_pos.x, end_pos.y)  # vertical first

    # Check which routes cross component bodies
    h_crosses = _l_route_crosses_bbox(start_pos, bend_h, end_pos, start_bbox, end_bbox)
    v_crosses = _l_route_crosses_bbox(start_pos, bend_v, end_pos, start_bbox, end_bbox)

    # Prefer based on pin side, but avoid crossings
    if prefer_horizontal and not h_crosses:
        return (start_pos, bend_h, end_pos)
    elif not prefer_horizontal and not v_crosses:
        return (start_pos, bend_v, end_pos)
    elif not h_crosses:
        return (start_pos, bend_h, end_pos)
    elif not v_crosses:
        return (start_pos, bend_v, end_pos)
    else:
        # Both L-routes cross - use U-routing around the obstacle
        if start_bbox is None:
            # No bbox to avoid, just use preferred L-route
            if prefer_horizontal:
                return (start_pos, bend_h, end_pos)
            else:
                return (start_pos, bend_v, end_pos)
        elif prefer_horizontal:
            # Go horizontal away from end, then vertical, then to end
            escape_x = start_bbox.left - 15 if dx > 0 else start_bbox.right + 15
            return (
                start_pos,
                Point(escape_x, start_pos.y),
                Point(escape_x, end_pos.y),
                end_pos,
            )
        else:
            # Go vertical away from end, then horizontal, then to end
            escape_y = start_bbox.top - 15 if dy > 0 else start_bbox.bottom + 15
            return (
                start_pos,
                Point(start_pos.x, escape_y),
                Point(end_pos.x, escape_y),
                end_pos,
            )


def route_netlist(placed: PlacedNetlist) -> RoutedNetlist:
    """Compute wire routes for a placed netlist.

    Takes a PlacedNetlist and returns a RoutedNetlist with pre-computed
    wire waypoints that avoid component bounding boxes.
    """
    # Compute bboxes for all instances
    instance_bboxes = [_compute_instance_bbox(inst) for inst in placed.instances]

    wires: list[RoutedWire] = []

    for edge in placed.edges:
        start_pos, start_pin = _get_pin_position(placed, edge.start, edge.net)
        end_pos, end_pin = _get_pin_position(placed, edge.end, edge.net)

        # Get bboxes for start/end if they are instances
        start_bbox = (
            instance_bboxes[edge.start] if isinstance(edge.start, int) else None
        )
        end_bbox = instance_bboxes[edge.end] if isinstance(edge.end, int) else None

        # Route the edge
        waypoints = _route_edge(start_pos, end_pos, start_bbox, end_bbox)

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
