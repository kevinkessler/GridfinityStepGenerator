"""Core geometry primitives for gridfinity bins.

CADQuery's box(x, y, z) is CENTERED on the workplane.
Bottom face is at z=-z/2, top face at z=+z/2.
All functions return shapes in "local" coordinates; callers translate to final position.
"""

import cadquery as cq

from gridfinity_step.constants import (
    GF_PITCH,
    GF_ZPITCH,
    GF_CLEARANCE,
    GF_CORNER_RADIUS,
    GF_BASE_TOTAL,
    GF_FLOOR_THICKNESS,
)


def rounded_box(
    width: float,
    depth: float,
    height: float,
    corner_radius: float,
) -> cq.Workplane:
    """Create a rounded-rectangle box centered on the workplane.

    Box extends from -height/2 to +height/2 in Z.
    """
    return (
        cq.Workplane("XY")
        .box(width, depth, height)
        .edges("|Z")
        .fillet(corner_radius)
    )


def rounded_box_chamfered_bottom(
    width: float,
    depth: float,
    height: float,
    corner_radius: float,
    bottom_radius: float,
) -> cq.Workplane:
    """Rounded box with a different fillet radius on bottom edges."""
    box = rounded_box(width, depth, height, corner_radius)
    if bottom_radius > 0:
        box = box.faces("<Z").edges().fillet(bottom_radius)
    return box


def bin_outer_dimensions(num_x: float, num_y: float) -> tuple[float, float]:
    """Return (width, depth) of the bin's outer bounding box."""
    return (
        num_x * GF_PITCH - GF_CLEARANCE,
        num_y * GF_PITCH - GF_CLEARANCE,
    )


def bin_outer_shell(
    num_x: float,
    num_y: float,
    num_z: int,
    corner_radius: float = GF_CORNER_RADIUS,
) -> cq.Workplane:
    """Create the outer shell of a bin body.

    Centered on workplane. Height = num_z * GF_ZPITCH.
    Caller must translate to final position.
    """
    outer_w, outer_d = bin_outer_dimensions(num_x, num_y)
    height = num_z * GF_ZPITCH
    return rounded_box(outer_w, outer_d, height, corner_radius)


def bin_cavity(
    num_x: float,
    num_y: float,
    num_z: int,
    wall_thickness: float,
    floor_thickness: float = GF_FLOOR_THICKNESS,
    corner_radius: float = GF_CORNER_RADIUS,
) -> cq.Workplane:
    """The internal void to subtract from a bin.

    Centered on workplane. Caller translates to align with the bin body.
    """
    outer_w, outer_d = bin_outer_dimensions(num_x, num_y)

    inner_w = outer_w - 2 * wall_thickness
    inner_d = outer_d - 2 * wall_thickness
    inner_cr = max(0.1, corner_radius - wall_thickness)

    # Make cavity taller than needed; it gets positioned and cut into the body
    cavity_height = num_z * GF_ZPITCH + 10

    return rounded_box(inner_w, inner_d, cavity_height, inner_cr)


def make_basic_bin(
    num_x: float,
    num_y: float,
    num_z: int,
    wall_thickness: float,
    floor_thickness: float = GF_FLOOR_THICKNESS,
) -> cq.Workplane:
    """Create a basic hollow bin body.

    Positioned so the bottom face of the body is at z=0.
    (The base pads attach below this.)

    Body height = num_z * GF_ZPITCH.
    """
    body_height = num_z * GF_ZPITCH

    # Outer shell: centered, bottom at z=0 means translate by body_height/2
    outer = bin_outer_shell(num_x, num_y, num_z)
    outer = outer.translate((0, 0, body_height / 2))

    # Cavity: needs to start at effective floor height above the body bottom
    # Effective floor: how high above body bottom the usable floor sits
    effective_floor = floor_thickness  # floor is this many mm above body bottom

    cavity = bin_cavity(num_x, num_y, num_z, wall_thickness, floor_thickness)
    # Position cavity so its bottom face is at effective_floor
    ch = num_z * GF_ZPITCH + 10  # cavity_height
    cavity = cavity.translate((0, 0, effective_floor + ch / 2))

    result = outer.cut(cavity)
    return result
