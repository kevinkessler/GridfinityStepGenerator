"""Assemble a complete hollow Gridfinity bin with optional features."""

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


# ── Feature: Label tab ─────────────────────────────────────────────────

def _add_label_tab(
    block: cq.Workplane,
    width: int,
    height: int,
    depth: int,
    wall: str = "back",  # front, back, left, right
    label_width: float = 0,   # 0 = auto (full width)
    label_depth: float = 14,  # mm — how far out it sticks
    label_height: float = 0,  # 0 = auto
    corner_radius: float = 0.6,
):
    """Add a label tab protruding from one wall near the top."""
    outer_w = width * GRID_UNIT - BLOCK_SPACING
    outer_h = height * GRID_UNIT - BLOCK_SPACING
    body_h = _block_height(depth)

    # Auto-size: full width minus small margin, height ~¾ of tab depth
    if label_width <= 0:
        label_width = outer_w - 6 if wall in ("front", "back") else outer_h - 6
    if label_height <= 0:
        label_height = label_depth * 0.75

    # Create the tab as a rounded-rectangle extrusion
    tab = (
        cq.Workplane("XY")
        .placeSketch(
            cq.Sketch()
            .rect(label_width, label_depth)
            .vertices()
            .fillet(corner_radius)
        )
        .extrude(label_height)
    )

    # Position based on wall selection
    tab_z = body_h - label_height / 2 - 2  # near top
    half_w = outer_w / 2
    half_h = outer_h / 2

    positions = {
        "front":  (0, -half_h - label_depth / 2, tab_z),
        "back":   (0,  half_h + label_depth / 2, tab_z),
        "left":   (-half_w - label_depth / 2, 0, tab_z),
        "right":  (half_w + label_depth / 2, 0, tab_z),
    }

    if wall in positions:
        tab = tab.translate(positions[wall])
        block = block.union(tab)

    return block


# ── Feature: Finger slide ──────────────────────────────────────────────

def _add_finger_slide(
    block: cq.Workplane,
    width: int,
    height: int,
    wall: str = "front",
    radius: float = 8,
) -> cq.Workplane:
    """Add a large fillet to the top edge of one wall for easy part retrieval."""
    outer_w = width * GRID_UNIT - BLOCK_SPACING
    outer_h = height * GRID_UNIT - BLOCK_SPACING
    body_h = _block_height(depth=3)  # approximate

    # The top edge of the selected wall
    edge_positions = {
        "front": (0, -outer_h / 2, body_h),
        "back":  (0,  outer_h / 2, body_h),
        "left":  (-outer_w / 2, 0, body_h),
        "right": (outer_w / 2, 0, body_h),
    }

    if wall in edge_positions:
        try:
            block = (
                block
                .edges(cq.NearestToPointSelector(edge_positions[wall]))
                .fillet(radius)
            )
        except Exception:
            pass

    return block


# ── Feature: Tapered corner ────────────────────────────────────────────

def _add_tapered_corner(
    block: cq.Workplane,
    width: int,
    height: int,
    corners: str = "all",  # all, front_left, front_right, back_left, back_right
    radius: float = 10,
    setback: float = -1,  # -1 = auto
) -> cq.Workplane:
    """Apply a larger corner radius to specific corners."""
    outer_w = width * GRID_UNIT - BLOCK_SPACING
    outer_h = height * GRID_UNIT - BLOCK_SPACING
    body_h = _block_height(depth=3)

    if setback <= 0:
        setback = FILLET_RADIUS / 2

    corner_positions = {
        "front_left":  (-outer_w / 2, -outer_h / 2, body_h),
        "front_right": ( outer_w / 2, -outer_h / 2, body_h),
        "back_left":   (-outer_w / 2,  outer_h / 2, body_h),
        "back_right":  ( outer_w / 2,  outer_h / 2, body_h),
    }

    if corners == "all":
        targets = list(corner_positions.values())
    elif corners in corner_positions:
        targets = [corner_positions[corners]]
    else:
        targets = []

    for pos in targets:
        try:
            block = (
                block
                .edges(cq.NearestToPointSelector(pos))
                .fillet(radius)
            )
        except Exception:
            pass

    return block


# ── Main assembly ──────────────────────────────────────────────────────

def make_bin(
    width: int,
    height: int,
    depth: int,
    wall_thickness: float = 1.2,
    floor_thickness: float = 1.2,
    magnets: bool = False,
    # Label
    label_wall: str = "",
    label_width: float = 0,
    label_depth: float = 14,
    # Finger slide
    finger_slide_wall: str = "",
    finger_slide_radius: float = 8,
    # Tapered corner
    tapered_corners: str = "",
    tapered_radius: float = 10,
) -> cq.Workplane:
    """Create a hollow Gridfinity storage bin."""
    body_h = _block_height(depth)

    # 1. Solid block
    block = make_block(width, height, depth)

    # 2. Cut stacking lip
    block = cut_stacking_lip(block, width, height)

    # 3. Hollow cavity
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

    # 5. Optional features
    if label_wall:
        block = _add_label_tab(
            block, width, height, depth,
            wall=label_wall, label_width=label_width, label_depth=label_depth,
        )

    if finger_slide_wall:
        block = _add_finger_slide(
            block, width, height,
            wall=finger_slide_wall, radius=finger_slide_radius,
        )

    if tapered_corners:
        block = _add_tapered_corner(
            block, width, height,
            corners=tapered_corners, radius=tapered_radius,
        )

    return block
