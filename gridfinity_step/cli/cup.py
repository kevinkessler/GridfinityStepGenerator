"""CLI for gridfinity STEP generation."""

import argparse
import sys

from gridfinity_step.core.bin import make_bin
from gridfinity_step.export import export_step


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(
        description="Generate Gridfinity bin STEP files",
    )
    parser.add_argument("width", type=int, help="Width in grid units")
    parser.add_argument("height", type=int, help="Height (depth) in grid units")
    parser.add_argument("depth", type=int, help="Bin depth (2 or 3 recommended)")
    parser.add_argument("--wall", "-w", type=float, default=1.2, help="Wall thickness (mm)")
    parser.add_argument("--floor", "-f", type=float, default=1.2, help="Floor thickness (mm)")
    parser.add_argument("--magnets", "-m", action="store_true", help="Add magnet/screw holes")

    # Label tab
    parser.add_argument("--label", choices=["front", "back", "left", "right"],
                        help="Add label tab on specified wall")
    parser.add_argument("--label-width", type=float, default=0, help="Label tab width (0=auto)")
    parser.add_argument("--label-depth", type=float, default=14, help="Label tab protrusion (mm)")

    # Finger slide
    parser.add_argument("--finger-slide", choices=["front", "back", "left", "right"],
                        help="Add finger slide on specified wall")
    parser.add_argument("--finger-radius", type=float, default=8, help="Finger slide fillet radius (mm)")

    # Tapered corners
    parser.add_argument("--tapered-corners", choices=["all", "front_left", "front_right", "back_left", "back_right"],
                        help="Add tapered corners")
    parser.add_argument("--tapered-radius", type=float, default=10, help="Tapered corner radius (mm)")

    # Dividers
    parser.add_argument("--vchambers", type=int, default=1,
                        help="Number of vertical chambers (dividers along X)")
    parser.add_argument("--hchambers", type=int, default=1,
                        help="Number of horizontal chambers (dividers along Y)")
    parser.add_argument("--divider-thickness", type=float, default=1.2,
                        help="Divider wall thickness (mm)")
    # Wall cutout
    parser.add_argument("--cutout", choices=["front", "back", "left", "right"],
                        help="Add wall cutout on specified wall")
    parser.add_argument("--cutout-width", type=float, default=20, help="Cutout width (mm)")
    parser.add_argument("--cutout-height", type=float, default=12, help="Cutout height (mm)")

    parser.add_argument("--output", "-o", default="gridfinity_bin.step", help="Output STEP file")
    args = parser.parse_args(argv)

    print(f"Generating {args.width}\u00d7{args.height}\u00d7{args.depth} bin", end="")
    if args.magnets:
        print(" +magnets", end="")
    if args.label:
        print(f" +label({args.label})", end="")
    if args.finger_slide:
        print(f" +finger({args.finger_slide})", end="")
    if args.tapered_corners:
        print(f" +taper({args.tapered_corners})", end="")
    if args.vchambers > 1:
        print(f" +vdiv({args.vchambers})", end="")
    if args.hchambers > 1:
        print(f" +hdiv({args.hchambers})", end="")
    if args.cutout:
        print(f" +cutout({args.cutout})", end="")
    print()

    bin_shape = make_bin(
        args.width, args.height, args.depth,
        wall_thickness=args.wall,
        floor_thickness=args.floor,
        magnets=args.magnets,
        label_wall=args.label or "",
        label_width=args.label_width,
        label_depth=args.label_depth,
        finger_slide_wall=args.finger_slide or "",
        finger_slide_radius=args.finger_radius,
        tapered_corners=args.tapered_corners or "",
        tapered_radius=args.tapered_radius,
        vertical_chambers=args.vchambers,
        horizontal_chambers=args.hchambers,
        divider_thickness=args.divider_thickness,
        cutout_wall=args.cutout or "",
        cutout_width=args.cutout_width,
        cutout_height=args.cutout_height,
    )
    path = export_step(bin_shape, args.output)
    print(f"STEP exported: {path}")


if __name__ == "__main__":
    main()
