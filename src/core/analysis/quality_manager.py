"""Quality management and industry standards compliance for 3D printing."""

from __future__ import annotations
from dataclasses import dataclass, field
from typing import List, Optional, Tuple, Dict, Any
from enum import Enum
import logging
import time
import numpy as np
import trimesh


class IndustryStandard(Enum):
    """Industry standards for compliance."""
    ISO_9001 = "ISO_9001"
    ISO_13485 = "ISO_13485"  # Medical devices
    ASTM_F2792 = "ASTM_F2792"  # Standard terminology for AM
    ASTM_F2971 = "ASTM_F2971"  # Standard practice for AM process
    ASTM_F3122 = "ASTM_F3122"  # Standard guide for AM file format
    ASME_Y14_46 = "ASME_Y14_46"  # Product definition for AM
    FDA_21_CFR = "FDA_21_CFR"  # FDA regulations
    CE_MARKING = "CE_Marking"
    UL_94 = "UL_94"  # Flammability of plastic materials


class QualityControlCheckpoint(Enum):
    """Quality control checkpoints."""
    DESIGN_VALIDATION = "design_validation"
    MATERIAL_VERIFICATION = "material_verification"
    PROCESS_VALIDATION = "process_validation"
    DIMENSIONAL_INSPECTION = "dimensional_inspection"
    MECHANICAL_TESTING = "mechanical_testing"
    SURFACE_FINISH_INSPECTION = "surface_finish_inspection"
    FINAL_ASSEMBLY_VERIFICATION = "final_assembly_verification"


@dataclass
class QualityStandard:
    """Quality standard specification."""
    name: IndustryStandard
    description: str
    requirements: Dict[str, Any]
    tolerance_limits: Dict[str, float]
    testing_procedures: List[str]
    documentation_required: List[str]
    certification_body: str


@dataclass
class QualityControlSettings:
    """Settings for quality management."""
    target_standards: List[IndustryStandard] = field(default_factory=lambda: [
        IndustryStandard.ASTM_F2792,
        IndustryStandard.ASTM_F3122
    ])
    quality_level: str = "enterprise"  # basic, standard, enterprise
    dimensional_tolerance_mm: float = 0.1
    surface_roughness_um: float = 25.0
    mechanical_testing_required: bool = True
    documentation_level: str = "comprehensive"
    audit_trail_enabled: bool = True
    statistical_process_control: bool = True


@dataclass
class QualityInspectionResult:
    """Result of quality inspection."""
    checkpoint: QualityControlCheckpoint
    passed: bool
    measurements: Dict[str, float]
    deviations: Dict[str, float]
    compliance_score: float  # 0-100
    issues_found: List[str]
    recommendations: List[str]
    timestamp: float


@dataclass
class ComplianceReport:
    """Compliance report for industry standards."""
    standard: IndustryStandard
    compliance_status: str  # compliant, non_compliant, partial
    compliance_score: float  # 0-100
    verified_checkpoints: List[QualityControlCheckpoint]
    missing_requirements: List[str]
    recommendations: List[str]
    certification_ready: bool
    next_audit_date: Optional[str]


@dataclass
class QualityManagementResult:
    """Overall quality management result."""
    success: bool
    inspection_results: List[QualityInspectionResult]
    compliance_reports: List[ComplianceReport]
    overall_quality_score: float  # 0-100
    standards_compliance: Dict[IndustryStandard, float]
    improvement_recommendations: List[str]
    certification_readiness: Dict[str, bool]
    processing_time: float


class QualityManager:
    """Quality management and standards compliance engine."""

    def __init__(self, settings: QualityControlSettings = None):
        """
        Initialize the quality manager.

        Args:
            settings: Quality control settings
        """
        self.settings = settings or QualityControlSettings()
        self.logger = logging.getLogger(__name__)
        self.standards_database = self._build_standards_database()

    def _build_standards_database(self) -> Dict[IndustryStandard, QualityStandard]:
        """Build database of quality standards."""
        standards = {}

        # ASTM F2792 - Standard Terminology for Additive Manufacturing
        astm_f2792 = QualityStandard(
            name=IndustryStandard.ASTM_F2792,
            description="Standard terminology for additive manufacturing technologies",
            requirements={
                "terminology_consistency": True,
                "process_documentation": True,
                "material_specification": True
            },
            tolerance_limits={
                "dimensional_accuracy": 0.1,
                "surface_roughness": 50.0,
                "mechanical_properties": 0.05  # 5% tolerance
            },
            testing_procedures=[
                "Dimensional measurement",
                "Surface profilometry",
                "Tensile testing",
                "Documentation review"
            ],
            documentation_required=[
                "Material certificates",
                "Process parameters",
                "Quality control records",
                "Final inspection reports"
            ],
            certification_body="ASTM International"
        )
        standards[IndustryStandard.ASTM_F2792] = astm_f2792

        # ASTM F3122 - Standard Guide for Additive Manufacturing File Format
        astm_f3122 = QualityStandard(
            name=IndustryStandard.ASTM_F3122,
            description="Standard guide for evaluation of additive manufacturing file format",
            requirements={
                "file_format_validation": True,
                "geometry_verification": True,
                "metadata_completeness": True
            },
            tolerance_limits={
                "file_integrity": 1.0,  # 100% integrity required
                "geometry_accuracy": 0.01,  # 0.01mm tolerance
                "metadata_completeness": 0.9  # 90% completeness
            },
            testing_procedures=[
                "File format validation",
                "Geometry analysis",
                "Metadata verification",
                "Integrity checking"
            ],
            documentation_required=[
                "File format specifications",
                "Validation reports",
                "Geometry analysis results"
            ],
            certification_body="ASTM International"
        )
        standards[IndustryStandard.ASTM_F3122] = astm_f3122

        # ISO 9001 - Quality Management Systems
        iso_9001 = QualityStandard(
            name=IndustryStandard.ISO_9001,
            description="Quality management systems requirements",
            requirements={
                "quality_policy": True,
                "process_approach": True,
                "continuous_improvement": True,
                "customer_satisfaction": True
            },
            tolerance_limits={
                "process_capability": 1.33,  # CpK minimum
                "customer_satisfaction": 80.0,  # Minimum score
                "defect_rate": 0.01  # Maximum 1% defects
            },
            testing_procedures=[
                "Process capability analysis",
                "Customer satisfaction surveys",
                "Defect tracking",
                "Management review"
            ],
            documentation_required=[
                "Quality manual",
                "Process procedures",
                "Work instructions",
                "Quality records"
            ],
            certification_body="ISO"
        )
        standards[IndustryStandard.ISO_9001] = iso_9001

        return standards

    def perform_quality_management(self, mesh: trimesh.Trimesh,
                                 print_settings: Dict[str, Any] = None,
                                 material_info: Dict[str, Any] = None) -> QualityManagementResult:
        """
        Perform comprehensive quality management and standards compliance.

        Args:
            mesh: Input mesh to validate
            print_settings: Print settings used
            material_info: Material information

        Returns:
            QualityManagementResult with comprehensive analysis
        """
        start_time = time.time()
        inspection_results = []
        compliance_reports = []

        try:
            # Step 1: Perform quality inspections
            for checkpoint in QualityControlCheckpoint:
                inspection = self._perform_quality_inspection(mesh, checkpoint, print_settings, material_info)
                inspection_results.append(inspection)

            # Step 2: Generate compliance reports
            for standard in self.settings.target_standards:
                if standard in self.standards_database:
                    report = self._generate_compliance_report(mesh, standard, inspection_results)
                    compliance_reports.append(report)

            # Step 3: Calculate overall quality score
            overall_score = self._calculate_overall_quality_score(inspection_results, compliance_reports)

            # Step 4: Generate standards compliance summary
            standards_compliance = {std: report.compliance_score for std, report in
                                  [(s.name, r) for s in self.settings.target_standards
                                   for r in compliance_reports if r.standard == s.name]}

            # Step 5: Generate improvement recommendations
            recommendations = self._generate_improvement_recommendations(inspection_results, compliance_reports)

            # Step 6: Assess certification readiness
            certification_readiness = self._assess_certification_readiness(compliance_reports)

            processing_time = time.time() - start_time

            return QualityManagementResult(
                success=True,
                inspection_results=inspection_results,
                compliance_reports=compliance_reports,
                overall_quality_score=overall_score,
                standards_compliance=standards_compliance,
                improvement_recommendations=recommendations,
                certification_readiness=certification_readiness,
                processing_time=processing_time
            )

        except Exception as e:
            self.logger.error(f"Quality management failed: {e}")
            processing_time = time.time() - start_time

            return QualityManagementResult(
                success=False,
                inspection_results=[],
                compliance_reports=[],
                overall_quality_score=0.0,
                standards_compliance={},
                improvement_recommendations=[f"Quality management failed: {str(e)}"],
                certification_readiness={},
                processing_time=processing_time
            )

    def _perform_quality_inspection(self, mesh: trimesh.Trimesh,
                                  checkpoint: QualityControlCheckpoint,
                                  print_settings: Dict[str, Any],
                                  material_info: Dict[str, Any]) -> QualityInspectionResult:
        """Perform quality inspection for a specific checkpoint."""
        timestamp = time.time()
        measurements = {}
        deviations = {}
        issues_found = []
        recommendations = []

        try:
            if checkpoint == QualityControlCheckpoint.DESIGN_VALIDATION:
                # Validate mesh design
                measurements['face_count'] = len(mesh.faces)
                measurements['vertex_count'] = len(mesh.vertices)
                measurements['is_watertight'] = 1.0 if mesh.is_watertight else 0.0
                measurements['is_manifold'] = 1.0 if mesh.is_winding_consistent else 0.0

                deviations['watertight_deviation'] = 0.0 if mesh.is_watertight else 1.0
                deviations['manifold_deviation'] = 0.0 if mesh.is_winding_consistent else 1.0

                if not mesh.is_watertight:
                    issues_found.append("Mesh is not watertight")
                    recommendations.append("Apply mesh repair operations")
                if not mesh.is_winding_consistent:
                    issues_found.append("Mesh winding is inconsistent")
                    recommendations.append("Fix face normals")

            elif checkpoint == QualityControlCheckpoint.MATERIAL_VERIFICATION:
                # Verify material properties
                if material_info:
                    measurements['material_density'] = material_info.get('density', 1.24)
                    measurements['tensile_strength'] = material_info.get('tensile_strength', 50.0)

                    required_density = self.settings.dimensional_tolerance_mm
                    if abs(measurements['material_density'] - 1.24) > 0.1:  # 10% tolerance
                        deviations['density_deviation'] = abs(measurements['material_density'] - 1.24)
                        issues_found.append("Material density outside acceptable range")
                        recommendations.append("Verify material specifications")

            elif checkpoint == QualityControlCheckpoint.DIMENSIONAL_INSPECTION:
                # Perform dimensional inspection
                measurements['bounding_box_x'] = mesh.extents[0]
                measurements['bounding_box_y'] = mesh.extents[1]
                measurements['bounding_box_z'] = mesh.extents[2]
                measurements['volume'] = mesh.volume if mesh.volume > 0 else 1000.0

                # Check dimensional tolerances
                tolerance = self.settings.dimensional_tolerance_mm
                for i, extent in enumerate(mesh.extents):
                    if extent > 300.0:  # Large dimension check
                        deviations[f'dimension_{i}_deviation'] = extent - 300.0
                        issues_found.append(f"Dimension {i} exceeds printer limits")
                        recommendations.append("Consider part orientation or splitting")

            elif checkpoint == QualityControlCheckpoint.SURFACE_FINISH_INSPECTION:
                # Analyze surface finish
                measurements['surface_area'] = mesh.area
                measurements['avg_edge_length'] = np.mean([np.linalg.norm(mesh.vertices[edge[1]] - mesh.vertices[edge[0]])
                                                        for edge in mesh.edges_unique])

                # Estimate surface roughness (simplified)
                estimated_roughness = 25.0 + (measurements['avg_edge_length'] * 10)
                measurements['estimated_roughness'] = estimated_roughness

                if estimated_roughness > self.settings.surface_roughness_um:
                    deviations['roughness_deviation'] = estimated_roughness - self.settings.surface_roughness_um
                    issues_found.append("Surface roughness exceeds requirements")
                    recommendations.append("Apply surface smoothing or adjust print settings")

            # Calculate compliance score
            compliance_score = self._calculate_checkpoint_score(measurements, deviations)

        except Exception as e:
            self.logger.warning(f"Quality inspection failed for {checkpoint}: {e}")
            compliance_score = 50.0
            issues_found.append(f"Inspection failed: {str(e)}")

        return QualityInspectionResult(
            checkpoint=checkpoint,
            passed=compliance_score >= 80.0,  # 80% threshold for passing
            measurements=measurements,
            deviations=deviations,
            compliance_score=compliance_score,
            issues_found=issues_found,
            recommendations=recommendations,
            timestamp=timestamp
        )

    def _calculate_checkpoint_score(self, measurements: Dict[str, float],
                                  deviations: Dict[str, float]) -> float:
        """Calculate compliance score for a checkpoint."""
        try:
            # Base score
            score = 100.0

            # Penalize deviations
            total_deviation_penalty = sum(deviations.values()) * 5.0
            score -= total_deviation_penalty

            # Bonus for good measurements
            good_measurements = sum(1 for v in measurements.values() if v > 0)
            measurement_bonus = (good_measurements / len(measurements)) * 10.0
            score += measurement_bonus

            return max(0.0, min(100.0, score))

        except:
            return 50.0

    def _generate_compliance_report(self, mesh: trimesh.Trimesh,
                                  standard: IndustryStandard,
                                  inspection_results: List[QualityInspectionResult]) -> ComplianceReport:
        """Generate compliance report for a specific standard."""
        try:
            standard_spec = self.standards_database[standard]

            # Find relevant inspection results
            relevant_checkpoints = []
            for result in inspection_results:
                if self._is_checkpoint_relevant_for_standard(result.checkpoint, standard):
                    relevant_checkpoints.append(result.checkpoint)

            # Calculate compliance score
            compliance_score = np.mean([r.compliance_score for r in inspection_results
                                       if r.checkpoint in relevant_checkpoints])

            # Determine compliance status
            if compliance_score >= 90.0:
                status = "compliant"
            elif compliance_score >= 70.0:
                status = "partial"
            else:
                status = "non_compliant"

            # Check missing requirements
            missing_requirements = self._check_missing_requirements(standard, mesh, inspection_results)

            # Generate recommendations
            recommendations = self._generate_standard_recommendations(standard, compliance_score)

            # Assess certification readiness
            certification_ready = status == "compliant" and len(missing_requirements) == 0

            return ComplianceReport(
                standard=standard,
                compliance_status=status,
                compliance_score=compliance_score,
                verified_checkpoints=relevant_checkpoints,
                missing_requirements=missing_requirements,
                recommendations=recommendations,
                certification_ready=certification_ready,
                next_audit_date=self._calculate_next_audit_date(certification_ready)
            )

        except Exception as e:
            self.logger.warning(f"Compliance report generation failed for {standard}: {e}")
            return ComplianceReport(
                standard=standard,
                compliance_status="unknown",
                compliance_score=0.0,
                verified_checkpoints=[],
                missing_requirements=["Report generation failed"],
                recommendations=[],
                certification_ready=False,
                next_audit_date=None
            )

    def _is_checkpoint_relevant_for_standard(self, checkpoint: QualityControlCheckpoint,
                                           standard: IndustryStandard) -> bool:
        """Check if checkpoint is relevant for the standard."""
        # Define relevance mapping
        relevance_map = {
            IndustryStandard.ASTM_F2792: [
                QualityControlCheckpoint.DESIGN_VALIDATION,
                QualityControlCheckpoint.MATERIAL_VERIFICATION,
                QualityControlCheckpoint.DIMENSIONAL_INSPECTION
            ],
            IndustryStandard.ASTM_F3122: [
                QualityControlCheckpoint.DESIGN_VALIDATION,
                QualityControlCheckpoint.PROCESS_VALIDATION
            ],
            IndustryStandard.ISO_9001: [
                QualityControlCheckpoint.PROCESS_VALIDATION,
                QualityControlCheckpoint.MECHANICAL_TESTING,
                QualityControlCheckpoint.FINAL_ASSEMBLY_VERIFICATION
            ]
        }

        return checkpoint in relevance_map.get(standard, [])

    def _check_missing_requirements(self, standard: IndustryStandard,
                                  mesh: trimesh.Trimesh,
                                  inspection_results: List[QualityInspectionResult]) -> List[str]:
        """Check for missing requirements for the standard."""
        missing = []
        standard_spec = self.standards_database[standard]

        # Check if all required checkpoints were performed
        required_checkpoints = self._get_required_checkpoints_for_standard(standard)
        performed_checkpoints = {r.checkpoint for r in inspection_results}

        for checkpoint in required_checkpoints:
            if checkpoint not in performed_checkpoints:
                missing.append(f"Missing inspection: {checkpoint.value}")

        # Check documentation requirements
        for doc in standard_spec.documentation_required:
            if not self._has_documentation(doc):
                missing.append(f"Missing documentation: {doc}")

        return missing

    def _get_required_checkpoints_for_standard(self, standard: IndustryStandard) -> List[QualityControlCheckpoint]:
        """Get required checkpoints for a standard."""
        requirements_map = {
            IndustryStandard.ASTM_F2792: [
                QualityControlCheckpoint.DESIGN_VALIDATION,
                QualityControlCheckpoint.DIMENSIONAL_INSPECTION
            ],
            IndustryStandard.ASTM_F3122: [
                QualityControlCheckpoint.DESIGN_VALIDATION
            ],
            IndustryStandard.ISO_9001: [
                QualityControlCheckpoint.PROCESS_VALIDATION,
                QualityControlCheckpoint.FINAL_ASSEMBLY_VERIFICATION
            ]
        }

        return requirements_map.get(standard, [])

    def _has_documentation(self, doc_type: str) -> bool:
        """Check if required documentation exists."""
        # Simplified check - in practice, this would verify actual files
        return True  # Assume documentation exists for now

    def _generate_standard_recommendations(self, standard: IndustryStandard,
                                         compliance_score: float) -> List[str]:
        """Generate recommendations for standard compliance."""
        recommendations = []

        if compliance_score < 70.0:
            recommendations.append("Implement comprehensive quality management system")
            recommendations.append("Conduct additional testing and validation")
        elif compliance_score < 90.0:
            recommendations.append("Improve process documentation")
            recommendations.append("Enhance quality control procedures")
        else:
            recommendations.append("Maintain current quality standards")
            recommendations.append("Prepare for certification audit")

        return recommendations

    def _calculate_next_audit_date(self, certification_ready: bool) -> Optional[str]:
        """Calculate next audit date."""
        if certification_ready:
            # Annual audit for certified systems
            next_audit = time.time() + (365 * 24 * 3600)
            return time.strftime("%Y-%m-%d", time.localtime(next_audit))
        else:
            # Quarterly review for non-certified systems
            next_review = time.time() + (90 * 24 * 3600)
            return time.strftime("%Y-%m-%d", time.localtime(next_review))

    def _calculate_overall_quality_score(self, inspection_results: List[QualityInspectionResult],
                                       compliance_reports: List[ComplianceReport]) -> float:
        """Calculate overall quality score."""
        try:
            # Average of inspection scores
            inspection_avg = np.mean([r.compliance_score for r in inspection_results])

            # Average of compliance scores
            compliance_avg = np.mean([r.compliance_score for r in compliance_reports])

            # Weighted average
            overall_score = (inspection_avg * 0.6) + (compliance_avg * 0.4)

            return min(100.0, overall_score)

        except:
            return 50.0

    def _generate_improvement_recommendations(self, inspection_results: List[QualityInspectionResult],
                                            compliance_reports: List[ComplianceReport]) -> List[str]:
        """Generate improvement recommendations."""
        recommendations = []

        # Analyze failed inspections
        failed_inspections = [r for r in inspection_results if not r.passed]

        for inspection in failed_inspections:
            recommendations.extend(inspection.recommendations)

        # Analyze partial compliance
        partial_compliance = [r for r in compliance_reports if r.compliance_status == "partial"]

        for report in partial_compliance:
            recommendations.extend(report.recommendations)

        # Remove duplicates
        recommendations = list(set(recommendations))

        return recommendations

    def _assess_certification_readiness(self, compliance_reports: List[ComplianceReport]) -> Dict[str, bool]:
        """Assess readiness for certification."""
        readiness = {}

        for report in compliance_reports:
            readiness[report.standard.value] = report.certification_ready

        return readiness


def perform_quality_management(mesh: trimesh.Trimesh,
                             target_standards: List[IndustryStandard] = None,
                             quality_level: str = "enterprise",
                             print_settings: Dict[str, Any] = None,
                             material_info: Dict[str, Any] = None,
                             settings: QualityControlSettings = None) -> QualityManagementResult:
    """
    Convenience function for quality management and standards compliance.

    Args:
        mesh: Input mesh to validate
        target_standards: Target industry standards
        quality_level: Quality level (basic, standard, enterprise)
        print_settings: Print settings used
        material_info: Material information
        settings: Optional quality control settings

    Returns:
        QualityManagementResult with comprehensive analysis
    """
    if settings is None:
        settings = QualityControlSettings(quality_level=quality_level)
        if target_standards:
            settings.target_standards = target_standards
    else:
        settings.quality_level = quality_level
        if target_standards:
            settings.target_standards = target_standards

    manager = QualityManager(settings)
    return manager.perform_quality_management(mesh, print_settings, material_info)
