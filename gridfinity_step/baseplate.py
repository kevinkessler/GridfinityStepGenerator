"""Gridfinity baseplate generator.

A baseplate is the grid plate that bins snap into.
It has a grid of recessed sockets matching the bin base pad profile.
"""

import math
import cadquery as cq

from gridfinity_step.gridfinity import (
    GRID_UNIT,
    BLOCK_SPACING,
    FILLET_RADIUS,
    BLOCK_MATING_DEPTH,
    BLOCK_MATING_INSET,
    BLOCK_MATING_CHAMFER,
    BASEPLATE_MATING_INSET,
    MAGNET_INSET,
    MAGNET_DIAMETER,
    MAGNET_DEPTH,
    SCREW_DIAMETER,
    SCREW_DEPTH,
    _inset_profile,
)


def make_baseplate(
    width: float,
    height: float,
    magnets: bool = False,
) -> cq.Workplane:
    """Create a Gridfinity baseplate.

    Args:
        width, height: Grid units (can be fractional)
        magnets: Add magnet counterbore holes
    """
    outer_w = width * GRID_UNIT - BLOCK_SPACING
    outer_h = height * GRID_UNIT - BLOCK_SPACING

    # 1. Solid base — rounded rectangle
    base = (
        cq.Workplane("XY")
        .placeSketch(_inset_profile(width, height, BLOCK_SPACING / 2))
        .extrude(BLOCK_MATING_DEPTH)
    )

    # 2. Cut grid sockets — one per cell, matching the bin pad profile
    cells_x = math.ceil(width)
    cells_y = math.ceil(height)

    for ix in range(cells_x):
        for iy in range(cells_y):
            cx = -outer_w / 2 + (ix + 0.5) * GRID_UNIT
            cy = -outer_h / 2 + (iy + 0.5) * GRID_UNIT

            # Socket uses baseplate inset (slightly wider than block mating inset)
            socket = (
                cq.Workplane("XY")
                .placeSketch(_inset_profile(1, 1, BASEPLATE_MATING_INSET))
                .extrude(BLOCK_MATING_DEPTH * -0.7)  # go partway down
                .translate((cx, cy, BLOCK_MATING_DEPTH))
            )
            base = base.cut(socket)

    # 3. Magnet counterbore holes at cell corners
    if magnets:
        for ix in range(cells_x + 1):
            for iy in range(cells_y + 1):
                mx = -outer_w / 2 + ix * GRID_UNIT
                my = -outer_h / 2 + iy * GRID_UNIT

                # Four magnet positions per cell corner
                for sx, sy in [(-1, -1), (1, -1), (-1, 1), (1, 1)]:
                    hole_x = mx + sx * MAGNET_INSET
                    hole_y = my + sy * MAGNET_INSET

                    # Skip holes outside the baseplate
                    if abs(hole_x) > outer_w / 2 - 2 or abs(hole_y) > outer_h / 2 - 2:
                        continue

                    hole = (
                        cq.Workplane("XY")
                        .cylinder(BLOCK_MATING_DEPTH + 1, MAGNET_DIAMETER / 2)
                        .translate((hole_x, hole_y, 0))
                    )
                    base = base.cut(hole)

    return base
