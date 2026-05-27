"""CLI for gridfinity STEP generation."""

import argparse
import sys

from gridfinity_step.config import BinConfig, LipSettings
from gridfinity_step.core.bin import make_bin
from gridfinity_step.export import export_step
from gridfinity_step.constants import wall_thickness as calc_wt


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(
        description="Generate Gridfinity bin STEP files",
    )
    parser.add_argument(
        "--width", "-x", type=float, default=2,
        help="Width in grid units (42mm each)",
    )
    parser.add_argument(
        "--depth", "-y", type=float, default=1,
        help="Depth in grid units",
    )
    parser.add_argument(
        "--height", "-z", type=int, default=3,
        help="Height in grid units (7mm each)",
    )
    parser.add_argument(
        "--wall", "-w", type=float, default=0,
        help="Wall thickness in mm (0=auto)",
    )
    parser.add_argument(
        "--lip",
        choices=["normal", "reduced", "reduced_double", "minimum", "none"],
        default="normal",
        help="Lip style",
    )
    parser.add_argument(
        "--flat-base",
        choices=["off", "gridfinity", "rounded"],
        default="off",
        help="Base type",
    )
    parser.add_argument(
        "--floor", type=float, default=0.7,
        help="Floor thickness in mm",
    )
    parser.add_argument(
        "--no-notches", action="store_true",
        help="Disable lip notches",
    )
    parser.add_argument(
        "--headroom", type=float, default=0.8,
        help="Stacking headroom in mm",
    )
    parser.add_argument(
        "--output", "-o", default="gridfinity_bin.step",
        help="Output STEP file path",
    )
    parser.add_argument(
        "--stl", default=None,
        help="Also export STL for comparison",
    )
    args = parser.parse_args(argv)

    wt = calc_wt(args.wall, args.height)
    config = BinConfig(
        num_x=args.width,
        num_y=args.depth,
        num_z=args.height,
        wall_thickness=wt,
        lip=LipSettings(
            style=args.lip,
            notches=not args.no_notches,
        ),
        flat_base=args.flat_base,
        floor_thickness=args.floor,
        headroom=args.headroom,
    )

    print(f"Generating {args.width:.1f}x{args.depth:.1f}x{args.height} bin...")
    print(f"  Wall thickness: {wt:.2f}mm")
    print(f"  Lip style: {args.lip}")
    print(f"  Base: {args.flat_base}")

    bin_shape = make_bin(config)
    path = export_step(bin_shape, args.output)
    print(f"STEP exported: {path}")

    if args.stl:
        from gridfinity_step.export import export_stl
        stl_path = export_stl(bin_shape, args.stl)
        print(f"STL exported: {stl_path}")


if __name__ == "__main__":
    main()
