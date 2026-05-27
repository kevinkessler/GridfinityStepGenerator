"""Gridfinity bin generator — monolithic approach.

Builds the entire bin as a single solid body by:
1. Creating the full outer shape
2. Cutting the main cavity
3. Cutting the lip shelf cavity
4. Cutting base pad voids

This avoids union-related issues between separately-cut components.
"""

import cadquery as cq

from gridfinity_step.constants import (
    GF_PITCH,
    GF_ZPITCH,
    GF_CLEARANCE,
    GF_CORNER_RADIUS,
    GF_BASE_TOTAL,
    GF_FLOOR_THICKNESS,
    GF_LIP_TOTAL,
    GF_BASE_PAD_DIAMETER,
)
from gridfinity_step.config import BinConfig
from gridfinity_step.geometry import rounded_box


def _rounded_box_at_z(w: float, d: float, h: float, r: float, z_bottom: float) -> cq.Workplane:
    """Create a rounded box with bottom at z=z_bottom."""
    box = rounded_box(w, d, h, r)
    return box.translate((0, 0, z_bottom + h / 2))


def make_bin(config: BinConfig) -> cq.Workplane:
    """Create a complete gridfinity bin as a single solid."""
    num_x = config.num_x
    num_y = config.num_y
    num_z = config.num_z
    wt = config.effective_wall_thickness

    outer_w = num_x * GF_PITCH - GF_CLEARANCE
    outer_d = num_y * GF_PITCH - GF_CLEARANCE
    body_h = num_z * GF_ZPITCH
    total_h = GF_BASE_TOTAL + body_h + GF_LIP_TOTAL

    cr = GF_CORNER_RADIUS

    # 1. Create the full outer shape
    result = _rounded_box_at_z(outer_w, outer_d, total_h, cr, 0)

    # 2. Cut main cavity (body interior)
    inner_w = outer_w - 2 * wt
    inner_d = outer_d - 2 * wt
    inner_cr = max(0.1, cr - wt)

    # Cavity: from floor level up to bottom of lip
    floor_z = GF_BASE_TOTAL - GF_FLOOR_THICKNESS + config.floor_thickness
    lip_z = GF_BASE_TOTAL + body_h
    cavity_h = lip_z - floor_z + 1  # up to lip bottom, slight overcut
    cavity = _rounded_box_at_z(inner_w, inner_d, cavity_h, inner_cr, floor_z)
    result = result.cut(cavity)

    # 3. Cut lip shelf cavity (if lip is not "none")
    if config.lip.style != "none":
        # The lip shelf overhangs inward, creating a narrower top opening
        q = 1.65 - wt + 0.95
        overhang = (2.3 + 2 * q) / 2

        lip_inner_w = inner_w - 2 * overhang
        lip_inner_d = inner_d - 2 * overhang
        lip_inner_cr = max(0.1, inner_cr - overhang)

        # Lip cavity: narrower opening through the lip zone
        # This cuts fresh material in the lip zone that wasn't removed by the main cavity
        lip_cavity = _rounded_box_at_z(
            lip_inner_w, lip_inner_d,
            GF_LIP_TOTAL + 1, lip_inner_cr,
            lip_z - 0.5,  # start slightly below lip bottom
        )
        result = result.cut(lip_cavity)

    # 4. Cut base pad voids (for pad-style base)
    if config.flat_base == "off":
        pad_w = GF_PITCH - GF_BASE_PAD_DIAMETER
        pad_d = GF_PITCH - GF_BASE_PAD_DIAMETER
        # Create negative space between pads
        offset_x = -outer_w / 2
        offset_y = -outer_d / 2

        for ix in range(int(num_x)):
            for iy in range(int(num_y)):
                # Space between pads = a rectangular cutout in each grid cell
                cx = offset_x + ix * GF_PITCH + GF_PITCH / 2
                cy = offset_y + iy * GF_PITCH + GF_PITCH / 2

                void_w = GF_PITCH - GF_BASE_PAD_DIAMETER / 2
                void_d = GF_PITCH - GF_BASE_PAD_DIAMETER / 2

                # Cut a small rectangular void in each cell to leave pad corners
                void = cq.Workplane("XY").box(void_w, void_d, GF_BASE_TOTAL + 2)
                void = void.translate((cx, cy, GF_BASE_TOTAL / 2))
                result = result.cut(void)

    elif config.flat_base == "rounded":
        # Fillet the bottom edges
        result = result.faces("<Z").edges().fillet(cr / 2)

    return result
