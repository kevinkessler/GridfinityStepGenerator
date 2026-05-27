# GridfinityStepGenerator

Generate Gridfinity-compatible storage bins and baseplates as STEP files using CADQuery.

Output is parametric CAD (STEP format), not mesh (STL) — suitable for use in FreeCAD, Fusion 360, SolidWorks, etc.

## Quick Start

```bash
# Setup (one-time)
curl -Ls https://micro.mamba.pm/api/micromamba/linux-64/latest | tar -xvj bin/micromamba
./bin/micromamba create -p ./.conda-env -c conda-forge cadquery -y

# Generate a bin
./bin/micromamba run -p ./.conda-env python -m gridfinity_step.cli.cup 2 1 3 -o my_bin.step

# Generate a baseplate
./bin/micromamba run -p ./.conda-env python -m gridfinity_step.cli.baseplate 3 2 -o my_plate.step
```

## Bin Generator

```
python -m gridfinity_step.cli.cup <width> <height> <depth> [options]
```

Dimensions are in grid units (1 unit = 42mm wide, 7mm tall).

### Options

| Flag | Description | Default |
|---|---|---|
| `--wall`, `-w` | Wall thickness (mm, 0=auto) | 1.2 |
| `--floor`, `-f` | Floor thickness (mm) | 1.2 |
| `--magnets`, `-m` | Add magnet/screw holes | off |
| `--label` | Label wedge on wall (front/back/left/right) | off |
| `--finger-slide` | Finger slide on wall | off |
| `--tapered-corners` | Larger corner radius | off |
| `--vchambers` | Vertical divider count | 1 |
| `--hchambers` | Horizontal divider count | 1 |
| `--cutout` | Wall cutout (front/back/left/right) | off |
| `--sliding-lid` | Add groove for sliding lid | off |
| `--efficient-floor` | Fillet bottom edges | off |
| `--extend` | Connector tabs (x/y/both) | off |
| `--align-x` | Fractional extension position (near/far/center) | near |
| `--align-y` | Fractional extension position (near/far/center) | near |
| `--output`, `-o` | Output STEP file | gridfinity_bin.step |

### Examples

```bash
# Basic 2x1 bin, 3 units tall
python -m gridfinity_step.cli.cup 2 1 3

# 2x2 bin with 4 compartments, magnets, label
python -m gridfinity_step.cli.cup 2 2 3 --vchambers 2 --hchambers 2 --magnets --label back

# Fractional bin (1 full + 9mm extension)
python -m gridfinity_step.cli.cup 2 1.2143 3 --align-y far

# Bin with sliding lid groove + matching lid
python -m gridfinity_step.cli.cup 2 1 3 --sliding-lid -o bin.step
python -c "
from gridfinity_step.core.bin import make_lid
import cadquery as cq
lid = make_lid(2, 1, 3)
cq.exporters.export(lid, 'lid.step')
"
```

## Baseplate Generator

```
python -m gridfinity_step.cli.baseplate <width> <height> [--magnets]
```

```bash
# 3x2 baseplate with magnet holes
python -m gridfinity_step.cli.baseplate 3 2 --magnets -o plate.step
```

## Architecture

Based on [kmeisthax/gridfinity-cadquery](https://github.com/kmeisthax/gridfinity-cadquery) reference patterns.

```
gridfinity_step/
├── gridfinity.py      # Core: constants, profiles, block/lip/stack/base functions
├── baseplate.py       # Baseplate generator
├── export.py          # STEP/STL export
├── core/
│   └── bin.py         # make_bin() — full bin assembly with all features
└── cli/
    ├── cup.py         # Bin CLI
    └── baseplate.py   # Baseplate CLI
```
