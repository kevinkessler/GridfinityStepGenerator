"""Gridfinity stacking lip — the top rim that allows bins to stack.

Returns a shape with bottom face at z=0, top at z=GF_LIP_TOTAL.
Caller translates to position the lip bottom at the top of the bin body.
"""

import cadquery as cq

from gridfinity_step.constants import (
    GF_PITCH,
    GF_CLEARANCE,
    GF_CORNER_RADIUS,
    GF_LIP_LOWER_TAPER_HEIGHT,
    GF_LIP_RISER_HEIGHT,
    GF_LIP_UPPER_TAPER_HEIGHT,
    GF_LIP_TOTAL,
)
from gridfinity_step.geometry import rounded_box, bin_outer_dimensions


def make_lip(
    num_x: float,
    num_y: float,
    wall_thickness: float,
    lip_style: str = "normal",
    headroom: float = 0.8,
    notches: bool = True,
) -> cq.Workplane:
    """Create the stacking lip with bottom at z=0.

    For "normal" lip: three stacked sections that approximate the taper profile.
    """
    outer_w, outer_d = bin_outer_dimensions(num_x, num_y)
    outer_w -= headroom
    outer_d -= headroom
    cr = GF_CORNER_RADIUS

    if lip_style == "none":
        return cq.Workplane("XY")

    if lip_style == "normal":
        h1 = GF_LIP_LOWER_TAPER_HEIGHT
        h2 = GF_LIP_RISER_HEIGHT
        h3 = GF_LIP_UPPER_TAPER_HEIGHT

        # At widest point, lip extends ~2.5mm beyond bin on each side
        taper_out = 2.5
        w_wide = outer_w + 2 * taper_out
        d_wide = outer_d + 2 * taper_out
        w_top = outer_w + 2 * 0.3
        d_top = outer_d + 2 * 0.3

        # Build bottom-up: each section sits on top of the previous
        sections = []

        # Lower taper: widest width, height h1
        s = rounded_box(w_wide, d_wide, h1, cr)
        s = s.translate((0, 0, h1 / 2))
        sections.append(s)

        # Riser: same width, height h2
        s = rounded_box(w_wide, d_wide, h2, cr)
        s = s.translate((0, 0, h1 + h2 / 2))
        sections.append(s)

        # Upper taper: narrower, height h3
        s = rounded_box(w_top, d_top, h3, cr)
        s = s.translate((0, 0, h1 + h2 + h3 / 2))
        sections.append(s)

        result = sections[0]
        for s in sections[1:]:
            result = result.union(s)

    else:
        # Reduced/minimum lip: simpler, single block
        w = outer_w + 2 * 1.0
        d = outer_d + 2 * 1.0
        result = rounded_box(w, d, GF_LIP_TOTAL, cr)
        result = result.translate((0, 0, GF_LIP_TOTAL / 2))

    # Ensure bottom is exactly at z=0 (shift if needed)
    # The sections are built with bottom at 0, so no shift needed
    return result
