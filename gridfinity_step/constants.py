# Gridfinity specification constants (mm)
# https://gridfinity.xyz/specification/

GF_PITCH = 42.0
GF_ZPITCH = 7.0
GF_CORNER_RADIUS = 3.75
GF_CLEARANCE = 0.5
GF_FLOOR_THICKNESS = 0.7

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
GF_BASE_PAD_DIAMETER = 12.0
GF_BASE_GRID_CLEARANCE = 3.5

# Magnet defaults
GF_MAGNET_DIAMETER = 6.5
GF_MAGNET_THICKNESS = 2.4
GF_SCREW_DIAMETER = 3.0
GF_SCREW_DEPTH = 6.0


def wall_thickness(user_thickness: float, num_z: int) -> float:
    """Auto-select wall thickness based on bin height (Zack's design)."""
    if user_thickness > 0:
        return user_thickness
    if num_z < 6:
        return 0.95
    if num_z < 12:
        return 1.2
    return 1.6
