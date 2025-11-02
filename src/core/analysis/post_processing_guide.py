"""Enhanced post-processing guidance for 3D printed parts."""

from __future__ import annotations
from dataclasses import dataclass, field
from typing import List, Optional, Tuple, Dict, Any
from enum import Enum
import logging
import time
import numpy as np
import trimesh


class PostProcessTechnique(Enum):
    """Post-processing techniques."""
    SANDING = "sanding"
    PRIMING = "priming"
    PAINTING = "painting"
    POLISHING = "polishing"
    VAPOR_SMOOTHING = "vapor_smoothing"
    EPOXY_COATING = "epoxy_coating"
    HEAT_TREATMENT = "heat_treatment"
    UV_CURING = "uv_curing"
    CHEMICAL_SMOOTHING = "chemical_smoothing"
    MECHANICAL_POLISHING = "mechanical_polishing"


class MaterialType(Enum):
    """Material types for post-processing."""
    PLA = "PLA"
    ABS = "ABS"
    PETG = "PETG"
    TPU = "TPU"
    NYLON = "Nylon"
    ASA = "ASA"
    PC = "PC"
    WOOD = "Wood-filled"
    METAL = "Metal-filled"
    CARBON = "Carbon-filled"


@dataclass
class PostProcessingStep:
    """Individual post-processing step."""
    technique: PostProcessTechnique
    material_types: List[MaterialType]
    tools_required: List[str]
    estimated_time: float  # minutes
    difficulty: str  # Easy, Medium, Hard
    description: str
    tips: List[str]
    safety_notes: List[str]
    cost_estimate: float  # USD


@dataclass
class PostProcessingGuide:
    """Complete post-processing guide for a printed part."""
    material_type: MaterialType
    surface_quality_target: str  # Rough, Standard, Smooth, Mirror
    steps: List[PostProcessingStep]
    total_estimated_time: float
    total_cost_estimate: float
    warnings: List[str]
    final_tips: List[str]


class PostProcessingAdvisor:
    """Advanced post-processing guidance system."""

    def __init__(self):
        """Initialize the post-processing advisor."""
        self.logger = logging.getLogger(__name__)
        self.technique_database = self._build_technique_database()

    def _build_technique_database(self) -> Dict[MaterialType, Dict[str, List[PostProcessingStep]]]:
        """Build database of post-processing techniques for different materials."""
        database = {}

        # PLA techniques
        pla_steps = [
            PostProcessingStep(
                technique=PostProcessTechnique.SANDING,
                material_types=[MaterialType.PLA],
                tools_required=["Sandpaper (220-2000 grit)", "Sanding block"],
                estimated_time=15.0,
                difficulty="Easy",
                description="Remove layer lines with progressive sanding",
                tips=[
                    "Start with coarse grit (220) and progress to fine (2000)",
                    "Sand in circular motions to avoid scratches",
                    "Use water for wet sanding to reduce dust"
                ],
                safety_notes=["Wear dust mask", "Work in ventilated area"],
                cost_estimate=5.0
            ),
            PostProcessingStep(
                technique=PostProcessTechnique.PRIMING,
                material_types=[MaterialType.PLA],
                tools_required=["Primer spray", "Masking tape"],
                estimated_time=10.0,
                difficulty="Easy",
                description="Apply primer to seal surface and improve paint adhesion",
                tips=[
                    "Use plastic-specific primer",
                    "Apply thin, even coats",
                    "Allow proper drying time between coats"
                ],
                safety_notes=["Work in ventilated area", "Wear protective gloves"],
                cost_estimate=8.0
            ),
            PostProcessingStep(
                technique=PostProcessTechnique.PAINTING,
                material_types=[MaterialType.PLA],
                tools_required=["Acrylic paint", "Paint brushes", "Clear coat"],
                estimated_time=30.0,
                difficulty="Medium",
                description="Paint the surface for desired appearance",
                tips=[
                    "Use thin layers to avoid obscuring details",
                    "Apply clear coat for protection",
                    "Match paint type to application (matte, glossy, etc.)"
                ],
                safety_notes=["Work in ventilated area", "Use appropriate PPE"],
                cost_estimate=15.0
            )
        ]
        database[MaterialType.PLA] = {"standard": pla_steps}

        # ABS techniques
        abs_steps = [
            PostProcessingStep(
                technique=PostProcessTechnique.VAPOR_SMOOTHING,
                material_types=[MaterialType.ABS],
                tools_required=["Acetone", "Sealed container", "Gloves"],
                estimated_time=20.0,
                difficulty="Medium",
                description="Smooth surface using acetone vapor",
                tips=[
                    "Use controlled acetone vapor exposure",
                    "Monitor process closely to avoid over-smoothing",
                    "Allow 24 hours for full curing"
                ],
                safety_notes=["Highly flammable", "Use in fume hood", "Wear respirator"],
                cost_estimate=3.0
            ),
            PostProcessingStep(
                technique=PostProcessTechnique.SANDING,
                material_types=[MaterialType.ABS],
                tools_required=["Sandpaper (400-2000 grit)"],
                estimated_time=20.0,
                difficulty="Easy",
                description="Sand surface for smooth finish",
                tips=[
                    "ABS sands easily compared to other materials",
                    "Use progressively finer grits",
                    "Can achieve very smooth finish"
                ],
                safety_notes=["Wear dust mask", "Ventilate workspace"],
                cost_estimate=4.0
            )
        ]
        database[MaterialType.ABS] = {"standard": abs_steps}

        # PETG techniques
        petg_steps = [
            PostProcessingStep(
                technique=PostProcessTechnique.HEAT_TREATMENT,
                material_types=[MaterialType.PETG],
                tools_required=["Heat gun", "Oven", "Temperature controller"],
                estimated_time=45.0,
                difficulty="Hard",
                description="Heat treat to relieve internal stresses",
                tips=[
                    "Use controlled temperature (60-80°C)",
                    "Monitor for deformation",
                    "Allow slow cooling"
                ],
                safety_notes=["Risk of burns", "Fire hazard", "Use protective equipment"],
                cost_estimate=2.0
            ),
            PostProcessingStep(
                technique=PostProcessTechnique.SANDING,
                material_types=[MaterialType.PETG],
                tools_required=["Sandpaper (400-2000 grit)", "Polishing compound"],
                estimated_time=25.0,
                difficulty="Medium",
                description="Sand and polish for glossy finish",
                tips=[
                    "PETG can be polished to high gloss",
                    "Use automotive polishing compounds",
                    "Finish with microfiber cloth"
                ],
                safety_notes=["Wear protective eyewear", "Use dust extraction"],
                cost_estimate=12.0
            )
        ]
        database[MaterialType.PETG] = {"standard": petg_steps}

        return database

    def generate_guide(self, material_type: MaterialType,
                      surface_quality_target: str = "Standard",
                      print_time_hours: float = 1.0,
                      part_complexity: str = "Medium") -> PostProcessingGuide:
        """
        Generate comprehensive post-processing guide.

        Args:
            material_type: Material used for printing
            surface_quality_target: Desired surface quality (Rough, Standard, Smooth, Mirror)
            print_time_hours: Original print time in hours
            part_complexity: Complexity level (Simple, Medium, Complex)

        Returns:
            Complete post-processing guide
        """
        try:
            # Get material-specific techniques
            material_techniques = self.technique_database.get(material_type, {})
            quality_steps = material_techniques.get("standard", [])

            # Adjust for quality target
            if surface_quality_target.lower() == "rough":
                quality_steps = quality_steps[:1]  # Only basic sanding
            elif surface_quality_target.lower() == "mirror":
                # Add advanced polishing steps
                mirror_steps = quality_steps.copy()
                if material_type in [MaterialType.PLA, MaterialType.PETG]:
                    mirror_steps.append(PostProcessingStep(
                        technique=PostProcessTechnique.MECHANICAL_POLISHING,
                        material_types=[material_type],
                        tools_required=["Rotary tool", "Polishing compounds", "Microfiber cloths"],
                        estimated_time=60.0,
                        difficulty="Hard",
                        description="Achieve mirror-like finish through mechanical polishing",
                        tips=[
                            "Use progressively finer compounds",
                            "Work in small sections",
                            "Use light pressure to avoid heat buildup"
                        ],
                        safety_notes=["Eye protection required", "Use dust extraction"],
                        cost_estimate=25.0
                    ))
                quality_steps = mirror_steps

            # Calculate totals
            total_time = sum(step.estimated_time for step in quality_steps)
            total_cost = sum(step.cost_estimate for step in quality_steps)

            # Generate warnings
            warnings = self._generate_warnings(material_type, quality_steps)

            # Generate final tips
            final_tips = self._generate_final_tips(material_type, surface_quality_target)

            return PostProcessingGuide(
                material_type=material_type,
                surface_quality_target=surface_quality_target,
                steps=quality_steps,
                total_estimated_time=total_time,
                total_cost_estimate=total_cost,
                warnings=warnings,
                final_tips=final_tips
            )

        except Exception as e:
            self.logger.error(f"Guide generation failed: {e}")
            # Return basic guide on failure
            return PostProcessingGuide(
                material_type=material_type,
                surface_quality_target=surface_quality_target,
                steps=[],
                total_estimated_time=0.0,
                total_cost_estimate=0.0,
                warnings=["Guide generation failed, using manual methods"],
                final_tips=["Consult material-specific documentation"]
            )

    def _generate_warnings(self, material_type: MaterialType,
                          steps: List[PostProcessingStep]) -> List[str]:
        """Generate safety and process warnings."""
        warnings = []

        # Material-specific warnings
        if material_type == MaterialType.ABS:
            warnings.append("ABS produces fumes during processing - ensure excellent ventilation")
        elif material_type in [MaterialType.NYLON, MaterialType.CARBON]:
            warnings.append("Filled materials may require specialized tools and techniques")

        # Technique-specific warnings
        for step in steps:
            if step.technique == PostProcessTechnique.VAPOR_SMOOTHING:
                warnings.append("Acetone vapor smoothing is highly flammable - use extreme caution")
            elif step.technique == PostProcessTechnique.HEAT_TREATMENT:
                warnings.append("Heat treatment can cause deformation - monitor temperature closely")

        return warnings

    def _generate_final_tips(self, material_type: MaterialType,
                           quality_target: str) -> List[str]:
        """Generate final tips for best results."""
        tips = []

        tips.append("Always test post-processing techniques on scrap pieces first")
        tips.append("Document your process for consistent results")

        if quality_target.lower() == "mirror":
            tips.append("Mirror finishes require patience and multiple iterations")
            tips.append("Consider professional finishing services for critical applications")

        if material_type == MaterialType.PLA:
            tips.append("PLA responds well to sanding but avoid excessive heat during polishing")
        elif material_type == MaterialType.ABS:
            tips.append("ABS can achieve excellent finishes but requires good ventilation")

        return tips


def generate_post_processing_guide(material_type: MaterialType,
                                 surface_quality: str = "Standard",
                                 print_time: float = 1.0,
                                 complexity: str = "Medium") -> PostProcessingGuide:
    """
    Convenience function to generate post-processing guide.

    Args:
        material_type: Material used for printing
        surface_quality: Desired surface quality
        print_time: Original print time in hours
        complexity: Part complexity level

    Returns:
        Complete post-processing guide
    """
    advisor = PostProcessingAdvisor()
    return advisor.generate_guide(material_type, surface_quality, print_time, complexity)
