"""Gridfinity STEP generator using CADQuery.

Based on the reference implementation by kmeisthax/gridfinity-cadquery.
Uses Sketch API for clean rounded-rectangle profiles.
"""

import math
import cadquery as cq

# ── Gridfinity spec constants ──────────────────────────────────────────

GRID_UNIT = 42.0          # mm — 1×1 baseplate size
BLOCK_SPACING = 0.5       # mm — gap between adjacent blocks
FILLET_RADIUS = 4.0       # mm — master fillet radius for mating surfaces

# Block body
GRID_DEPTH = 18.75        # mm — total depth per 2 height units
STACKING_CLEARANCE = 0.954  # mm — clearance at top for un-stacking

# Mating surfaces
BLOCK_MATING_DEPTH = 4.75   # mm — bottom lip depth (fits baseplate)
BASEPLATE_MATING_DEPTH = 4.4  # mm — baseplate socket depth
STACKING_MATING_DEPTH = 3.796  # mm — top lip depth (for stacking blocks)
BLOCK_MATING_INSET = 2.4    # mm — XY inset for block bottom lip
BASEPLATE_MATING_INSET = 2.15  # mm — XY inset for baseplate socket
BLOCK_MATING_CHAMFER = 0.8  # mm — bottom chamfer on block lip

# Stacking lip
BLOCK_STACKING_LIP = 0.77426   # mm — width of stacking lip overhang
BLOCK_STACKING_CHAMFER = 0.69645  # mm — chamfer on stacking lip

# Magnets
MAGNET_INSET = 8.0
MAGNET_DIAMETER = 6.5
MAGNET_DEPTH = 2.4
SCREW_DIAMETER = 3.5
SCREW_DEPTH = 6.0


# ── Profile helpers ────────────────────────────────────────────────────

def _inset_profile(gw: float, gh: float, inset: float) -> cq.Sketch:
    """Rounded rectangle sketch for a gw×gh grid-unit block, inset by `inset` mm."""
    w = gw * GRID_UNIT - inset * 2
    h = gh * GRID_UNIT - inset * 2
    return (
        cq.Sketch()
        .rect(w, h)
        .vertices()
        .fillet(FILLET_RADIUS - inset)
    )


def _block_height(depth: int) -> float:
    """Height of block body (excluding bottom lip) for given depth units."""
    return (GRID_DEPTH - BLOCK_MATING_DEPTH) / 2 * depth - STACKING_CLEARANCE


# ── Public API ─────────────────────────────────────────────────────────

def make_block(width: float, height: float, depth: int) -> cq.Workplane:
    """Create a solid Gridfinity block body (no lip, no cutouts)."""
    return (
        cq.Workplane("XY")
        .placeSketch(_inset_profile(width, height, BLOCK_SPACING / 2))
        .extrude(_block_height(depth))
    )


def cut_stacking_lip(block: cq.Workplane, width: float, height: float) -> cq.Workplane:
    """Cut the stacking lip into the top (>Z) face of a block."""
    top_z = block.faces(">Z").val().Center().z

    inset = (
        cq.Workplane("XY")
        .placeSketch(_inset_profile(width, height, BLOCK_MATING_INSET))
        .extrude(STACKING_MATING_DEPTH * -1)
        .translate((0, 0, top_z))
    )

    result = block.faces(">Z").cut(inset)

    try:
        result = (
            result
            .edges(cq.NearestToPointSelector((0, 0, top_z)))
            .chamfer(BLOCK_MATING_INSET - BLOCK_SPACING * 0.5 - BLOCK_STACKING_LIP)
            .edges(cq.NearestToPointSelector((0, 0, top_z - STACKING_MATING_DEPTH)))
            .chamfer(BLOCK_STACKING_CHAMFER)
            .edges(cq.NearestToPointSelector((
                width * GRID_UNIT / 2,
                height * GRID_UNIT / 2,
                top_z + 10,
            )))
            .fillet(BLOCK_STACKING_LIP / 2)
            .edges(cq.NearestToPointSelector((
                width * GRID_UNIT / 2 - BLOCK_STACKING_LIP * 4,
                height * GRID_UNIT / 2 - BLOCK_STACKING_LIP * 4,
                top_z + 2,
            )))
            .fillet(BLOCK_STACKING_LIP)
        )
    except Exception:
        pass

    return result


def _cell_sizes(dim: float, position: str = "near") -> list[tuple[float, bool]]:
    """Convert a fractional grid dimension into cell sizes, matching OpenSCAD's num_to_list.

    position: "near" (fraction at end), "far" (fraction at start), "center" (split both ends)
    """
    ceil_dim = math.ceil(dim)
    frac = dim - math.floor(dim)
    has_fractional = ceil_dim != dim

    if position == "center":
        half_frac = frac / 2
        full_cells = ceil_dim - (1 if has_fractional else 0)
        cells = []
        if has_fractional:
            cells.append((half_frac, False))
        for i in range(full_cells):
            is_corner = i == 0 or i == full_cells - 1
            cells.append((1.0, is_corner))
        if has_fractional:
            cells.append((half_frac, False))
        return cells

    count = ceil_dim
    has_pre = has_fractional and position == "far"
    has_post = has_fractional and position == "near"

    cells = []
    for i in range(count):
        if i == 0 and has_pre:
            cells.append((frac, False))
        elif i == count - 1 and has_post:
            cells.append((frac, False))
        else:
            is_corner = (
                (i == 0 and not has_pre) or
                (i == 1 and has_pre) or
                (i == count - 1 and not has_post) or
                (i == count - 2 and has_post)
            )
            cells.append((1.0, is_corner))
    return cells


def add_bottom_lip(
    block: cq.Workplane,
    width: float,
    height: float,
    magnets: bool = False,
    align_x: str = "near",
    align_y: str = "near",
) -> cq.Workplane:
    """Add the Gridfinity mating lip to the bottom (<Z) face.

    Uses OpenSCAD-style cell-based placement: ceil(N) cells per axis,
    each cell getting a pad proportional to its size.
    Fractional dimensions get a small pad at the position specified by align_x/align_y.
    """
    outer_w = width * GRID_UNIT - BLOCK_SPACING
    outer_h = height * GRID_UNIT - BLOCK_SPACING

    x_cells = _cell_sizes(width, align_x)
    y_cells = _cell_sizes(height, align_y)

    pad_grid = cq.Workplane("XY")
    accum_x = 0.0
    for cx, (cw, _is_corner_x) in enumerate(x_cells):
        accum_y = 0.0
        for cy, (ch, _is_corner_y) in enumerate(y_cells):
            # Cell center in world coordinates
            px = -outer_w / 2 + (accum_x + cw / 2) * GRID_UNIT
            py = -outer_h / 2 + (accum_y + ch / 2) * GRID_UNIT

            # Skip cells too small for pad geometry
            if cw * GRID_UNIT <= BLOCK_MATING_INSET * 2 + 1 or ch * GRID_UNIT <= BLOCK_MATING_INSET * 2 + 1:
                accum_y += ch
                continue

            # Create dual-taper pad matching OpenSCAD pad_oversize profile:
            # - Bottom: narrow section (approx 35.6mm per full cell)
            # - Top: wide section (approx 42.4mm per full cell, slightly wider than grid)
            # Built as two stacked sections unioned, with chamfer on bottom

            pad_h = BLOCK_MATING_DEPTH

            # Pad dimensions from OpenSCAD pad_oversize hull-of-cylinders:
            # pad_corner_position = [pitch/2 - corner_radius - clearance/2]
            #                       = [21 - 3.75 - 0.25] = [17, 17]
            # hull width = 2*pad_corner + cylinder_diameter
            #
            # Bottom (z=0):   cyl d=1.6 → width=34+1.6=35.6, cr=0.8
            # Bevel1 top:     cyl d=3.2 → width=34+3.2=37.2, cr=1.6 (at z=0.8)
            # Bevel2 bottom:  cyl d=3.2 → width=34+3.2=37.2, cr=1.6 (at z=2.6)
            # Top (z=5.0):    cyl d=8.4 → width=34+8.4=42.4, cr=4.2
            #
            # Convert to insets from 42mm cell boundary:
            #   inset = (42 - width) / 2
            #   bottom_inset = (42-35.6)/2 = 3.2
            #   mid_inset    = (42-37.2)/2 = 2.4
            #   top_inset    = (42-42.4)/2 = -0.2

            bottom_inset = 3.2
            mid_inset = 2.4
            top_inset = -0.2

            # Lower section (bevel1): z=0 to z=0.8, tapers 35.6→37.2
            bevel1_h = 0.8
            lower = (
                cq.Workplane("XY")
                .placeSketch(_inset_profile(cw, ch, bottom_inset))
                .extrude(bevel1_h * -1)
            )

            # Middle section (straight): z=0.8 to z=2.6, constant 37.2
            mid_h = 1.8
            middle = (
                cq.Workplane("XY")
                .placeSketch(_inset_profile(cw, ch, mid_inset))
                .extrude(mid_h * -1)
                .translate((0, 0, -bevel1_h))
            )

            # Upper section (bevel2 outward flare): z=2.6 to z=4.75, tapers 37.2→42.4
            upper_h = pad_h - bevel1_h - mid_h
            upper = (
                cq.Workplane("XY")
                .placeSketch(_inset_profile(cw, ch, top_inset))
                .extrude(upper_h * -1)
                .translate((0, 0, -bevel1_h - mid_h))
            )

            pad = lower.union(middle).union(upper)

            # Chamfer very bottom edge
            try:
                pad = pad.faces("<Z").chamfer(0.8)
            except Exception:
                pass

            pad_grid = pad_grid.union(
                cq.Workplane("XY").union(pad.val().moved(cq.Location(cq.Vector(px, py, 0))))
            )
            accum_y += ch
        accum_x += cw

    result = block.union(pad_grid)

    # Magnet/screw holes
    if magnets:
        result = (
            result.faces("<Z")
            .workplane()
            .rarray(GRID_UNIT, GRID_UNIT, len(x_cells), len(y_cells))
            .rect(GRID_UNIT - MAGNET_INSET * 2, GRID_UNIT - MAGNET_INSET * 2)
            .vertices()
            .cboreHole(SCREW_DIAMETER, MAGNET_DIAMETER, MAGNET_DEPTH, SCREW_DEPTH)
        )

    return result


def make_bin(
    width: float,
    height: float,
    depth: int,
    magnets: bool = False,
) -> cq.Workplane:
    """Create a complete Gridfinity bin in one go."""
    block = make_block(width, height, depth)
    block = cut_stacking_lip(block, width, height)
    block = add_bottom_lip(block, width, height, magnets=magnets)
    return block
