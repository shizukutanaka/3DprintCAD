"""Regression tests for the PR #18 follow-up defects.

Covers three defects that were recorded as follow-ups and reproduced
against the pre-fix code:

1. MeshRepairer called ``Trimesh.remove_duplicate_faces()``, which was
   removed in trimesh 4.x, so the REMOVE_DUPLICATES operation always
   failed and duplicated faces survived repair. The mesh optimizer's
   cleaning step called the same removed API (plus the also-removed
   ``remove_degenerate_faces()``) and silently skipped cleaning.
2. ``InferenceOptimizer``'s background batch thread raised
   ``UnboundLocalError`` on every loop iteration (the local ``batch``
   was only assigned when the buffer was full) and logged
   "Batch processor error" roughly once per second forever.
3. Support generation placed support points below the build plate
   (no floor at the model's base plane, and pillars were built from a
   hardcoded z=0), producing inside-out pillars whose volume was then
   reported as 0. The advanced generator's pillar helper translated a
   centered cylinder to the segment start, leaving half of every
   pillar below its base.
"""

import logging
import time

import numpy as np
import trimesh

from src.core.analysis.ai_defect_detector import InferenceOptimizer
from src.core.analysis.mesh_optimization import MeshOptimizer
from src.core.analysis.mesh_repair import MeshRepairer, RepairOperation
from src.core.analysis.support_generator import (
    SupportGenerator,
    SupportSettings,
    SupportType,
)
from src.core.advanced_support_generation import AdvancedSupportGenerator


# ---------------------------------------------------------------------------
# Defect 1: removed trimesh 4.x APIs in mesh repair / optimization
# ---------------------------------------------------------------------------

def _box_with_duplicate_faces():
    box = trimesh.creation.box(extents=[1.0, 1.0, 1.0])
    faces = np.vstack([box.faces, box.faces[:3]])  # 3 duplicated faces
    return trimesh.Trimesh(
        vertices=box.vertices.copy(), faces=faces, process=False
    ), len(box.faces)


def test_repair_removes_duplicate_faces():
    mesh, unique_face_count = _box_with_duplicate_faces()
    repaired, summary = MeshRepairer().repair_mesh(mesh)

    op = next(
        o for o in summary.operations_performed
        if o.operation == RepairOperation.REMOVE_DUPLICATES
    )
    assert op.success, f"REMOVE_DUPLICATES failed: {op.message}"
    assert len(repaired.faces) == unique_face_count


def test_optimizer_clean_mesh_removes_duplicate_faces():
    mesh, unique_face_count = _box_with_duplicate_faces()
    cleaned = MeshOptimizer()._clean_mesh(mesh.copy())
    assert len(cleaned.faces) == unique_face_count


# ---------------------------------------------------------------------------
# Defect 2: batch processor error spam
# ---------------------------------------------------------------------------

def test_batch_processor_does_not_log_errors_when_idle(caplog):
    optimizer = InferenceOptimizer()
    try:
        with caplog.at_level(
            logging.DEBUG,
            logger="src.core.analysis.ai_defect_detector",
        ):
            # The defective loop logged about one error per second.
            time.sleep(1.6)
    finally:
        optimizer.shutdown()
    errors = [
        r for r in caplog.records
        if "Batch processor error" in r.getMessage()
    ]
    assert errors == []


# ---------------------------------------------------------------------------
# Defect 3: support points below the build plate / volume reported as 0
# ---------------------------------------------------------------------------

def _overhang_fixture():
    vertices = np.array([
        [0, 0, 0], [1, 0, 0], [1, 1, 0], [0, 1, 0],
        [0, 0, 2], [1, 0, 2], [1, 1, 2], [0, 1, 2],
        [0.5, 0.5, 4],
    ], dtype=np.float64)
    faces = np.array([
        [0, 2, 1], [0, 3, 2],
        [4, 5, 6], [4, 6, 7],
        [4, 5, 8], [5, 6, 8],
        [6, 7, 8], [7, 4, 8],
    ], dtype=np.int32)
    return trimesh.Trimesh(vertices=vertices, faces=faces, process=False)


def test_support_points_on_plate_and_volume_reported():
    mesh = _overhang_fixture()
    plate_z = 0.0  # build plate plane
    generator = SupportGenerator(
        SupportSettings(support_type=SupportType.TREE)
    )
    result = generator.generate_supports(mesh)

    assert result.success
    assert result.support_mesh is not None
    # No support point and no part of the support mesh below the plate.
    for point in result.support_points:
        assert point[2] >= plate_z
    assert result.support_mesh.bounds[0][2] >= plate_z - 1e-9
    # Real volume must be reported (was 0.0 before the fix).
    assert result.support_volume > 0


def test_support_pillars_reach_floating_model_from_plate():
    # A model floating above the plate: pillars must start at the
    # build plate (z=0) and reach up to the model, with real volume.
    mesh = _overhang_fixture()
    mesh.apply_translation([0, 0, 10.0])
    generator = SupportGenerator(
        SupportSettings(support_type=SupportType.TREE)
    )
    result = generator.generate_supports(mesh)

    assert result.success
    assert result.support_mesh is not None
    assert abs(result.support_mesh.bounds[0][2] - 0.0) < 1e-9
    assert result.support_volume > 0


def test_support_volume_reported_for_multi_level_model():
    # Two legs and a top slab: several overhang faces share the same
    # (x, y) axis at different heights. Emitting one pillar per point
    # produced duplicate cap faces on the shared base ring, the
    # combined mesh was not watertight, and its volume reported as 0.
    leg1 = trimesh.creation.box(extents=[1, 3, 3])
    leg1.apply_translation([-4, 0, 1.5])
    leg2 = trimesh.creation.box(extents=[1, 3, 3])
    leg2.apply_translation([4, 0, 1.5])
    top = trimesh.creation.box(extents=[9, 3, 1])
    top.apply_translation([0, 0, 3.5])
    mesh = trimesh.util.concatenate([leg1, leg2, top])

    generator = SupportGenerator(
        SupportSettings(support_type=SupportType.TREE)
    )
    result = generator.generate_supports(mesh)

    assert result.success
    assert result.support_mesh is not None
    assert result.support_mesh.is_volume
    assert result.support_volume > 0


def test_advanced_pillar_spans_start_to_end():
    generator = AdvancedSupportGenerator()
    start = np.array([1.0, 2.0, 0.5])
    end = np.array([1.0, 2.0, 3.5])
    pillar = generator._create_support_pillar(start, end, 0.4)

    assert len(pillar.faces) > 0
    # The pillar spans exactly start -> end: nothing below the base,
    # and it actually reaches the contact point.
    assert pillar.bounds[0][2] >= start[2] - 1e-9
    assert pillar.bounds[1][2] <= end[2] + 1e-9
    assert abs(pillar.bounds[1][2] - end[2]) < 1e-6
