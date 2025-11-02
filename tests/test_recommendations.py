"""Unit tests for print recommendations functionality."""
from pathlib import Path

import pytest
import trimesh

from src.core.recommendation import RecommendationEngine, MaterialType, PrinterType, MaterialPreset
from src.core.analysis import mesh_validator


def test_recommendation_engine_initialization():
    """Test RecommendationEngine initialization."""
    engine = RecommendationEngine()
    assert len(engine.get_available_materials()) > 0

    # Check default materials are loaded
    materials = engine.get_available_materials()
    assert "pla_standard" in materials
    assert "abs_standard" in materials
    assert "petg_standard" in materials
    assert "resin_standard" in materials


def test_material_preset_creation():
    """Test MaterialPreset creation and conversion."""
    preset = MaterialPreset(
        name="Test PLA",
        material_type=MaterialType.PLA,
        printer_type=PrinterType.FDM,
        nozzle_temp_min=190,
        nozzle_temp_max=220,
        bed_temp=60,
        print_speed=3600,
        travel_speed=9000,
        first_layer_speed=1800,
        layer_height_min=0.1,
        layer_height_max=0.3,
        layer_height_recommended=0.2,
        density=1.24,
        shrinkage_factor=0.3,
        min_wall_thickness=0.8,
        min_feature_size=0.4,
        support_angle_threshold=60.0,
        bed_adhesion_type="brim",
        cooling_fan=True
    )

    # Test to_dict conversion
    preset_dict = preset.to_dict()
    assert preset_dict["name"] == "Test PLA"
    assert preset_dict["material_type"] == "pla"
    assert preset_dict["nozzle_temp_min"] == 190


def test_material_recommendation_high_detail():
    """Test material recommendation for high detail models."""
    engine = RecommendationEngine()

    # Create validation result for high detail model
    mesh = trimesh.creation.icosphere(subdivisions=4, radius=5.0)

    validation_result = mesh_validator.validate_mesh(mesh)

    # Modify metrics to simulate high detail requirements
    if validation_result.metrics:
        # Simulate very fine features
        validation_result.metrics.min_feature_size_mm = 0.1
        validation_result.metrics.surface_roughness_score = 0.05

    material = engine.recommend_material(validation_result)
    assert material == "resin_standard"  # Should recommend resin for high detail


def test_material_recommendation_large_model():
    """Test material recommendation for large models."""
    engine = RecommendationEngine()

    # Create large box
    mesh = trimesh.creation.box(extents=[100.0, 100.0, 100.0])
    validation_result = mesh_validator.validate_mesh(mesh)

    material = engine.recommend_material(validation_result)
    # Should recommend ABS or similar for large models
    assert material in ["abs_standard", "petg_standard"]


def test_material_recommendation_default():
    """Test default material recommendation."""
    engine = RecommendationEngine()

    # Create simple box
    mesh = trimesh.creation.box(extents=[10.0, 10.0, 10.0])
    validation_result = mesh_validator.validate_mesh(mesh)

    material = engine.recommend_material(validation_result)
    assert material == "pla_standard"  # Should default to PLA


def test_infill_density_calculation():
    """Test infill density calculation."""
    engine = RecommendationEngine()

    mesh = trimesh.creation.box(extents=[10.0, 10.0, 10.0])
    validation_result = mesh_validator.validate_mesh(mesh)

    infill = engine.calculate_infill_density(validation_result)
    assert 10.0 <= infill <= 100.0  # Should be within reasonable bounds


def test_infill_density_thin_walls():
    """Test infill density for thin walls."""
    engine = RecommendationEngine()

    mesh = trimesh.creation.box(extents=[10.0, 10.0, 10.0])
    validation_result = mesh_validator.validate_mesh(mesh)

    # Simulate thin walls
    if validation_result.metrics:
        validation_result.metrics.min_wall_thickness_mm = 0.5

    infill = engine.calculate_infill_density(validation_result)

    # Should be higher than base for thin walls
    base_infill = 15.0
    assert infill > base_infill


def test_print_time_estimation():
    """Test print time estimation."""
    engine = RecommendationEngine()

    mesh = trimesh.creation.box(extents=[20.0, 20.0, 20.0])
    validation_result = mesh_validator.validate_mesh(mesh)

    material_preset = engine.get_material_preset("pla_standard")
    assert material_preset is not None

    print_time = engine.estimate_print_time(
        validation_result, material_preset, 0.2, 20.0
    )

    assert print_time > 0.1  # Should take at least some time
    assert print_time < 100.0  # Should be reasonable


def test_optimal_orientation():
    """Test optimal orientation determination."""
    engine = RecommendationEngine()

    mesh = trimesh.creation.box(extents=[30.0, 20.0, 10.0])
    validation_result = mesh_validator.validate_mesh(mesh)

    orientation, reason = engine.determine_optimal_orientation(validation_result)

    assert len(orientation) == 3  # Should be 3 Euler angles
    assert isinstance(reason, str)
    assert len(reason) > 0


def test_generate_comprehensive_recommendations():
    """Test comprehensive recommendation generation."""
    engine = RecommendationEngine()

    mesh = trimesh.creation.box(extents=[15.0, 15.0, 15.0])
    validation_result = mesh_validator.validate_mesh(mesh)

    recommendations = engine.generate_recommendations(validation_result)

    # Check all required fields are present
    assert recommendations.material_preset is not None
    assert recommendations.nozzle_temperature > 0
    assert recommendations.bed_temperature >= 0
    assert recommendations.print_speed > 0
    assert recommendations.layer_height > 0
    assert 0 <= recommendations.infill_density <= 100
    assert isinstance(recommendations.supports_required, bool)
    assert recommendations.estimated_print_time_hours > 0
    assert recommendations.estimated_material_volume_cm3 > 0
    assert len(recommendations.optimal_orientation) == 3


def test_recommendations_to_dict():
    """Test recommendations serialization."""
    engine = RecommendationEngine()

    mesh = trimesh.creation.box(extents=[10.0, 10.0, 10.0])
    validation_result = mesh_validator.validate_mesh(mesh)

    recommendations = engine.generate_recommendations(validation_result)
    recommendations_dict = recommendations.to_dict()

    assert isinstance(recommendations_dict, dict)
    assert "material_preset" in recommendations_dict
    assert "nozzle_temperature" in recommendations_dict
    assert "estimated_print_time_hours" in recommendations_dict


def test_save_recommendations(tmp_path):
    """Test saving recommendations to file."""
    engine = RecommendationEngine()

    mesh = trimesh.creation.box(extents=[10.0, 10.0, 10.0])
    validation_result = mesh_validator.validate_mesh(mesh)

    recommendations = engine.generate_recommendations(validation_result)

    output_path = tmp_path / "recommendations.json"
    engine.save_recommendations(recommendations, output_path)

    assert output_path.exists()

    # Verify file content
    import json
    with open(output_path) as f:
        data = json.load(f)

    assert "material_preset" in data
    assert "nozzle_temperature" in data


def test_get_material_preset():
    """Test getting specific material presets."""
    engine = RecommendationEngine()

    pla_preset = engine.get_material_preset("pla_standard")
    assert pla_preset is not None
    assert pla_preset.material_type == MaterialType.PLA

    abs_preset = engine.get_material_preset("abs_standard")
    assert abs_preset is not None
    assert abs_preset.material_type == MaterialType.ABS

    # Test non-existent preset
    none_preset = engine.get_material_preset("nonexistent")
    assert none_preset is None


def test_material_types_enum():
    """Test MaterialType enum values."""
    assert MaterialType.PLA.value == "pla"
    assert MaterialType.ABS.value == "abs"
    assert MaterialType.PETG.value == "petg"
    assert MaterialType.RESIN.value == "resin"


def test_printer_types_enum():
    """Test PrinterType enum values."""
    assert PrinterType.FDM.value == "fdm"
    assert PrinterType.SLA.value == "sla"
    assert PrinterType.SLS.value == "sls"


def test_recommendations_with_overhangs():
    """Test recommendations for models with overhangs."""
    engine = RecommendationEngine()

    mesh = trimesh.creation.box(extents=[10.0, 10.0, 10.0])
    validation_result = mesh_validator.validate_mesh(mesh)

    # Simulate overhangs
    if validation_result.metrics:
        validation_result.metrics.overhang_face_count = 15

    recommendations = engine.generate_recommendations(validation_result)

    assert recommendations.supports_required
    assert recommendations.support_type != "none"
    assert recommendations.support_density > 0


def test_recommendations_no_validation():
    """Test recommendations generation without validation result."""
    engine = RecommendationEngine()

    # Should not crash with None validation result
    recommendations = engine.generate_recommendations(None)

    assert recommendations is not None
    assert recommendations.material_preset is not None