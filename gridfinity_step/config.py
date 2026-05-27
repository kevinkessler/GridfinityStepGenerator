from dataclasses import dataclass, field
from typing import Tuple

from gridfinity_step.constants import (
    GF_FLOOR_THICKNESS,
    GF_MAGNET_DIAMETER,
    GF_MAGNET_THICKNESS,
    GF_SCREW_DIAMETER,
    GF_SCREW_DEPTH,
)


@dataclass
class MagnetSettings:
    diameter: float = 0
    thickness: float = 0
    easy_release: str = "off"  # off, auto, inner, outer
    captive_height: float = 0
    side_access: str = "disabled"  # disabled, left, right
    crush_depth: float = 0
    chamfer: float = 0


@dataclass
class ScrewSettings:
    diameter: float = 0
    depth: float = 0


@dataclass
class LipSettings:
    style: str = "normal"  # normal, reduced, reduced_double, minimum, none
    notches: bool = True
    side_relief_trigger: Tuple[float, float] = (1, 1)
    top_relief_height: float = -1
    top_relief_width: float = -1
    clip_position: str = "disabled"
    non_blocking: bool = False


@dataclass
class LabelSettings:
    style: str = "disabled"
    position: str = "left"
    size: Tuple[float, float, float, float] = (0, 14, 0, 0.6)
    relief: Tuple[float, float, float, float] = (0, 0, 0, 0.6)
    walls: Tuple[int, int, int, int] = (0, 1, 0, 0)


@dataclass
class PatternSettings:
    enabled: bool = False
    style: str = "hexgrid"
    strength: float = 2
    rotate: bool = False
    fill: str = "none"
    border: float = 0
    depth: float = 0
    cell_size: Tuple[float, float] = (10, 10)
    hole_sides: int = 6
    hole_radius: float = 0.5
    grid_chamfer: float = 0
    voronoi_noise: float = 0.75
    brick_weight: float = 5
    quality: float = 0.4


@dataclass
class BinConfig:
    """All parameters for generating a gridfinity bin."""

    # Dimensions (gridfinity units)
    num_x: float = 2
    num_y: float = 1
    num_z: int = 3

    # Wall
    wall_thickness: float = 0  # 0 = auto

    # Lip / Stacking
    lip: LipSettings = field(default_factory=LipSettings)
    headroom: float = 0.8
    height_includes_lip: bool = False

    # Base
    magnets: MagnetSettings = field(default_factory=MagnetSettings)
    screws: ScrewSettings = field(default_factory=ScrewSettings)
    center_magnet: Tuple[float, float] = (0, 0)  # diameter, thickness
    flat_base: str = "off"  # off, gridfinity, rounded
    efficient_floor: str = "off"  # off, on, rounded, smooth
    floor_thickness: float = GF_FLOOR_THICKNESS
    cavity_floor_radius: float = -1
    spacer: bool = False
    filled_in: str = "disabled"  # disabled, enabled, enabledfilllip
    hole_overhang_remedy: int = 2
    box_corner_attachments_only: str = "enabled"
    sub_pitch: int = 1
    align_grid: Tuple[str, str] = ("near", "near")
    minimum_printable_pad_size: float = 0.2

    # Label
    label: LabelSettings = field(default_factory=LabelSettings)

    # Finger slide
    finger_slide: str = "none"
    finger_slide_radius: float = -3
    finger_slide_walls: Tuple[int, int, int, int] = (1, 0, 0, 0)
    finger_slide_lip_aligned: bool = True

    # Tapered corner
    tapered_corner: str = "none"
    tapered_corner_size: float = 10
    tapered_setback: float = -1

    # Rendering
    render_position: str = "center"  # default, center, zero

    @property
    def effective_wall_thickness(self) -> float:
        from gridfinity_step.constants import wall_thickness as calc_wt
        return calc_wt(self.wall_thickness, self.num_z)
