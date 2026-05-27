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
    parser.add_argument(
        "--wall", "-w", type=float, default=1.2,
        help="Wall thickness in mm",
    )
    parser.add_argument(
        "--floor", "-f", type=float, default=1.2,
        help="Floor thickness in mm",
    )
    parser.add_argument(
        "--magnets", "-m", action="store_true",
        help="Add magnet/screw holes",
    )
    parser.add_argument(
        "--output", "-o", default="gridfinity_bin.step",
        help="Output STEP file",
    )
    args = parser.parse_args(argv)

    print(f"Generating {args.width}×{args.height}×{args.depth} bin...")
    bin_shape = make_bin(
        args.width, args.height, args.depth,
        wall_thickness=args.wall,
        floor_thickness=args.floor,
        magnets=args.magnets,
    )
    path = export_step(bin_shape, args.output)
    print(f"STEP exported: {path}")


if __name__ == "__main__":
    main()
