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


# ── Feature: Chamber dividers ──────────────────────────────────────────

def _add_dividers(
    block: cq.Workplane,
    width: int,
    height: int,
    depth: int,
    wall_thickness: float,
    floor_thickness: float,
    vertical: int = 1,
    horizontal: int = 1,
    divider_thickness: float = 1.2,
) -> cq.Workplane:
    """Add internal divider walls to split the bin into chambers.

    Args:
        vertical: Number of vertical chambers (dividers along X, spanning Y)
        horizontal: Number of horizontal chambers (dividers along Y, spanning X)
    """
    if vertical < 2 and horizontal < 2:
        return block

    body_h = _block_height(depth)
    lip_inner_w = width * GRID_UNIT - 2 * BLOCK_MATING_INSET
    lip_inner_h = height * GRID_UNIT - 2 * BLOCK_MATING_INSET
    cavity_w = lip_inner_w - 2 * wall_thickness
    cavity_h_dim = lip_inner_h - 2 * wall_thickness

    floor_z = BLOCK_MATING_DEPTH + floor_thickness
    divider_h = body_h - floor_z - 2  # leave small gap at top

    half_cw = cavity_w / 2
    half_ch = cavity_h_dim / 2

    # Vertical dividers (walls running in Y direction, at X intervals)
    for i in range(1, vertical):
        x_pos = -half_cw + i * (cavity_w / vertical)
        div = (
            cq.Workplane("XY")
            .box(divider_thickness, cavity_h_dim, divider_h)
            .translate((x_pos, 0, floor_z + divider_h / 2))
        )
        block = block.union(div)

    # Horizontal dividers (walls running in X direction, at Y intervals)
    for i in range(1, horizontal):
        y_pos = -half_ch + i * (cavity_h_dim / horizontal)
        div = (
            cq.Workplane("XY")
            .box(cavity_w, divider_thickness, divider_h)
            .translate((0, y_pos, floor_z + divider_h / 2))
        )
        block = block.union(div)

    return block


# ── Feature: Wall cutouts ──────────────────────────────────────────────

def _add_wall_cutout(
    block: cq.Workplane,
    width: int,
    height: int,
    depth: int,
    wall: str = "front",
    position: float = 0.5,     # 0-1 ratio along wall
    cutout_width: float = 20,  # mm
    cutout_height: float = 12, # mm
    corner_radius: float = 3,
) -> cq.Workplane:
    """Cut a rounded-rectangle opening in one wall for easy access."""
    outer_w = width * GRID_UNIT - BLOCK_SPACING
    outer_h = height * GRID_UNIT - BLOCK_SPACING
    body_h = _block_height(depth)

    half_w = outer_w / 2
    half_h = outer_h / 2

    # Cutout shape — a thin box that will cut through the wall
    cutout = (
        cq.Workplane("XY")
        .placeSketch(
            cq.Sketch()
            .rect(cutout_width, cutout_height)
            .vertices()
            .fillet(corner_radius)
        )
        .extrude(20)  # thick enough to cut through wall
    )

    # Position based on wall side and position ratio
    mid_z = body_h * 0.45  # roughly centered vertically

    wall_dirs = {
        "front": (0, -1, 0),  # face normal is -Y
        "back":  (0,  1, 0),  # face normal is +Y
        "left":  (-1, 0, 0),  # face normal is -X
        "right": (1,  0, 0),  # face normal is +X
    }

    if wall not in wall_dirs:
        return block

    nx, ny, _ = wall_dirs[wall]

    if nx != 0:  # left/right wall — cutout spans Y
        span = outer_h
        cutout_x = nx * (half_w - 5)  # 5mm outside the wall
        cutout_y = (position - 0.5) * span  # position along Y
    else:  # front/back wall — cutout spans X
        span = outer_w
        cutout_x = (position - 0.5) * span
        cutout_y = ny * (half_h - 5)

    cutout = cutout.translate((cutout_x, cutout_y, mid_z))
    block = block.cut(cutout)

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
    # Dividers
    vertical_chambers: int = 1,
    horizontal_chambers: int = 1,
    divider_thickness: float = 1.2,
    # Wall cutouts
    cutout_wall: str = "",
    cutout_width: float = 20,
    cutout_height: float = 12,
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

    # 5. Dividers (inside cavity)
    if vertical_chambers > 1 or horizontal_chambers > 1:
        block = _add_dividers(
            block, width, height, depth,
            wall_thickness, floor_thickness,
            vertical=vertical_chambers,
            horizontal=horizontal_chambers,
            divider_thickness=divider_thickness,
        )

    # 6. Wall cutout
    if cutout_wall:
        block = _add_wall_cutout(
            block, width, height, depth,
            wall=cutout_wall,
            cutout_width=cutout_width,
            cutout_height=cutout_height,
        )

    # 7. Optional features
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
