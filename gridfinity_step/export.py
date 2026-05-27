"""Export CADQuery shapes to file formats."""

import cadquery as cq


def export_step(shape: cq.Workplane, filepath: str) -> str:
    """Export shape to STEP file (ISO 10303)."""
    cq.exporters.export(shape, filepath)
    return filepath


def export_stl(shape: cq.Workplane, filepath: str, tolerance: float = 0.01) -> str:
    """Export shape to STL (mesh) for 3D printing comparison."""
    cq.exporters.export(shape, filepath, exportType="STL", tolerance=tolerance)
    return filepath
