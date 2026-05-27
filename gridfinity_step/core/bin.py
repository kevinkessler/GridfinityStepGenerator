"""Assemble a complete hollow Gridfinity bin."""

import cadquery as cq

from gridfinity_step.gridfinity import (
    GRID_UNIT,
    BLOCK_SPACING,
    FILLET_RADIUS,
    BLOCK_MATING_DEPTH,
    BLOCK_MATING_INSET,
    STACKING_MATING_DEPTH,
    make_block,
    cut_stacking_lip,
    add_bottom_lip,
    _block_height,
)


def make_bin(
    width: int,
    height: int,
    depth: int,
    wall_thickness: float = 1.2,
    floor_thickness: float = 1.2,
    magnets: bool = False,
) -> cq.Workplane:
    """Create a hollow Gridfinity storage bin.

    The cavity is sized to fit within the stacking lip recess,
    preserving the lip shelf for proper stacking.
    """
    body_h = _block_height(depth)

    # 1. Solid block
    block = make_block(width, height, depth)

    # 2. Cut stacking lip
    block = cut_stacking_lip(block, width, height)

    # 3. Hollow cavity — fit within lip recess (inset by BLOCK_MATING_INSET)
    # The lip recess inner width = grid_unit*width - 2*BLOCK_MATING_INSET
    # Subtract wall_thickness from each side
    lip_inner_w = width * GRID_UNIT - 2 * BLOCK_MATING_INSET
    lip_inner_h = height * GRID_UNIT - 2 * BLOCK_MATING_INSET

    cavity_w = lip_inner_w - 2 * wall_thickness
    cavity_h_dim = lip_inner_h - 2 * wall_thickness
    cavity_cr = max(0.5, FILLET_RADIUS - BLOCK_MATING_INSET - wall_thickness)

    floor_z = BLOCK_MATING_DEPTH + floor_thickness
    cavity_depth = body_h - floor_z + STACKING_MATING_DEPTH + 0.5

    cavity = (
        cq.Workplane("XY")
        .placeSketch(
            cq.Sketch()
            .rect(cavity_w, cavity_h_dim)
            .vertices()
            .fillet(cavity_cr)
        )
        .extrude(cavity_depth)
        .translate((0, 0, floor_z))
    )

    block = block.cut(cavity)

    # 4. Add bottom mating lip
    block = add_bottom_lip(block, width, height, magnets=magnets)

    return block
