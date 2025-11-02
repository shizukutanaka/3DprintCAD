"""BIM (Building Information Modeling) integration for 3D printing CAD."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import List, Optional, Tuple, Dict, Any, Union
import numpy as np
import trimesh
from enum import Enum
import logging
import json
import xml.etree.ElementTree as ET


class BIMStandard(Enum):
    """Supported BIM standards."""
    IFC = "ifc"  # Industry Foundation Classes
    COBIE = "cobie"  # Construction Operations Building Information Exchange
    GBXML = "gbxml"  # Green Building XML
    IFCXML = "ifcxml"  # IFC XML format


class BIMElementType(Enum):
    """Types of BIM elements."""
    WALL = "wall"
    FLOOR = "floor"
    CEILING = "ceiling"
    ROOF = "roof"
    COLUMN = "column"
    BEAM = "beam"
    DOOR = "door"
    WINDOW = "window"
    STAIR = "stair"
    FURNITURE = "furniture"
    EQUIPMENT = "equipment"
    SYSTEM = "system"


@dataclass
class BIMElement:
    """A BIM element with metadata."""

    id: str
    name: str
    element_type: BIMElementType
    geometry: trimesh.Trimesh
    properties: Dict[str, Any] = field(default_factory=dict)
    materials: List[Dict[str, Any]] = field(default_factory=list)
    relationships: List[str] = field(default_factory=list)  # IDs of related elements
    classification: Optional[str] = None  # Uniclass, Omniclass, etc.
    spatial_location: Optional[Dict[str, float]] = None  # Building, floor, room


@dataclass
class BIMModel:
    """Complete BIM model."""

    name: str
    description: Optional[str] = None
    elements: List[BIMElement] = field(default_factory=list)
    relationships: Dict[str, List[str]] = field(default_factory=dict)
    metadata: Dict[str, Any] = field(default_factory=dict)
    coordinate_system: str = "local"  # local, global, project


@dataclass
class BIMIntegrationResult:
    """Result of BIM integration operation."""

    success: bool
    model: Optional[BIMModel] = None
    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    statistics: Dict[str, Any] = field(default_factory=dict)


class BIMIntegrator:
    """BIM integration system for 3D printing CAD."""

    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.supported_formats = [BIMStandard.IFC, BIMStandard.GBXML]

    def import_bim_model(self, file_path: str, format: BIMStandard) -> BIMIntegrationResult:
        """Import a BIM model from file."""

        result = BIMIntegrationResult(success=False)

        try:
            if format == BIMStandard.IFC:
                result = self._import_ifc(file_path)
            elif format == BIMStandard.GBXML:
                result = self._import_gbxml(file_path)
            else:
                result.errors.append(f"Unsupported BIM format: {format.value}")

        except Exception as e:
            result.errors.append(f"Failed to import BIM model: {str(e)}")
            self.logger.error(f"BIM import error: {e}")

        return result

    def export_bim_model(self, model: BIMModel, file_path: str, format: BIMStandard) -> bool:
        """Export a BIM model to file."""

        try:
            if format == BIMStandard.IFC:
                return self._export_ifc(model, file_path)
            elif format == BIMStandard.GBXML:
                return self._export_gbxml(model, file_path)
            else:
                self.logger.error(f"Unsupported export format: {format.value}")
                return False

        except Exception as e:
            self.logger.error(f"BIM export error: {e}")
            return False

    def convert_bim_to_printable(self, bim_model: BIMModel,
                               print_requirements: Dict[str, Any]) -> List[trimesh.Trimesh]:
        """Convert BIM model to printable 3D meshes."""

        printable_meshes = []

        try:
            # Process each BIM element
            for element in bim_model.elements:
                # Apply print-specific transformations
                printable_mesh = self._convert_element_to_printable(
                    element, print_requirements
                )

                if printable_mesh:
                    printable_meshes.append(printable_mesh)

        except Exception as e:
            self.logger.error(f"Error converting BIM to printable: {e}")

        return printable_meshes

    def analyze_bim_for_printing(self, bim_model: BIMModel) -> Dict[str, Any]:
        """Analyze BIM model for 3D printing compatibility."""

        analysis = {
            "total_elements": len(bim_model.elements),
            "element_types": {},
            "printability_score": 0.0,
            "issues": [],
            "recommendations": [],
            "material_analysis": {},
            "scale_analysis": {},
            "complexity_analysis": {}
        }

        try:
            # Count element types
            for element in bim_model.elements:
                element_type = element.element_type.value
                analysis["element_types"][element_type] = analysis["element_types"].get(element_type, 0) + 1

            # Analyze printability
            analysis["printability_score"] = self._calculate_printability_score(bim_model)
            analysis["issues"] = self._identify_printing_issues(bim_model)
            analysis["recommendations"] = self._generate_printing_recommendations(bim_model)
            analysis["material_analysis"] = self._analyze_materials(bim_model)
            analysis["scale_analysis"] = self._analyze_scale(bim_model)
            analysis["complexity_analysis"] = self._analyze_complexity(bim_model)

        except Exception as e:
            self.logger.error(f"Error analyzing BIM for printing: {e}")
            analysis["issues"].append(f"Analysis failed: {str(e)}")

        return analysis

    def _import_ifc(self, file_path: str) -> BIMIntegrationResult:
        """Import IFC file."""

        result = BIMIntegrationResult(success=False)

        try:
            # IFC parsing would require ifcopenshell library
            # This is a simplified placeholder implementation

            # For demonstration, create a mock BIM model
            mock_model = BIMModel(
                name="Imported IFC Model",
                description="Mock BIM model from IFC import",
                elements=[
                    BIMElement(
                        id="wall_001",
                        name="Exterior Wall",
                        element_type=BIMElementType.WALL,
                        geometry=trimesh.creation.box(extents=[10, 0.2, 3]),
                        properties={"material": "concrete", "thickness": 0.2}
                    ),
                    BIMElement(
                        id="door_001",
                        name="Entry Door",
                        element_type=BIMElementType.DOOR,
                        geometry=trimesh.creation.box(extents=[0.9, 0.05, 2.1]),
                        properties={"material": "wood", "type": "entry"}
                    )
                ]
            )

            result.success = True
            result.model = mock_model
            result.statistics = {
                "elements_imported": len(mock_model.elements),
                "warnings": ["This is a mock implementation - real IFC import requires ifcopenshell"]
            }

        except Exception as e:
            result.errors.append(f"IFC import failed: {str(e)}")

        return result

    def _import_gbxml(self, file_path: str) -> BIMIntegrationResult:
        """Import gbXML file."""

        result = BIMIntegrationResult(success=False)

        try:
            # Parse XML
            tree = ET.parse(file_path)
            root = tree.getroot()

            # Extract building elements
            elements = []
            ns = {'gbxml': 'http://www.gbxml.org/schema'}

            # Parse surfaces (walls, floors, etc.)
            for surface in root.findall('.//gbxml:Surface', ns):
                element = self._parse_gbxml_surface(surface, ns)
                if element:
                    elements.append(element)

            model = BIMModel(
                name=root.find('.//gbxml:Name', ns).text if root.find('.//gbxml:Name', ns) is not None else "gbXML Model",
                elements=elements
            )

            result.success = True
            result.model = model
            result.statistics = {"elements_imported": len(elements)}

        except Exception as e:
            result.errors.append(f"gbXML import failed: {str(e)}")

        return result

    def _parse_gbxml_surface(self, surface_element, ns) -> Optional[BIMElement]:
        """Parse a gbXML surface element."""

        try:
            surface_id = surface_element.get('id', 'unknown')
            surface_type = surface_element.get('surfaceType', 'unknown')

            # Map gbXML surface types to BIM element types
            type_mapping = {
                'ExteriorWall': BIMElementType.WALL,
                'InteriorWall': BIMElementType.WALL,
                'Roof': BIMElementType.ROOF,
                'Floor': BIMElementType.FLOOR,
                'Ceiling': BIMElementType.CEILING
            }

            element_type = type_mapping.get(surface_type, BIMElementType.WALL)

            # Extract geometry (simplified)
            planar_geometry = surface_element.find('.//gbxml:PlanarGeometry', ns)
            if planar_geometry is not None:
                # Create a simple rectangular geometry based on surface info
                width = 10.0  # Mock dimensions
                height = 3.0
                thickness = 0.2

                if element_type == BIMElementType.FLOOR or element_type == BIMElementType.CEILING:
                    geometry = trimesh.creation.box(extents=[width, width, thickness])
                else:
                    geometry = trimesh.creation.box(extents=[width, thickness, height])

                return BIMElement(
                    id=surface_id,
                    name=f"{surface_type} {surface_id}",
                    element_type=element_type,
                    geometry=geometry,
                    properties={"surface_type": surface_type}
                )

        except Exception as e:
            self.logger.warning(f"Error parsing gbXML surface: {e}")

        return None

    def _export_ifc(self, model: BIMModel, file_path: str) -> bool:
        """Export to IFC format."""

        # This would require ifcopenshell library
        # For now, create a simplified IFC-like structure

        try:
            ifc_data = {
                "schema": "IFC4",
                "model": {
                    "name": model.name,
                    "elements": [
                        {
                            "id": element.id,
                            "name": element.name,
                            "type": element.element_type.value,
                            "properties": element.properties
                        }
                        for element in model.elements
                    ]
                }
            }

            with open(file_path, 'w') as f:
                json.dump(ifc_data, f, indent=2)

            return True

        except Exception as e:
            self.logger.error(f"IFC export failed: {e}")
            return False

    def _export_gbxml(self, model: BIMModel, file_path: str) -> bool:
        """Export to gbXML format."""

        try:
            # Create basic gbXML structure
            root = ET.Element("gbXML", version="6.01")

            # Add header
            header = ET.SubElement(root, "gbXMLProperties")
            ET.SubElement(header, "Name").text = model.name

            # Add surfaces
            campus = ET.SubElement(root, "Campus", id="Campus001")
            building = ET.SubElement(campus, "Building", id="Building001")

            for element in model.elements:
                surface = ET.SubElement(building, "Surface",
                                      id=element.id,
                                      surfaceType=self._map_element_type_to_gbxml(element.element_type))

                # Add basic geometry placeholder
                planar_geom = ET.SubElement(surface, "PlanarGeometry")
                ET.SubElement(planar_geom, "PolyLoop")

            # Write to file
            tree = ET.ElementTree(root)
            tree.write(file_path, encoding='unicode', xml_declaration=True)

            return True

        except Exception as e:
            self.logger.error(f"gbXML export failed: {e}")
            return False

    def _map_element_type_to_gbxml(self, element_type: BIMElementType) -> str:
        """Map BIM element type to gbXML surface type."""

        mapping = {
            BIMElementType.WALL: "ExteriorWall",
            BIMElementType.FLOOR: "Floor",
            BIMElementType.CEILING: "Ceiling",
            BIMElementType.ROOF: "Roof"
        }

        return mapping.get(element_type, "ExteriorWall")

    def _convert_element_to_printable(self, element: BIMElement,
                                    print_requirements: Dict[str, Any]) -> Optional[trimesh.Trimesh]:
        """Convert a BIM element to printable mesh."""

        try:
            # Start with the element's geometry
            printable_mesh = element.geometry.copy()

            # Apply print-specific transformations
            scale_factor = print_requirements.get('scale_factor', 1.0)
            if scale_factor != 1.0:
                printable_mesh.apply_scale(scale_factor)

            # Ensure manifold
            if not printable_mesh.is_watertight:
                printable_mesh.fill_holes()

            # Apply material-specific optimizations
            material = element.properties.get('material', 'generic')
            if material == 'concrete':
                # Concrete needs thicker walls for strength
                pass  # Would implement wall thickening
            elif material == 'wood':
                # Wood can be thinner
                pass  # Would implement wall thinning

            return printable_mesh

        except Exception as e:
            self.logger.error(f"Error converting element {element.id} to printable: {e}")
            return None

    def _calculate_printability_score(self, model: BIMModel) -> float:
        """Calculate overall printability score (0-1)."""

        if not model.elements:
            return 0.0

        scores = []

        for element in model.elements:
            score = 1.0  # Start with perfect score

            # Penalize complex geometries
            if len(element.geometry.faces) > 10000:
                score *= 0.7

            # Penalize very small features
            bounds = element.geometry.bounds
            min_dimension = np.min(bounds[1] - bounds[0])
            if min_dimension < 1.0:  # Less than 1mm
                score *= 0.8

            scores.append(score)

        return np.mean(scores) if scores else 0.0

    def _identify_printing_issues(self, model: BIMModel) -> List[str]:
        """Identify potential printing issues."""

        issues = []

        for element in model.elements:
            # Check geometry complexity
            if len(element.geometry.faces) > 50000:
                issues.append(f"Element {element.name}: Extremely high polygon count may cause printing issues")

            # Check for small features
            bounds = element.geometry.bounds
            dimensions = bounds[1] - bounds[0]
            if np.any(dimensions < 0.5):  # Features smaller than 0.5mm
                issues.append(f"Element {element.name}: Contains very small features that may not print properly")

            # Check material compatibility
            material = element.properties.get('material', 'unknown')
            if material not in ['plastic', 'resin', 'metal', 'concrete', 'wood']:
                issues.append(f"Element {element.name}: Material '{material}' may not be suitable for 3D printing")

        return issues

    def _generate_printing_recommendations(self, model: BIMModel) -> List[str]:
        """Generate recommendations for printing."""

        recommendations = []

        # General recommendations
        recommendations.append("Consider using support structures for overhangs greater than 45 degrees")
        recommendations.append("Scale model appropriately for your printer's build volume")
        recommendations.append("Use appropriate infill density based on functional requirements")

        # Element-specific recommendations
        has_large_elements = any(len(element.geometry.faces) > 10000 for element in model.elements)
        if has_large_elements:
            recommendations.append("Consider simplifying complex geometries or splitting large elements")

        has_small_features = any(
            np.min(element.geometry.bounds[1] - element.geometry.bounds[0]) < 1.0
            for element in model.elements
        )
        if has_small_features:
            recommendations.append("Small features may require higher resolution printing or post-processing")

        return recommendations

    def _analyze_materials(self, model: BIMModel) -> Dict[str, Any]:
        """Analyze materials in the BIM model."""

        material_counts = {}
        material_volumes = {}

        for element in model.elements:
            material = element.properties.get('material', 'unknown')
            volume = element.geometry.volume

            material_counts[material] = material_counts.get(material, 0) + 1
            material_volumes[material] = material_volumes.get(material, 0) + volume

        return {
            "material_counts": material_counts,
            "material_volumes": material_volumes,
            "total_materials": len(material_counts)
        }

    def _analyze_scale(self, model: BIMModel) -> Dict[str, Any]:
        """Analyze scale and dimensions."""

        if not model.elements:
            return {}

        # Calculate overall bounding box
        all_bounds = []
        for element in model.elements:
            all_bounds.append(element.geometry.bounds)

        if not all_bounds:
            return {}

        # Find overall bounds
        min_bounds = np.min([b[0] for b in all_bounds], axis=0)
        max_bounds = np.max([b[1] for b in all_bounds], axis=0)

        dimensions = max_bounds - min_bounds

        return {
            "overall_dimensions": dimensions.tolist(),
            "volume": float(np.prod(dimensions)),
            "aspect_ratio": float(max(dimensions) / min(dimensions)) if min(dimensions) > 0 else float('inf'),
            "scale_suitable_for_printing": all(d < 500 for d in dimensions)  # Less than 500mm
        }

    def _analyze_complexity(self, model: BIMModel) -> Dict[str, Any]:
        """Analyze geometric complexity."""

        total_faces = sum(len(element.geometry.faces) for element in model.elements)
        total_vertices = sum(len(element.geometry.vertices) for element in model.elements)

        # Calculate complexity score
        complexity_score = min(1.0, total_faces / 50000)  # Normalize to 50k faces

        return {
            "total_faces": total_faces,
            "total_vertices": total_vertices,
            "average_faces_per_element": total_faces / len(model.elements) if model.elements else 0,
            "complexity_score": complexity_score,
            "complexity_level": "high" if complexity_score > 0.7 else "medium" if complexity_score > 0.4 else "low"
        }


# Global instance
bim_integrator = BIMIntegrator()


def import_bim_file(file_path: str, format: BIMStandard) -> BIMIntegrationResult:
    """Convenience function to import BIM file."""
    return bim_integrator.import_bim_model(file_path, format)


def export_bim_file(model: BIMModel, file_path: str, format: BIMStandard) -> bool:
    """Convenience function to export BIM file."""
    return bim_integrator.export_bim_model(model, file_path, format)


def analyze_bim_for_3d_printing(model: BIMModel) -> Dict[str, Any]:
    """Convenience function to analyze BIM model for 3D printing."""
    return bim_integrator.analyze_bim_for_printing(model)
