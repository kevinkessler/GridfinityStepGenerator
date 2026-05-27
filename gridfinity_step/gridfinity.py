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


def _cell_sizes(dim: float) -> list[tuple[float, bool]]:
    """Convert a fractional grid dimension into cell sizes, matching OpenSCAD's num_to_list.

    Returns list of [cell_size_in_grid_units, is_outer_edge].
    e.g. 1.2143 → [[1.0, True], [0.2143, False]]
         2.0    → [[1.0, True], [1.0, True]]
    """
    ceil_dim = math.ceil(dim)
    frac = dim - math.floor(dim)
    has_fractional = ceil_dim != dim
    count = ceil_dim

    cells = []
    for i in range(count):
        if i == 0 and has_fractional and False:  # hasPrePad — only for center/far, not "near"
            cells.append((frac, False))
        elif i == count - 1 and has_fractional:   # hasPostPad — for "near" alignment
            cells.append((frac, False))
        else:
            is_corner = (i == 0) or (i == count - 1 and not has_fractional) or (i == count - 2 and has_fractional)
            cells.append((1.0, is_corner))
    return cells


def add_bottom_lip(
    block: cq.Workplane,
    width: float,
    height: float,
    magnets: bool = False,
) -> cq.Workplane:
    """Add the Gridfinity mating lip to the bottom (<Z) face.

    Uses OpenSCAD-style cell-based placement: ceil(N) cells per axis,
    each cell getting a pad proportional to its size.
    Fractional dimensions get a small pad at the fractional end.
    """
    outer_w = width * GRID_UNIT - BLOCK_SPACING
    outer_h = height * GRID_UNIT - BLOCK_SPACING

    x_cells = _cell_sizes(width)
    y_cells = _cell_sizes(height)

    pad_grid = cq.Workplane("XY")
    accum_x = 0.0
    for cx, (cw, _is_corner_x) in enumerate(x_cells):
        accum_y = 0.0
        for cy, (ch, _is_corner_y) in enumerate(y_cells):
            # Cell center in world coordinates
            px = -outer_w / 2 + (accum_x + cw / 2) * GRID_UNIT
            py = -outer_h / 2 + (accum_y + ch / 2) * GRID_UNIT

            # Create pad sized proportionally to cell
            pad_profile = _inset_profile(cw, ch, BLOCK_MATING_INSET)
            pad = (
                cq.Workplane("XY")
                .placeSketch(pad_profile)
                .extrude(BLOCK_MATING_DEPTH * -1)
                .edges("<Z")
                .chamfer(BLOCK_MATING_CHAMFER)
            )
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
