"""Gridfinity STEP generator using CADQuery.

Based on the reference implementation by kmeisthax/gridfinity-cadquery.
Uses Sketch API for clean rounded-rectangle profiles.
"""

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

def _inset_profile(gw: int, gh: int, inset: float) -> cq.Sketch:
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

def make_block(width: int, height: int, depth: int) -> cq.Workplane:
    """Create a solid Gridfinity block body (no lip, no cutouts)."""
    return (
        cq.Workplane("XY")
        .placeSketch(_inset_profile(width, height, BLOCK_SPACING / 2))
        .extrude(_block_height(depth))
    )


def cut_stacking_lip(block: cq.Workplane, width: int, height: int) -> cq.Workplane:
    """Cut the stacking lip into the top (>Z) face of a block.

    This creates the recessed rim that allows another block to stack on top.
    """
    top_z = block.faces(">Z").val().Center().z

    inset = (
        cq.Workplane("XY")
        .placeSketch(_inset_profile(width, height, BLOCK_MATING_INSET))
        .extrude(STACKING_MATING_DEPTH * -1)
        .translate((0, 0, top_z))
    )

    result = block.faces(">Z").cut(inset)

    # Chamfer and fillet the lip edges for smooth stacking
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
        pass  # fillets may fail on small geometry

    return result


def add_bottom_lip(
    block: cq.Workplane,
    width: int,
    height: int,
    magnets: bool = False,
) -> cq.Workplane:
    """Add the Gridfinity mating lip to the bottom (<Z) face.

    The lip has a grid of tapered feet that fit into a baseplate.
    """
    # Single 1×1 lip profile
    mating_sketch = _inset_profile(1, 1, BLOCK_MATING_INSET)
    lip_solid = (
        cq.Workplane("XY")
        .placeSketch(mating_sketch)
        .extrude(BLOCK_MATING_DEPTH * -1)
        .edges("<Z")
        .chamfer(BLOCK_MATING_CHAMFER)
    )

    # Place one lip per grid cell on the bottom face
    result = (
        block.faces("<Z")
        .rarray(GRID_UNIT, GRID_UNIT, width, height)
        .eachpoint(
            lambda loc: lip_solid.val().moved(loc),
            combine="a",
            clean=True,
        )
    )

    # Chamfer the inter-pad fillets
    for i in range(width):
        for j in range(height):
            x = (i * GRID_UNIT) - (width * GRID_UNIT / 2) + BLOCK_MATING_INSET
            y = (j * GRID_UNIT) - (height * GRID_UNIT / 2) + BLOCK_MATING_INSET
            try:
                result = (
                    result
                    .edges(cq.NearestToPointSelector((x, y, 0)))
                    .chamfer(BLOCK_MATING_INSET - BLOCK_SPACING * 0.5 - 0.01)
                )
            except Exception:
                continue

    # Magnet/screw holes
    if magnets:
        result = (
            result.faces("<Z")
            .workplane()
            .rarray(GRID_UNIT, GRID_UNIT, width, height)
            .rect(GRID_UNIT - MAGNET_INSET * 2, GRID_UNIT - MAGNET_INSET * 2)
            .vertices()
            .cboreHole(SCREW_DIAMETER, MAGNET_DIAMETER, MAGNET_DEPTH, SCREW_DEPTH)
        )

    return result


def make_bin(
    width: int,
    height: int,
    depth: int,
    magnets: bool = False,
) -> cq.Workplane:
    """Create a complete Gridfinity bin in one go."""
    block = make_block(width, height, depth)
    block = cut_stacking_lip(block, width, height)
    block = add_bottom_lip(block, width, height, magnets=magnets)
    return block
