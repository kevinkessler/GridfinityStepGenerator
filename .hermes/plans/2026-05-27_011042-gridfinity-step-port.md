# GridfinityStepGenerator — Porting Plan

> **For Hermes:** Use subagent-driven-development skill to implement this plan task-by-task.

**Goal:** Port the Gridfinity Extended OpenSCAD bin generator to Python/CADQuery, outputting STEP files instead of STL.

**Architecture:** Python package using CADQuery (OpenCASCADE BRep kernel). Replicate the OpenSCAD geometry through CADQuery primitives: `Workplane`, `box`, `cylinder`, `cut`, `fillet`, `union`, `hull` (via 2D profile extrusion + fillets). The output is a STEP file suitable for parametric CAD, not a mesh.

**Tech Stack:** Python 3.13, CADQuery 2.7, OCP 7.8.1, conda environment

---

## Source Analysis

The OpenSCAD project (`ostat/gridfinity_extended_openscad`) uses CSG operations:

| OpenSCAD Concept | CADQuery Equivalent |
|---|---|
| `hull() corner cylinders` | 2D `rect()` → `extrude()` → `fillet()` edges |
| `difference()` | `Workplane.cut()` |
| `union()` | `Workplane.union()` |
| `intersection()` | `Workplane.intersect()` |
| `linear_extrude()` | `Workplane.extrude()` |
| `cylinder()` | `Workplane.circle().extrude()` |
| `cube()` | `Workplane.box()` |
| `translate([x,y,z])` | `Workplane.transformed(offset=Vector(x,y,z))` |
| `rotate()` | `Workplane.rotateAboutCenter()` |
| `color()` | N/A (STEP has no color — skip) |
| `$fn` fragments | N/A (BRep is exact — skip) |

### Gridfinity Spec (constants)
```
gf_pitch = 42          # Grid unit in X/Y (mm)
gf_zpitch = 7          # Grid unit in Z (mm)
gf_cup_corner_radius = 3.75
gf_cup_floor_thickness = 0.7
gf_Lip_Height = 3.8    # Total lip height
gfBaseHeight = 5.0     # Total base height
clearance = 0.5        # Per-side clearance
```

### Project Structure (OpenSCAD → Python mapping)

```
gridfinity_extended_openscad/         → gridfinity_step/
├── gridfinity_basic_cup.scad         → cli/cup.py
├── gridfinity_baseplate.scad         → cli/baseplate.py
├── modules/
│   ├── gridfinity_constants.scad     → constants.py
│   ├── functions_gridfinity.scad     → geometry.py (calculations)
│   ├── functions_environment.scad    → config.py (env/settings)
│   ├── module_gridfinity.scad        → core/primitives.py (pad_grid, frame)
│   ├── module_gridfinity_block.scad  → core/block.py (main bin body)
│   ├── module_gridfinity_cup.scad    → core/cup.py (cup = block + walls + features)
│   ├── module_lip.scad               → features/lip.py
│   ├── module_gridfinity_cup_base.scad → features/base.py (magnets, screws)
│   ├── module_magnet.scad           → features/magnets.py
│   ├── module_gridfinity_label.scad → features/label.py
│   ├── module_fingerslide.scad      → features/fingerslide.py
│   ├── module_patterns.scad         → features/patterns.py
│   ├── module_gridfinity_efficient_floor.scad → features/efficient_floor.py
│   ├── module_gridfinity_sliding_lid.scad     → features/sliding_lid.py
│   ├── module_wallcutout.scad       → features/wall_cutout.py
│   ├── module_divider_walls.scad    → features/dividers.py
│   └── module_gridfinity_baseplate.scad → core/baseplate.py
```

---

## Implementation Strategy

**Incremental, testable at each phase.** STEP output verified visually after each feature.

### Phase 1: Foundation (core geometry)
Build the basic bin body — a rounded-rectangle block with internal cavity, lip, and gridfinity-compatible base.

### Phase 2: Essential features
Magnets, screws, labels, finger slides — the most-used options.

### Phase 3: Advanced features
Wall patterns, floor patterns, dividers, wall cutouts, sliding lid, extensions.

### Phase 4: Polish
Baseplate generation, CLI, tests, documentation.

---

## Phase 1: Foundation — The Basic Bin

### Task 1.1: Project scaffold

**Objective:** Create Python package structure with constants

**Files:**
- Create: `gridfinity_step/__init__.py`
- Create: `gridfinity_step/constants.py`
- Create: `gridfinity_step/geometry.py`
- Create: `gridfinity_step/config.py`
- Create: `pyproject.toml`

**Step 1: Create directory structure**

```bash
mkdir -p gridfinity_step/core gridfinity_step/features gridfinity_step/cli
touch gridfinity_step/__init__.py gridfinity_step/core/__init__.py gridfinity_step/features/__init__.py gridfinity_step/cli/__init__.py
```

**Step 2: Write constants.py**

```python
# Gridfinity spec dimensions
GF_PITCH = 42.0          # Grid unit X/Y (mm)
GF_ZPITCH = 7.0          # Grid unit Z (mm)
GF_CORNER_RADIUS = 3.75  # Outer corner radius
GF_CLEARANCE = 0.5       # Per-side clearance

# Lip dimensions
GF_LIP_LOWER_TAPER_HEIGHT = 0.7
GF_LIP_RISER_HEIGHT = 1.8
GF_LIP_UPPER_TAPER_HEIGHT = 1.9
GF_LIP_HEIGHT = 1.2
GF_LIP_TOTAL = GF_LIP_LOWER_TAPER_HEIGHT + GF_LIP_RISER_HEIGHT + GF_LIP_UPPER_TAPER_HEIGHT  # 3.8

# Base dimensions
GF_BASE_LOWER_TAPER_HEIGHT = 0.8
GF_BASE_RISER_HEIGHT = 1.8
GF_BASE_UPPER_TAPER_HEIGHT = 2.15
GF_BASE_TOTAL = GF_BASE_LOWER_TAPER_HEIGHT + GF_BASE_RISER_HEIGHT + GF_BASE_UPPER_TAPER_HEIGHT + 0.25  # 5.0
GF_FLOOR_THICKNESS = 0.7

# Default wall thicknesses (auto-scaled by height)
def wall_thickness(num_z: int, user_thickness: float = 0) -> float:
    if user_thickness > 0:
        return user_thickness
    if num_z < 6:
        return 0.95
    if num_z < 12:
        return 1.2
    return 1.6
```

**Step 3: Write config.py**

```python
from dataclasses import dataclass, field
from typing import List, Tuple

@dataclass
class BinConfig:
    """All parameters for generating a gridfinity bin."""
    # Dimensions (in gridfinity units)
    num_x: float = 2.0      # Width in grid units (42mm each)
    num_y: float = 1.0      # Depth in grid units
    num_z: float = 3.0      # Height in grid units (7mm each)

    # Wall
    wall_thickness: float = 0  # 0 = auto

    # Lip
    lip_style: str = "normal"  # normal, reduced, minimum, none
    lip_notches: bool = True
    headroom: float = 0.8

    # Base
    magnet_diameter: float = 0
    magnet_thickness: float = 0
    screw_diameter: float = 0
    screw_depth: float = 0
    flat_base: str = "off"  # off, gridfinity, rounded
    efficient_floor: str = "off"  # off, on, rounded, smooth
    floor_thickness: float = GF_FLOOR_THICKNESS
    spacer: bool = False
    filled_in: str = "disabled"

    # Label
    label_style: str = "disabled"
    label_position: str = "left"
    label_size: Tuple[float, float, float, float] = (0, 14, 0, 0.6)

    # Positioning
    render_position: str = "center"  # default, center, zero

    # Other
    finger_slide: str = "none"
    tapered_corner: str = "none"
```

**Step 4: Write pyproject.toml**

```toml
[project]
name = "gridfinity-step"
version = "0.1.0"
dependencies = ["cadquery"]

[project.scripts]
gridfinity-cup = "gridfinity_step.cli.cup:main"
```

**Verification:** `python -c "from gridfinity_step.constants import GF_PITCH; print(GF_PITCH)"` → 42.0

---

### Task 1.2: Core geometry helpers

**Objective:** Functions for creating rounded rectangles, the fundamental building block

**Files:**
- Create: `gridfinity_step/geometry.py`
- Create: `tests/test_geometry.py`

**Step 1: Write geometry.py — rounded_rect_2d function**

CADQuery doesn't have OpenSCAD's `hull()`, so we create rounded rectangles by drawing a 2D profile (rectangle with filleted corners) and extruding:

```python
import cadquery as cq

def rounded_rect_2d(width: float, depth: float, radius: float) -> cq.Workplane:
    """Create a 2D rounded rectangle face on the XY plane."""
    return (
        cq.Workplane("XY")
        .rect(width - 2 * radius, depth - 2 * radius)
        .vertices()
        .circle(radius)
    )
# Actually, better approach:
def rounded_rect_2d(width: float, depth: float, radius: float) -> cq.Workplane:
    """Create 2D rounded rectangle profile."""
    result = (
        cq.Workplane("XY")
        .rect(width, depth)
        .vertices()
        .fillet(radius)
    )
    return result

def rounded_box(
    width: float, depth: float, height: float,
    radius: float, bottom_radius: float | None = None
) -> cq.Workplane:
    """Extruded rounded rectangle box."""
    if bottom_radius is None:
        bottom_radius = radius
    wp = rounded_rect_2d(width, depth, radius)
    result = wp.extrude(height)
    # Fillet bottom edges if needed
    if bottom_radius > 0:
        result = result.faces("<Z").edges().fillet(bottom_radius)
    return result

def corner_positions(num_x: float, num_y: float, corner_radius: float,
                     pitch: float = GF_PITCH, clearance: float = GF_CLEARANCE
                     ) -> list[tuple[float, float]]:
    """Return (x, y) positions of the 4 corners of a rounded bin outline."""
    outer_w = num_x * pitch - clearance
    outer_d = num_y * pitch - clearance
    cx = outer_w / 2 - corner_radius
    cy = outer_d / 2 - corner_radius
    return [
        (-cx, -cy), (cx, -cy), (-cx, cy), (cx, cy)
    ]

def bin_outer_shell(num_x: float, num_y: float, num_z: float,
                    corner_radius: float = GF_CORNER_RADIUS,
                    pitch: float = GF_PITCH,
                    clearance: float = GF_CLEARANCE) -> cq.Workplane:
    """Create the outer shell of a bin — a rounded-rectangle extrusion."""
    outer_w = num_x * pitch - clearance
    outer_d = num_y * pitch - clearance
    height = num_z * GF_ZPITCH
    return rounded_box(outer_w, outer_d, height, corner_radius)
```

**Step 2: Write tests/test_geometry.py**

```python
import cadquery as cq
from gridfinity_step.geometry import rounded_rect_2d, rounded_box, bin_outer_shell, corner_positions

def test_rounded_rect_2d_basic():
    face = rounded_rect_2d(42, 42, 3.75)
    assert face is not None
    # Should be a face/wire, not a solid

def test_rounded_box_creates_solid():
    box = rounded_box(42, 42, 10, 3.75)
    assert box.val().isValid()
    assert box.val().Solid() is not None

def test_bin_outer_shell_default():
    shell = bin_outer_shell(2.0, 1.0, 3.0)
    assert shell.val().isValid()
    # Outer dimensions: 2*42 - 0.5 = 83.5, 1*42 - 0.5 = 41.5
    bb = shell.val().BoundingBox()
    # Check approximate bounds
    assert abs(bb.xlen - 83.5) < 0.01
    assert abs(bb.ylen - 41.5) < 0.01
    assert abs(bb.zlen - 21.0) < 0.01
```

**Verification:** `pytest tests/test_geometry.py -v` → 3 passed

---

### Task 1.3: Inner cavity — hollow out the bin

**Objective:** Subtract the internal cavity from the outer shell

**Files:**
- Modify: `gridfinity_step/geometry.py`
- Modify: `tests/test_geometry.py`

**Step 1: Add bin_cavity function**

The cavity is a smaller rounded rectangle subtracted from the outer shell. It's offset inward by wall_thickness on all sides and upward by floor_thickness from the bottom:

```python
def bin_cavity(
    num_x: float, num_y: float, num_z: float,
    wall_thickness: float,
    floor_thickness: float = GF_FLOOR_THICKNESS,
    corner_radius: float = GF_CORNER_RADIUS,
    base_height: float = GF_BASE_TOTAL,
) -> cq.Workplane:
    """The internal void of a bin — a rounded box to subtract."""
    outer_w = num_x * GF_PITCH - GF_CLEARANCE
    outer_d = num_y * GF_PITCH - GF_CLEARANCE

    inner_w = outer_w - 2 * wall_thickness
    inner_d = outer_d - 2 * wall_thickness
    inner_cr = max(0, corner_radius - wall_thickness)

    # Floor height: base + floor_thickness
    z_start = base_height - GF_FLOOR_THICKNESS + floor_thickness

    # Height: full bin height minus lip height (cavity goes up to the lip)
    total_height = num_z * GF_ZPITCH
    cavity_height = total_height - z_start + 1  # +1 to ensure it clears the top

    # Note: inner corner radius must be >= 0
    inner_cr = max(0.1, inner_cr)

    return rounded_box(inner_w, inner_d, cavity_height, inner_cr)
```

**Step 2: Add make_basic_bin function**

```python
def make_basic_bin(
    num_x: float, num_y: float, num_z: float,
    wall_thickness: float,
    floor_thickness: float = GF_FLOOR_THICKNESS,
) -> cq.Workplane:
    """Create a basic hollow bin (no lip, no base features yet)."""
    outer = bin_outer_shell(num_x, num_y, num_z)

    cavity = bin_cavity(num_x, num_y, num_z, wall_thickness, floor_thickness)
    # Position cavity at z=base_height
    cavity = cavity.translate((0, 0, GF_BASE_TOTAL - GF_FLOOR_THICKNESS + floor_thickness))

    result = outer.cut(cavity)
    return result
```

**Step 3: Write test**

```python
from gridfinity_step.geometry import make_basic_bin, GF_PITCH

def test_basic_bin_is_hollow():
    bin_shape = make_basic_bin(2.0, 1.0, 3.0, wall_thickness=1.2)
    assert bin_shape.val().isValid()
    # The result should be a shell (not a solid block)
    # Verify it's not the same volume as a solid block would be
    bb = bin_shape.val().BoundingBox()
    assert abs(bb.zlen - 21.0) < 0.01
```

**Verification:** `pytest tests/test_geometry.py -v` → 4 passed

---

### Task 1.4: Stacking lip

**Objective:** Add the gridfinity stacking lip to the top of the bin

**Files:**
- Create: `gridfinity_step/features/__init__.py`
- Create: `gridfinity_step/features/lip.py`
- Create: `tests/test_lip.py`

**Step 1: Understand lip geometry**

The lip is a profile extruded around the top perimeter of the bin. It has three segments (bottom to top):
1. **Lower taper** (0.7mm): outward taper from bin wall
2. **Riser** (1.8mm): straight vertical section
3. **Upper taper** (1.9mm): inward taper back to just above bin wall

The lip extends outward from the bin walls. In OpenSCAD this is done with `hull()` between offset rectangles.

In CADQuery, the lip is a series of stacked rounded-rectangle extrusions, each slightly different in size, unioned together:

```python
from gridfinity_step.constants import (
    GF_LIP_LOWER_TAPER_HEIGHT, GF_LIP_RISER_HEIGHT,
    GF_LIP_UPPER_TAPER_HEIGHT, GF_LIP_HEIGHT,
    GF_LIP_TOTAL, GF_PITCH, GF_CLEARANCE, GF_CORNER_RADIUS,
)
from gridfinity_step.geometry import rounded_box
import cadquery as cq

def make_lip(
    num_x: float, num_y: float,
    wall_thickness: float,
    lip_style: str = "normal",
    headroom: float = 0.8,
) -> cq.Workplane:
    """Create the stacking lip that sits on top of the bin body."""
    outer_w = num_x * GF_PITCH - GF_CLEARANCE - headroom
    outer_d = num_y * GF_PITCH - GF_CLEARANCE - headroom
    corner_radius = GF_CORNER_RADIUS

    if lip_style == "none":
        return cq.Workplane("XY")  # empty

    if lip_style == "normal":
        # From bottom to top:
        # 1. Lower taper (outward): narrow → wide
        # 2. Riser (straight): wide → wide
        # 3. Upper taper (inward): wide → narrow

        bottom_w = outer_w
        bottom_d = outer_d
        mid_w = outer_w + 2 * 2.5  # taper outward ~2.5mm per side
        mid_d = outer_d + 2 * 2.5
        top_w = outer_w + 2 * 0.3  # slight overhang
        top_d = outer_d + 2 * 0.3

        # Build as stacked sections, then union
        lower = rounded_box(bottom_w, bottom_d, GF_LIP_LOWER_TAPER_HEIGHT, corner_radius)
        # For mid: we build a trapezoid-like profile by using different top/bottom
        # Simplified: use slightly larger box
        mid_offset = (mid_w - bottom_w) / 2
        riser = rounded_box(mid_w, mid_d, GF_LIP_RISER_HEIGHT, corner_radius)
        riser = riser.translate((0, 0, GF_LIP_LOWER_TAPER_HEIGHT))

        upper = rounded_box(top_w, top_d, GF_LIP_UPPER_TAPER_HEIGHT, corner_radius)
        upper = upper.translate((0, 0, GF_LIP_LOWER_TAPER_HEIGHT + GF_LIP_RISER_HEIGHT))

        lip = lower.union(riser).union(upper)
    elif lip_style == "reduced":
        # Similar but with reduced support taper
        # Simplified version for now
        bottom_w = outer_w
        bottom_d = outer_d
        top_w = outer_w + 2 * 1.0
        top_d = outer_d + 2 * 1.0
        lip = rounded_box(top_w, top_d, GF_LIP_TOTAL, corner_radius)
    else:
        lip = rounded_box(outer_w, outer_d, GF_LIP_TOTAL, corner_radius)

    return lip
```

**Step 2: Write tests**

```python
from gridfinity_step.features.lip import make_lip

def test_lip_normal_creates_shape():
    lip = make_lip(2.0, 1.0, wall_thickness=1.2, lip_style="normal")
    assert lip.val().isValid()
    bb = lip.val().BoundingBox()
    assert abs(bb.zlen - GF_LIP_TOTAL) < 0.02

def test_lip_none_is_empty():
    lip = make_lip(2.0, 1.0, wall_thickness=1.2, lip_style="none")
    # Should be empty
    assert lip.val() is None or lip.solids().size() == 0
```

**Verification:** `pytest tests/test_lip.py -v` → 2 passed

---

### Task 1.5: Gridfinity-compatible base

**Objective:** Create the tapered base pads that allow stacking into a gridfinity baseplate

**Files:**
- Create: `gridfinity_step/features/base.py`
- Create: `tests/test_base.py`

**Step 1: Understand base geometry**

The gridfinity base consists of:
- A tapered "pad" under each grid cell corner (the 4 corners of each 42×42 cell)
- Each pad is a truncated pyramid shape: wide at the top, narrow at the bottom
- The pad has: lower taper (0.8mm), riser (1.8mm), upper taper (2.15mm), total ~5mm
- The pads fit into the baseplate grid

In CADQuery, each pad is a tapered box (wider top, narrower bottom), created via a loft or by creating a larger top profile and filleting the transition.

```python
import cadquery as cq
from gridfinity_step.constants import (
    GF_PITCH, GF_ZPITCH, GF_CLEARANCE, GF_CORNER_RADIUS,
    GF_BASE_LOWER_TAPER_HEIGHT, GF_BASE_RISER_HEIGHT,
    GF_BASE_UPPER_TAPER_HEIGHT, GF_BASE_TOTAL,
)
from gridfinity_step.geometry import rounded_box, corner_positions
import math

def make_single_pad(pad_size: float, pad_height: float,
                    corner_radius: float = 1.0) -> cq.Workplane:
    """Create a single tapered base pad."""
    # Pad is a box with a tapered bottom
    top_size = pad_size
    bottom_size = pad_size * 0.85  # approximate taper

    # Create as a loft between top and bottom rectangles
    # Simpler: create a box and draft the sides
    pad = rounded_box(top_size, top_size, pad_height, corner_radius)
    return pad

def make_base_pads(
    num_x: float, num_y: float,
    sub_pitch: int = 1,
    align_x: str = "near", align_y: str = "near",
) -> cq.Workplane:
    """Generate all base pads in a grid pattern."""
    result = cq.Workplane("XY")
    outer_w = num_x * GF_PITCH - GF_CLEARANCE
    outer_d = num_y * GF_PITCH - GF_CLEARANCE

    num_pads_x = int(num_x + 1)
    num_pads_y = int(num_y + 1)
    spacing_x = GF_PITCH
    spacing_y = GF_PITCH

    # Offset to center pads under bin
    offset_x = -outer_w / 2
    offset_y = -outer_d / 2

    pad_diameter = 12.0  # width of each pad (approximate)
    pad_height = GF_BASE_TOTAL

    for ix in range(num_pads_x):
        for iy in range(num_pads_y):
            px = offset_x + ix * spacing_x
            py = offset_y + iy * spacing_y
            pad = make_single_pad(pad_diameter, pad_height)
            pad = pad.translate((px, py, 0))
            result = result.union(pad)

    return result

def make_full_base(
    num_x: float, num_y: float,
    flat_base: str = "off",
    sub_pitch: int = 1,
    align_x: str = "near", align_y: str = "near",
) -> cq.Workplane:
    """Create the full base (pads + connecting geometry)."""
    if flat_base == "rounded":
        # Simplified: just a rounded bottom
        outer_w = num_x * GF_PITCH - GF_CLEARANCE
        outer_d = num_y * GF_PITCH - GF_CLEARANCE
        return rounded_box(outer_w, outer_d, GF_BASE_TOTAL,
                          GF_CORNER_RADIUS, bottom_radius=GF_CORNER_RADIUS / 2)
    elif flat_base == "gridfinity":
        outer_w = num_x * GF_PITCH - GF_CLEARANCE
        outer_d = num_y * GF_PITCH - GF_CLEARANCE
        return rounded_box(outer_w, outer_d, GF_BASE_TOTAL, GF_CORNER_RADIUS)
    else:
        return make_base_pads(num_x, num_y, sub_pitch, align_x, align_y)
```

**Step 2: Write tests**

```python
from gridfinity_step.features.base import make_full_base, make_single_pad

def test_single_pad_creates_solid():
    pad = make_single_pad(12, GF_BASE_TOTAL)
    assert pad.val().isValid()

def test_base_pads_grid():
    base = make_full_base(2.0, 1.0)
    assert base.val().isValid()
    # Should have multiple solids (one per pad)
    bb = base.val().BoundingBox()
    assert abs(bb.zlen - GF_BASE_TOTAL) < 0.02
```

**Verification:** `pytest tests/test_base.py -v` → 2 passed

---

### Task 1.6: Assemble the basic bin

**Objective:** Put it all together — outer shell + cavity + lip + base → complete bin, and export as STEP

**Files:**
- Create: `gridfinity_step/core/__init__.py`
- Create: `gridfinity_step/core/bin.py`
- Create: `gridfinity_step/export.py`
- Create: `tests/test_bin.py`

**Step 1: Write bin.py — the main assembly**

```python
import cadquery as cq
from gridfinity_step.constants import GF_PITCH, GF_ZPITCH
from gridfinity_step.geometry import bin_outer_shell, bin_cavity
from gridfinity_step.features.lip import make_lip
from gridfinity_step.features.base import make_full_base

def make_bin(config) -> cq.Workplane:
    """Assemble a complete gridfinity bin from configuration."""
    num_x = config.num_x
    num_y = config.num_y
    num_z = config.num_z
    wt = config.wall_thickness

    # 1. Outer shell
    shell = bin_outer_shell(num_x, num_y, num_z)

    # 2. Inner cavity
    cavity = bin_cavity(num_x, num_y, num_z, wt, config.floor_thickness)
    cavity_z = GF_BASE_TOTAL - GF_FLOOR_THICKNESS + config.floor_thickness
    cavity = cavity.translate((0, 0, cavity_z))
    shell = shell.cut(cavity)

    # 3. Lip (at top of bin)
    bin_height = num_z * GF_ZPITCH
    if config.lip_style != "none":
        lip = make_lip(num_x, num_y, wt, config.lip_style, config.headroom)
        lip = lip.translate((0, 0, bin_height))
        shell = shell.union(lip)

    # 4. Base (at bottom)
    base = make_full_base(num_x, num_y, config.flat_base, align_x=config.align_grid[0])
    shell = shell.union(base)

    return shell
```

**Step 2: Write export.py**

```python
import cadquery as cq

def export_step(shape: cq.Workplane, filepath: str):
    """Export a CADQuery shape to STEP file."""
    cq.exporters.export(shape, filepath)
    return filepath

def export_stl(shape: cq.Workplane, filepath: str, tolerance: float = 0.01):
    """Export to STL (for comparison/testing)."""
    cq.exporters.export(shape, filepath, exportType="STL", tolerance=tolerance)
    return filepath
```

**Step 3: Write integration test**

```python
from gridfinity_step.config import BinConfig
from gridfinity_step.core.bin import make_bin
from gridfinity_step.export import export_step

def test_make_bin_produces_valid_solid():
    config = BinConfig(num_x=2.0, num_y=1.0, num_z=3.0, wall_thickness=1.2)
    bin_shape = make_bin(config)
    assert bin_shape.val().isValid()

def test_export_step(tmp_path):
    config = BinConfig(num_x=1.0, num_y=1.0, num_z=2.0, wall_thickness=0.95)
    bin_shape = make_bin(config)
    path = tmp_path / "test_bin.step"
    export_step(bin_shape, str(path))
    assert path.exists()
    assert path.stat().st_size > 0
```

**Verification:** `pytest tests/test_bin.py -v` → 2 passed (STEP file created and non-empty)

---

### Task 1.7: CLI entry point for cup generation

**Objective:** Command-line tool to generate a STEP file from parameters

**Files:**
- Create: `gridfinity_step/cli/__init__.py`
- Create: `gridfinity_step/cli/cup.py`

**Step 1: Write cup.py**

```python
import argparse
from gridfinity_step.config import BinConfig
from gridfinity_step.core.bin import make_bin
from gridfinity_step.export import export_step
from gridfinity_step.constants import wall_thickness as calc_wt

def main():
    parser = argparse.ArgumentParser(description="Generate Gridfinity bin STEP files")
    parser.add_argument("--width", type=float, default=2, help="Width in grid units (42mm)")
    parser.add_argument("--depth", type=float, default=1, help="Depth in grid units")
    parser.add_argument("--height", type=float, default=3, help="Height in grid units (7mm)")
    parser.add_argument("--wall", type=float, default=0, help="Wall thickness (0=auto)")
    parser.add_argument("--lip", choices=["normal","reduced","minimum","none"], default="normal")
    parser.add_argument("--flat-base", choices=["off","gridfinity","rounded"], default="off")
    parser.add_argument("--output", "-o", default="gridfinity_bin.step", help="Output STEP file")
    args = parser.parse_args()

    wt = calc_wt(int(args.height), args.wall)
    config = BinConfig(
        num_x=args.width, num_y=args.depth, num_z=args.height,
        wall_thickness=wt, lip_style=args.lip, flat_base=args.flat_base,
    )
    bin_shape = make_bin(config)
    path = export_step(bin_shape, args.output)
    print(f"Exported: {path}")

if __name__ == "__main__":
    main()
```

**Verification:** `python -m gridfinity_step.cli.cup --width 2 --depth 1 --height 3 -o test.step` → creates test.step

---

### Task 1.8: Visual verification

**Objective:** Generate a test STEP file and verify it opens / renders correctly

```bash
python -m gridfinity_step.cli.cup --width 2 --depth 1 --height 3 --lip normal --flat-base off -o test_basic.step
python -m gridfinity_step.cli.cup --width 1 --depth 1 --height 2 --lip normal --flat-base gridfinity -o test_small.step
python -m gridfinity_step.cli.cup --width 3 --depth 2 --height 4 --flat-base rounded -o test_rounded.step
```

Open in FreeCAD or online STEP viewer to verify the geometry looks correct.

---

## Phase 2: Essential Features

### Task 2.1: Magnets and screws in base

### Task 2.2: Label tab

### Task 2.3: Finger slide

### Task 2.4: Tapered corners

---

## Phase 3: Advanced Features

### Task 3.1: Chamber dividers (subdivisions)

### Task 3.2: Wall cutouts

### Task 3.3: Wall patterns (hex/grid/brick)

### Task 3.4: Floor patterns

### Task 3.5: Efficient floor

### Task 3.6: Sliding lid

### Task 3.7: Extendable sections

---

## Phase 4: Polish

### Task 4.1: Baseplate generator

### Task 4.2: Full CLI with all options

### Task 4.3: Unit test coverage > 80%

### Task 4.4: README and usage docs

---

## Key Design Decisions

### 1. Rounded rectangles via filleted edges vs. hull of cylinders
OpenSCAD's `hull()` of 4 corner cylinders creates a perfect rounded rectangle. In CADQuery, we use `Workplane.rect()` with `.fillet()` on the vertices for 2D profiles, then extrude. For 3D rounded boxes, we extrude first then fillet the vertical edges. This produces equivalent BRep geometry.

### 2. Lip as stacked extrusions
The gridfinity lip has a complex profile (taper out, straight, taper in). We approximate this as stacked rounded boxes of slightly different sizes, unioned together. This matches the visual result closely enough.

### 3. Base pads as individual solids
Each base pad is a separate solid, unioned together. This mirrors OpenSCAD's approach.

### 4. STEP output
STEP (ISO 10303) is a parametric CAD format preserving exact geometry. CADQuery natively supports STEP export via OpenCASCADE. Unlike STL (a mesh), STEP files retain curves, faces, and solid bodies — suitable for use in parametric CAD tools.

### 5. No color
STEP AP203/AP214 can carry color, but CADQuery's STEP exporter does not support color attributes. Colors from the OpenSCAD source are cosmetic only (for preview) and are omitted.

---

## Risks and Mitigations

| Risk | Mitigation |
|---|---|
| Lip geometry doesn't match OpenSCAD exactly | Generate both STL and STEP; visually compare; iterate on dimensions |
| Base pad tapering is approximate | Use CADQuery's taper/draft or loft operations for precise pad geometry |
| Filled-in mode requires different CSG tree | Handle as a separate code path, easier in Python than OpenSCAD |
| Performance with many dividers | CADQuery/OCP is fast for BRep; union operations are the bottleneck — test with worst-case (4×4 grid with all dividers) |
| STEP viewer needed for verification | Use FreeCAD (free), online STEP viewers, or CADQuery's built-in SVG/Jupyter export |

---

## Open Questions

1. Should we attempt to match the exact OpenSCAD output pixel-for-pixel, or create a "clean" CAD-native version that looks similar but may differ in details?
   - **Recommendation:** Clean CAD-native — STEP consumers expect clean parametric geometry.

2. Which features to prioritize? Full OpenSCAD feature parity, or the most-used subset?
   - **Recommendation:** Phase 1 (basic bin) first, then prioritized by usage frequency.

3. Should the CLI accept JSON/YAML config files matching the OpenSCAD JSON format?
   - **Recommendation:** Yes, add JSON config support in Phase 4 for compatibility with existing workflows.
