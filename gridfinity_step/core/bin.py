import math
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
    width: float,
    height: float,
    depth: int,
    wall_thickness: float,
    wall: str = "back",
    label_width: float = 0,
    label_depth: float = 14,
    label_height: float = 0,
):
    """Add a sloped label wedge on the INSIDE of one wall.

    The wedge is positioned just below the stacking lip, spanning nearly the
    full interior width of the wall. It slopes inward and downward into the
    cavity, creating an angled surface visible from above for sticking a label.
    """
    outer_w = width * GRID_UNIT - BLOCK_SPACING
    outer_h = height * GRID_UNIT - BLOCK_SPACING
    body_h = _block_height(depth)

    lip_inner_w = width * GRID_UNIT - 2 * BLOCK_MATING_INSET
    lip_inner_h = height * GRID_UNIT - 2 * BLOCK_MATING_INSET
    cavity_w = lip_inner_w - 2 * wall_thickness
    cavity_h_dim = lip_inner_h - 2 * wall_thickness

    if label_width <= 0:
        # Span full cavity + extend slightly into side walls for connection
        label_width = (cavity_w + wall_thickness * 2) if wall in ("front", "back") else (cavity_h_dim + wall_thickness * 2)
    if label_height <= 0:
        label_height = label_depth * 0.75

    # Clamp height to fit between floor and lip
    floor_z = BLOCK_MATING_DEPTH + 1.2  # approximate floor height
    z_top = body_h - STACKING_MATING_DEPTH  # just below lip
    max_height = z_top - floor_z
    label_height = min(label_height, max_height - 1)  # leave 1mm gap at bottom

    half_cw = cavity_w / 2
    half_ch = cavity_h_dim / 2

    wall_dirs = {
        "front": ("Y", -half_ch),   # inner face of front wall
        "back":  ("Y",  half_ch),    # inner face of back wall
        "left":  ("X", -half_cw),    # inner face of left wall
        "right": ("X",  half_cw),    # inner face of right wall
    }
    if wall not in wall_dirs:
        return block

    axis, wall_face = wall_dirs[wall]

    # Wedge extends from wall inner face toward center by label_depth,
    # but also extends wall_thickness INTO the wall for a solid connection
    if axis == "Y":
        wedge = cq.Workplane("XY").box(label_width, label_depth + wall_thickness, label_height)
        direction = -1 if wall == "back" else 1
        y_center = wall_face + direction * (label_depth - wall_thickness) / 2
        wedge = wedge.translate((0, y_center, z_top - label_height / 2))
    else:
        wedge = cq.Workplane("XY").box(label_depth + wall_thickness, label_width, label_height)
        direction = -1 if wall == "right" else 1
        x_center = wall_face + direction * (label_depth - wall_thickness) / 2
        wedge = wedge.translate((x_center, 0, z_top - label_height / 2))

    block = block.union(wedge)
    return block


# ── Feature: Finger slide ──────────────────────────────────────────────

def _add_finger_slide(
    block: cq.Workplane,
    width: float,
    height: float,
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
    width: float,
    height: float,
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
    width: float,
    height: float,
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
    width: float,
    height: float,
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


# ── Feature: Sliding lid ───────────────────────────────────────────────

def _add_sliding_lid_groove(
    block: cq.Workplane,
    width: float,
    height: float,
    depth: int,
    wall_thickness: float,
    lid_thickness: float = 0,
    clearance: float = 0.1,
    min_support: float = 0,
    min_wall: float = 0,
) -> cq.Workplane:
    """Cut a ledge around the inner perimeter for a sliding lid to rest on.

    The groove is cut just below the stacking lip, creating a wider opening
    at the top of the cavity where the lid slides in.
    """
    body_h = _block_height(depth)

    # Defaults based on wall_thickness (matching OpenSCAD defaults)
    if lid_thickness <= 0:
        lid_thickness = wall_thickness * 2
    if min_wall <= 0:
        min_wall = wall_thickness / 2
    if min_support <= 0:
        min_support = lid_thickness / 2

    outer_w = width * GRID_UNIT - BLOCK_SPACING
    outer_h = height * GRID_UNIT - BLOCK_SPACING

    # The groove is a wider cavity section at the top
    # It extends from below the lip down by lid_thickness + min_support
    groove_w = outer_w - clearance * 2 - min_wall * 2
    groove_h = outer_h - clearance * 2 - min_wall * 2
    groove_depth = lid_thickness + min_support + 0.5
    groove_z = body_h - groove_depth  # starts below the lip

    groove = (
        cq.Workplane("XY")
        .placeSketch(
            cq.Sketch()
            .rect(groove_w, groove_h)
            .vertices()
            .fillet(max(0.5, FILLET_RADIUS - min_wall))
        )
        .extrude(groove_depth)
        .translate((0, 0, groove_z + groove_depth / 2))
    )

    return block.cut(groove)


def make_lid(
    width: float,
    height: float,
    depth: int,
    wall_thickness: float = 1.2,
    lid_thickness: float = 0,
    clearance: float = 0.1,
    min_wall: float = 0,
) -> cq.Workplane:
    """Generate a separate sliding lid that fits the bin's groove.

    The lid is a flat rounded rectangle sized to fit into the groove
    with the specified clearance.
    """
    body_h = _block_height(depth)

    if lid_thickness <= 0:
        lid_thickness = wall_thickness * 2
    if min_wall <= 0:
        min_wall = wall_thickness / 2

    outer_w = width * GRID_UNIT - BLOCK_SPACING
    outer_h = height * GRID_UNIT - BLOCK_SPACING

    # Lid is slightly smaller than the groove for fit
    lid_w = outer_w - clearance * 2 - min_wall * 2 - 0.2
    lid_h = outer_h - clearance * 2 - min_wall * 2 - 0.2

    lid = (
        cq.Workplane("XY")
        .placeSketch(
            cq.Sketch()
            .rect(lid_w, lid_h)
            .vertices()
            .fillet(max(0.5, FILLET_RADIUS - min_wall - 0.2))
        )
        .extrude(lid_thickness)
        .translate((0, 0, lid_thickness / 2))
    )

    return lid


# ── Feature: Extendable sections ──────────────────────────────────────

def _add_extension_tabs(
    block: cq.Workplane,
    width: float,
    height: float,
    depth: int,
    wall_thickness: float,
    side: str = "x",  # "x", "y", or "both"
) -> cq.Workplane:
    """Add connector tabs on the sides for joining bins together."""
    outer_w = width * GRID_UNIT - BLOCK_SPACING
    outer_h = height * GRID_UNIT - BLOCK_SPACING
    body_h = _block_height(depth)

    tab_w = 10
    tab_d = 3
    tab_h = 4
    z_mid = body_h * 0.5

    if side in ("x", "both"):
        # Tabs on left and right edges
        for x_sign in [-1, 1]:
            x_center = x_sign * (outer_w / 2 + tab_d / 2)
            tab = (
                cq.Workplane("XY")
                .box(tab_d, tab_w, tab_h)
                .translate((x_center, 0, z_mid))
            )
            block = block.union(tab)

    if side in ("y", "both"):
        # Tabs on front and back edges
        for y_sign in [-1, 1]:
            y_center = y_sign * (outer_h / 2 + tab_d / 2)
            tab = (
                cq.Workplane("XY")
                .box(tab_w, tab_d, tab_h)
                .translate((0, y_center, z_mid))
            )
            block = block.union(tab)

    return block


# ── Main assembly ──────────────────────────────────────────────────────

def make_bin(
    width: float,
    height: float,
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
    # Sliding lid
    sliding_lid: bool = False,
    lid_thickness: float = 0,
    lid_clearance: float = 0.1,
    # Efficient floor
    efficient_floor: bool = False,
    # Extension tabs
    extension_side: str = "",
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

    # 3b. Efficient floor — fillet the bottom interior edges
    if efficient_floor:
        try:
            block = block.faces(">Z").edges(cq.NearestToPointSelector((0, 0, floor_z + 2))).fillet(2)
        except Exception:
            pass

    # 4. Add bottom mating lip
    block = add_bottom_lip(block, width, height, magnets=magnets)

    # 5. Sliding lid groove (before dividers so they don't block it)
    if sliding_lid:
        block = _add_sliding_lid_groove(
            block, width, height, depth,
            wall_thickness,
            lid_thickness=lid_thickness,
            clearance=lid_clearance,
        )

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
            block, width, height, depth, wall_thickness,
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

    if extension_side:
        block = _add_extension_tabs(
            block, width, height, depth, wall_thickness,
            side=extension_side,
        )

    return block
