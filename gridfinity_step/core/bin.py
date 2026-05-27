"""Assemble a complete gridfinity bin from configuration.

All components follow the convention: bottom face at z=0.
Stacking: base → body → lip.
"""

import cadquery as cq

from gridfinity_step.constants import GF_ZPITCH, GF_BASE_TOTAL, GF_LIP_TOTAL
from gridfinity_step.config import BinConfig
from gridfinity_step.geometry import make_basic_bin
from gridfinity_step.features.lip import make_lip
from gridfinity_step.features.base import make_base


def make_bin(config: BinConfig) -> cq.Workplane:
    """Assemble a complete gridfinity bin.

    Base at z=0, body on top of base, lip on top of body.
    Centered on XY plane.
    """
    num_x = config.num_x
    num_y = config.num_y
    num_z = config.num_z
    wt = config.effective_wall_thickness
    body_height = num_z * GF_ZPITCH

    # Stack components vertically
    z_body = GF_BASE_TOTAL
    z_lip = GF_BASE_TOTAL + body_height

    # Base: bottom at z=0
    base = make_base(num_x, num_y, flat_base=config.flat_base)

    # Body: bottom at z=GF_BASE_TOTAL
    body = make_basic_bin(num_x, num_y, num_z, wt, config.floor_thickness)
    body = body.translate((0, 0, z_body))

    # Lip: bottom at z=GF_BASE_TOTAL + body_height
    if config.lip.style != "none":
        lip = make_lip(num_x, num_y, wt, config.lip.style, config.headroom)
        lip = lip.translate((0, 0, z_lip))
        result = base.union(body).union(lip)
    else:
        result = base.union(body)

    return result
