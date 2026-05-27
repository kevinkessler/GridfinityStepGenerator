"""Gridfinity-compatible base — tapered pads for stacking into baseplates.

Returns a shape with bottom at z=0.
"""

import cadquery as cq

from gridfinity_step.constants import (
    GF_PITCH,
    GF_CLEARANCE,
    GF_CORNER_RADIUS,
    GF_BASE_TOTAL,
    GF_BASE_PAD_DIAMETER,
)
from gridfinity_step.geometry import rounded_box, rounded_box_chamfered_bottom, bin_outer_dimensions


def _single_pad(size: float, height: float) -> cq.Workplane:
    """A single base pad (rounded box, bottom at z=0)."""
    pad = rounded_box(size, size, height, GF_CORNER_RADIUS / 2)
    return pad.translate((0, 0, height / 2))


def _pad_grid(num_x: float, num_y: float) -> cq.Workplane:
    """Generate a grid of base pads, clipped to the bin outline."""
    outer_w, outer_d = bin_outer_dimensions(num_x, num_y)
    pad_size = GF_BASE_PAD_DIAMETER
    pad_height = GF_BASE_TOTAL

    # Pads at grid cell corners, origin at bin center
    offset_x = -outer_w / 2
    offset_y = -outer_d / 2

    result = cq.Workplane("XY")
    for ix in range(int(num_x) + 1):
        for iy in range(int(num_y) + 1):
            px = offset_x + ix * GF_PITCH
            py = offset_y + iy * GF_PITCH
            pad = _single_pad(pad_size, pad_height)
            pad = pad.translate((px, py, 0))
            if result.val() is None:
                result = pad
            else:
                result = result.union(pad)

    # Clip pads to the outer bin shape
    outer_shape = rounded_box(outer_w, outer_d, GF_BASE_TOTAL + 2, GF_CORNER_RADIUS)
    outer_shape = outer_shape.translate((0, 0, (GF_BASE_TOTAL + 2) / 2))
    result = result.intersect(outer_shape)
    return result


def make_base(
    num_x: float,
    num_y: float,
    flat_base: str = "off",
    align_x: str = "near",
    align_y: str = "near",
    sub_pitch: int = 1,
) -> cq.Workplane:
    """Create the base with bottom at z=0, top at z=GF_BASE_TOTAL."""
    outer_w, outer_d = bin_outer_dimensions(num_x, num_y)
    cr = GF_CORNER_RADIUS

    if flat_base == "rounded":
        base = rounded_box_chamfered_bottom(
            outer_w, outer_d, GF_BASE_TOTAL, cr, bottom_radius=cr / 2,
        )
        return base.translate((0, 0, GF_BASE_TOTAL / 2))
    elif flat_base == "gridfinity":
        base = rounded_box(outer_w, outer_d, GF_BASE_TOTAL, cr)
        return base.translate((0, 0, GF_BASE_TOTAL / 2))
    else:
        return _pad_grid(num_x, num_y)
