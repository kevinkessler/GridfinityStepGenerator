"""Gridfinity stacking lip — per the official spec.

The lip is flush with the bin body externally (same 41.5mm per unit width).
Internally, a tapered profile creates the shelf for stacking.

Profile (top to bottom):
  0.25mm flat
  1.9mm at 45° inward
  1.8mm vertical
  0.7mm at 45° outward (back to wall)
  Total: ~4.4mm

In CADQuery, this is created by subtracting a tapered cavity from the outer lip block.
"""

import cadquery as cq

from gridfinity_step.constants import (
    GF_CORNER_RADIUS,
)
from gridfinity_step.geometry import rounded_box, bin_outer_dimensions

LIP_HEIGHT = 4.4


def make_lip(
    num_x: float,
    num_y: float,
    wall_thickness: float,
    lip_style: str = "normal",
    headroom: float = 0.8,
    notches: bool = True,
) -> cq.Workplane:
    """Create the stacking lip, bottom at z=0, top at z=LIP_HEIGHT."""
    outer_w, outer_d = bin_outer_dimensions(num_x, num_y)
    cr = GF_CORNER_RADIUS

    if lip_style == "none":
        return cq.Workplane("XY")

    # 1. Outer lip block — flush with bin body
    outer_lip = rounded_box(outer_w, outer_d, LIP_HEIGHT, cr)
    outer_lip = outer_lip.translate((0, 0, LIP_HEIGHT / 2))

    if lip_style == "normal":
        # 2. Create the tapered internal cavity
        # The shelf protrudes inward by approximately 1.65mm from the wall
        # (this is the 'q' value from OpenSCAD: 1.65 - wall_thickness + 0.95)

        inner_cr = max(0.1, cr - wall_thickness)

        # Width at wall inner boundary
        inner_w = outer_w - 2 * wall_thickness
        inner_d = outer_d - 2 * wall_thickness

        # The lip overhangs inward: the top opening is narrower
        # Overhang amount (q in OpenSCAD) = 1.65 - wall_thickness + 0.95
        q = 1.65 - wall_thickness + 0.95
        overhang = (2.3 + 2 * q) / 2  # effective inward protrusion

        # Top opening dimensions (narrower due to overhang)
        top_inner_w = inner_w - 2 * overhang
        top_inner_d = inner_d - 2 * overhang
        top_inner_cr = max(0.1, inner_cr - overhang)

        # Build cavity as two stacked sections that approximate the taper
        # Lower section: wall inner dimensions (most of the height)
        lower_h = LIP_HEIGHT * 0.55  # ~2.4mm
        lower = rounded_box(inner_w, inner_d, lower_h, inner_cr)
        lower = lower.translate((0, 0, lower_h / 2))

        # Upper section: narrower (the shelf), taller at top
        upper_h = LIP_HEIGHT - lower_h  # ~2.0mm
        upper = rounded_box(top_inner_w, top_inner_d, upper_h + 0.5, top_inner_cr)
        upper = upper.translate((0, 0, lower_h + upper_h / 2))

        cavity = lower.union(upper)
        result = outer_lip.cut(cavity)

    elif lip_style in ("reduced", "reduced_double"):
        # Reduced lip: less overhang
        inner_cr = max(0.1, cr - wall_thickness)
        inner_w = outer_w - 2 * wall_thickness
        inner_d = outer_d - 2 * wall_thickness
        cavity = rounded_box(inner_w, inner_d, LIP_HEIGHT + 0.1, inner_cr)
        cavity = cavity.translate((0, 0, LIP_HEIGHT / 2))
        result = outer_lip.cut(cavity)

    elif lip_style == "minimum":
        # Minimum lip: nearly no overhang
        inner_cr = max(0.1, cr - wall_thickness - 1.0)
        inner_w = outer_w - 2 * (wall_thickness + 1.0)
        inner_d = outer_d - 2 * (wall_thickness + 1.0)
        cavity = rounded_box(inner_w, inner_d, LIP_HEIGHT + 0.1, inner_cr)
        cavity = cavity.translate((0, 0, LIP_HEIGHT / 2))
        result = outer_lip.cut(cavity)
    else:
        result = outer_lip

    return result
