"""CLI for gridfinity baseplate generation."""

import argparse
import sys

from gridfinity_step.baseplate import make_baseplate
from gridfinity_step.export import export_step


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description="Generate Gridfinity baseplate STEP files")
    parser.add_argument("width", type=float, help="Width in grid units")
    parser.add_argument("height", type=float, help="Height in grid units")
    parser.add_argument("--magnets", "-m", action="store_true", help="Add magnet holes")
    parser.add_argument("--output", "-o", default="baseplate.step", help="Output STEP file")
    args = parser.parse_args(argv)

    print(f"Generating {args.width:.3g}\u00d7{args.height:.3g} baseplate", end="")
    if args.magnets:
        print(" +magnets", end="")
    print()

    bp = make_baseplate(args.width, args.height, magnets=args.magnets)
    path = export_step(bp, args.output)
    print(f"STEP exported: {path}")


if __name__ == "__main__":
    main()
