"""Rule-based defeaturing system for automatic model simplification."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import List, Optional, Tuple, Dict, Any, Set
import numpy as np
import trimesh
from enum import Enum
import logging
import time


class DefeaturingRule(Enum):
    """Types of defeaturing rules."""
    SMALL_FEATURE_REMOVAL = "small_feature_removal"
    HOLE_FILLING = "hole_filling"
    FILLET_SIMPLIFICATION = "fillet_simplification"
    TEXTURE_REMOVAL = "texture_removal"
    INTERNAL_STRUCTURE_REMOVAL = "internal_structure_removal"
    THIN_WALL_MERGING = "thin_wall_merging"
    PATTERN_SIMPLIFICATION = "pattern_simplification"
    TOLERANCE_BASED_SIMPLIFICATION = "tolerance_based_simplification"


class DefeaturingPriority(Enum):
    """Priority levels for defeaturing operations."""
    CRITICAL = "critical"  # Must be removed for manufacturing
    HIGH = "high"        # Important for quality/speed
    MEDIUM = "medium"    # Nice to have
    LOW = "low"         # Optional


@dataclass
class DefeaturingRuleConfig:
    """Configuration for a single defeaturing rule."""

    rule_type: DefeaturingRule
    enabled: bool = True
    priority: DefeaturingPriority = DefeaturingPriority.MEDIUM
    threshold: float = 0.1  # Size threshold in mm
    tolerance: float = 0.01  # Geometric tolerance
    preserve_functionality: bool = True  # Don't remove functional features
    custom_parameters: Dict[str, Any] = field(default_factory=dict)


@dataclass
class DefeaturingResult:
    """Result of defeaturing operation."""

    original_mesh: trimesh.Trimesh
    simplified_mesh: trimesh.Trimesh
    removed_features: List[Dict[str, Any]] = field(default_factory=list)
    applied_rules: List[DefeaturingRule] = field(default_factory=list)
    simplification_ratio: float = 1.0
    processing_time: float = 0.0
    quality_metrics: Dict[str, Any] = field(default_factory=dict)


@dataclass
class FeatureCandidate:
    """A candidate feature for removal/modification."""

    feature_type: str
    location: np.ndarray
    size: float
    importance_score: float
    rule: DefeaturingRule
    metadata: Dict[str, Any] = field(default_factory=dict)


class RuleBasedDefeaturing:
    """Rule-based model defeaturing system."""

    def __init__(self):
        self.rules: Dict[DefeaturingRule, DefeaturingRuleConfig] = {}
        self.logger = logging.getLogger(__name__)
        self._initialize_default_rules()

    def _initialize_default_rules(self):
        """Initialize default defeaturing rules."""

        # Small feature removal
        self.rules[DefeaturingRule.SMALL_FEATURE_REMOVAL] = DefeaturingRuleConfig(
            rule_type=DefeaturingRule.SMALL_FEATURE_REMOVAL,
            enabled=True,
            priority=DefeaturingPriority.HIGH,
            threshold=0.5,  # Remove features smaller than 0.5mm
            preserve_functionality=True
        )

        # Hole filling
        self.rules[DefeaturingRule.HOLE_FILLING] = DefeaturingRuleConfig(
            rule_type=DefeaturingRule.HOLE_FILLING,
            enabled=True,
            priority=DefeaturingPriority.MEDIUM,
            threshold=1.0,  # Fill holes smaller than 1mm
            preserve_functionality=False
        )

        # Fillet simplification
        self.rules[DefeaturingRule.FILLET_SIMPLIFICATION] = DefeaturingRuleConfig(
            rule_type=DefeaturingRule.FILLET_SIMPLIFICATION,
            enabled=True,
            priority=DefeaturingPriority.LOW,
            threshold=0.2,  # Simplify fillets smaller than 0.2mm
            preserve_functionality=True
        )

        # Texture removal
        self.rules[DefeaturingRule.TEXTURE_REMOVAL] = DefeaturingRuleConfig(
            rule_type=DefeaturingRule.TEXTURE_REMOVAL,
            enabled=True,
            priority=DefeaturingPriority.MEDIUM,
            threshold=0.1,  # Remove textures smaller than 0.1mm
            preserve_functionality=False
        )

        # Internal structure removal
        self.rules[DefeaturingRule.INTERNAL_STRUCTURE_REMOVAL] = DefeaturingRuleConfig(
            rule_type=DefeaturingRule.INTERNAL_STRUCTURE_REMOVAL,
            enabled=False,  # Disabled by default for safety
            priority=DefeaturingPriority.CRITICAL,
            threshold=2.0,
            preserve_functionality=True
        )

        # Thin wall merging
        self.rules[DefeaturingRule.THIN_WALL_MERGING] = DefeaturingRuleConfig(
            rule_type=DefeaturingRule.THIN_WALL_MERGING,
            enabled=True,
            priority=DefeaturingPriority.HIGH,
            threshold=0.3,  # Merge walls thinner than 0.3mm
            preserve_functionality=True
        )

    def add_rule(self, config: DefeaturingRuleConfig):
        """Add or update a defeaturing rule."""
        self.rules[config.rule_type] = config

    def remove_rule(self, rule_type: DefeaturingRule):
        """Remove a defeaturing rule."""
        if rule_type in self.rules:
            del self.rules[rule_type]

    def defeaturing(self, mesh: trimesh.Trimesh,
                   rules_to_apply: Optional[List[DefeaturingRule]] = None) -> DefeaturingResult:
        """Apply rule-based defeaturing to a mesh."""

        start_time = time.time()
        result = DefeaturingResult(
            original_mesh=mesh.copy(),
            simplified_mesh=mesh.copy()
        )

        # Determine which rules to apply
        if rules_to_apply is None:
            rules_to_apply = [rule for rule, config in self.rules.items() if config.enabled]

        # Sort rules by priority
        rules_to_apply.sort(key=lambda r: self.rules[r].priority.value, reverse=True)

        # Find candidate features
        candidates = self._find_feature_candidates(mesh)

        # Apply rules in priority order
        for rule in rules_to_apply:
            if rule not in self.rules:
                continue

            config = self.rules[rule]
            applicable_candidates = [
                c for c in candidates
                if c.rule == rule and c.size < config.threshold
            ]

            if applicable_candidates:
                self.logger.info(f"Applying rule {rule.value} to {len(applicable_candidates)} features")

                # Apply the rule
                modified_mesh, removed = self._apply_rule(result.simplified_mesh, rule, applicable_candidates, config)

                if modified_mesh is not None:
                    result.simplified_mesh = modified_mesh
                    result.removed_features.extend(removed)
                    result.applied_rules.append(rule)

        # Calculate metrics
        result.processing_time = time.time() - start_time
        result.simplification_ratio = self._calculate_simplification_ratio(result.original_mesh, result.simplified_mesh)
        result.quality_metrics = self._calculate_quality_metrics(result)

        return result

    def _find_feature_candidates(self, mesh: trimesh.Trimesh) -> List[FeatureCandidate]:
        """Find candidate features for defeaturing."""

        candidates = []

        try:
            # Analyze mesh topology
            if hasattr(mesh, 'face_adjacency'):
                # Find small faces (potential small features)
                face_areas = mesh.area_faces
                small_faces = np.where(face_areas < 0.1)[0]  # Faces smaller than 0.1 mm²

                for face_idx in small_faces:
                    centroid = mesh.triangles_center[face_idx]
                    candidates.append(FeatureCandidate(
                        feature_type="small_face",
                        location=centroid,
                        size=float(face_areas[face_idx]),
                        importance_score=self._calculate_feature_importance(mesh, face_idx),
                        rule=DefeaturingRule.SMALL_FEATURE_REMOVAL,
                        metadata={"face_index": int(face_idx)}
                    ))

            # Find holes
            if hasattr(mesh, 'identifier') and mesh.is_watertight:
                # This is a simplified hole detection
                # In practice, you'd use more sophisticated algorithms
                pass

            # Find thin walls
            # This would require ray casting or section analysis
            thin_wall_candidates = self._find_thin_walls(mesh)
            candidates.extend(thin_wall_candidates)

            # Find fillets/rounds (simplified detection)
            fillet_candidates = self._find_fillets(mesh)
            candidates.extend(fillet_candidates)

        except Exception as e:
            self.logger.warning(f"Error finding feature candidates: {e}")

        return candidates

    def _find_thin_walls(self, mesh: trimesh.Trimesh) -> List[FeatureCandidate]:
        """Find thin wall candidates."""
        candidates = []

        try:
            # Simplified thin wall detection using ray casting
            bounds = mesh.bounds
            center = (bounds[0] + bounds[1]) / 2

            # Cast rays in cardinal directions
            directions = [
                np.array([1, 0, 0]), np.array([-1, 0, 0]),
                np.array([0, 1, 0]), np.array([0, -1, 0]),
                np.array([0, 0, 1]), np.array([0, 0, -1])
            ]

            for direction in directions:
                try:
                    # Find intersections
                    locations, _, _ = mesh.ray.intersects_location(
                        ray_origins=[center],
                        ray_directions=[direction],
                        multiple_hits=True
                    )

                    if len(locations) >= 2:
                        # Calculate wall thickness
                        distances = np.linalg.norm(locations - center, axis=1)
                        thickness = abs(distances[-1] - distances[0])

                        if thickness < 0.5:  # Thin wall threshold
                            candidates.append(FeatureCandidate(
                                feature_type="thin_wall",
                                location=center,
                                size=float(thickness),
                                importance_score=0.7,  # Medium importance
                                rule=DefeaturingRule.THIN_WALL_MERGING,
                                metadata={"direction": direction.tolist()}
                            ))

                except Exception:
                    continue

        except Exception as e:
            self.logger.warning(f"Error finding thin walls: {e}")

        return candidates

    def _find_fillets(self, mesh: trimesh.Trimesh) -> List[FeatureCandidate]:
        """Find fillet/round candidates."""
        candidates = []

        try:
            # Simplified fillet detection based on edge angles
            if hasattr(mesh, 'face_adjacency_angles'):
                angles = np.degrees(mesh.face_adjacency_angles)
                # Look for edges with angles suggesting fillets (typically 90-135 degrees)
                fillet_mask = (angles > 80) & (angles < 140)

                if np.any(fillet_mask):
                    adjacency = mesh.face_adjacency[fillet_mask]
                    for face_pair in adjacency:
                        # Calculate edge midpoint
                        edge_vertices = np.intersect1d(
                            mesh.faces[face_pair[0]],
                            mesh.faces[face_pair[1]]
                        )
                        if len(edge_vertices) >= 2:
                            midpoint = np.mean(mesh.vertices[edge_vertices], axis=0)
                            candidates.append(FeatureCandidate(
                                feature_type="fillet",
                                location=midpoint,
                                size=0.1,  # Assume small fillet
                                importance_score=0.3,  # Low importance
                                rule=DefeaturingRule.FILLET_SIMPLIFICATION
                            ))

        except Exception as e:
            self.logger.warning(f"Error finding fillets: {e}")

        return candidates

    def _calculate_feature_importance(self, mesh: trimesh.Trimesh, face_index: int) -> float:
        """Calculate importance score for a feature."""
        try:
            # Simple importance calculation based on position and connectivity
            centroid = mesh.triangles_center[face_index]

            # Features near the center are more important
            bounds = mesh.bounds
            center = (bounds[0] + bounds[1]) / 2
            distance_from_center = np.linalg.norm(centroid - center)

            # Normalize distance
            max_distance = np.linalg.norm(bounds[1] - bounds[0]) / 2
            distance_score = 1.0 - (distance_from_center / max_distance)

            # Features connected to many other faces are more important
            connected_faces = np.sum(mesh.face_adjacency == face_index)
            connectivity_score = min(1.0, connected_faces / 10.0)

            return (distance_score + connectivity_score) / 2.0

        except Exception:
            return 0.5  # Default medium importance

    def _apply_rule(self, mesh: trimesh.Trimesh, rule: DefeaturingRule,
                   candidates: List[FeatureCandidate], config: DefeaturingRuleConfig) -> Tuple[Optional[trimesh.Trimesh], List[Dict[str, Any]]]:
        """Apply a specific defeaturing rule."""

        try:
            if rule == DefeaturingRule.SMALL_FEATURE_REMOVAL:
                return self._apply_small_feature_removal(mesh, candidates, config)
            elif rule == DefeaturingRule.HOLE_FILLING:
                return self._apply_hole_filling(mesh, candidates, config)
            elif rule == DefeaturingRule.THIN_WALL_MERGING:
                return self._apply_thin_wall_merging(mesh, candidates, config)
            elif rule == DefeaturingRule.FILLET_SIMPLIFICATION:
                return self._apply_fillet_simplification(mesh, candidates, config)
            elif rule == DefeaturingRule.TEXTURE_REMOVAL:
                return self._apply_texture_removal(mesh, candidates, config)
            else:
                self.logger.warning(f"Rule {rule.value} not implemented yet")
                return mesh, []

        except Exception as e:
            self.logger.error(f"Error applying rule {rule.value}: {e}")
            return None, []

    def _apply_small_feature_removal(self, mesh: trimesh.Trimesh,
                                   candidates: List[FeatureCandidate],
                                   config: DefeaturingRuleConfig) -> Tuple[trimesh.Trimesh, List[Dict[str, Any]]]:
        """Remove small features from mesh."""

        removed_features = []
        faces_to_remove = set()

        for candidate in candidates:
            if candidate.feature_type == "small_face" and "face_index" in candidate.metadata:
                face_idx = candidate.metadata["face_index"]
                if config.preserve_functionality and candidate.importance_score > 0.7:
                    continue  # Skip important features

                faces_to_remove.add(face_idx)
                removed_features.append({
                    "type": "small_face",
                    "location": candidate.location.tolist(),
                    "size": candidate.size,
                    "importance": candidate.importance_score
                })

        if faces_to_remove:
            # Remove faces (this is a simplified approach)
            keep_faces = [i for i in range(len(mesh.faces)) if i not in faces_to_remove]
            simplified_mesh = mesh.submesh([keep_faces], only_watertight=False)
            return simplified_mesh, removed_features

        return mesh, removed_features

    def _apply_hole_filling(self, mesh: trimesh.Trimesh,
                          candidates: List[FeatureCandidate],
                          config: DefeaturingRuleConfig) -> Tuple[trimesh.Trimesh, List[Dict[str, Any]]]:
        """Fill small holes in mesh."""

        # This is a simplified implementation
        # Real hole filling would require more sophisticated algorithms
        if mesh.is_watertight:
            return mesh, []  # No holes to fill

        try:
            # Use trimesh's fill_holes method if available
            filled_mesh = mesh.fill_holes()
            return filled_mesh, [{"type": "hole_filling", "count": 1}]
        except Exception:
            return mesh, []

    def _apply_thin_wall_merging(self, mesh: trimesh.Trimesh,
                               candidates: List[FeatureCandidate],
                               config: DefeaturingRuleConfig) -> Tuple[trimesh.Trimesh, List[Dict[str, Any]]]:
        """Merge thin walls."""

        # This is a complex operation requiring advanced mesh processing
        # For now, return the mesh unchanged
        self.logger.info("Thin wall merging not fully implemented yet")
        return mesh, []

    def _apply_fillet_simplification(self, mesh: trimesh.Trimesh,
                                   candidates: List[FeatureCandidate],
                                   config: DefeaturingRuleConfig) -> Tuple[trimesh.Trimesh, List[Dict[str, Any]]]:
        """Simplify fillets."""

        # This is a complex operation
        # For now, return the mesh unchanged
        self.logger.info("Fillet simplification not fully implemented yet")
        return mesh, []

    def _apply_texture_removal(self, mesh: trimesh.Trimesh,
                             candidates: List[FeatureCandidate],
                             config: DefeaturingRuleConfig) -> Tuple[trimesh.Trimesh, List[Dict[str, Any]]]:
        """Remove surface textures."""

        # This would require surface analysis and smoothing
        # For now, return the mesh unchanged
        self.logger.info("Texture removal not fully implemented yet")
        return mesh, []

    def _calculate_simplification_ratio(self, original: trimesh.Trimesh,
                                      simplified: trimesh.Trimesh) -> float:
        """Calculate simplification ratio."""
        try:
            original_faces = len(original.faces)
            simplified_faces = len(simplified.faces)

            if original_faces == 0:
                return 1.0

            return simplified_faces / original_faces
        except Exception:
            return 1.0

    def _calculate_quality_metrics(self, result: DefeaturingResult) -> Dict[str, Any]:
        """Calculate quality metrics for defeaturing result."""

        metrics = {}

        try:
            original = result.original_mesh
            simplified = result.simplified_mesh

            # Basic metrics
            metrics["original_face_count"] = len(original.faces)
            metrics["simplified_face_count"] = len(simplified.faces)
            metrics["face_reduction"] = len(original.faces) - len(simplified.faces)
            metrics["volume_preservation"] = simplified.volume / original.volume if original.volume > 0 else 1.0
            metrics["surface_area_change"] = simplified.area / original.area if original.area > 0 else 1.0

            # Quality scores
            metrics["manifold_preservation"] = simplified.is_watertight == original.is_watertight
            metrics["watertight_preservation"] = simplified.is_watertight

        except Exception as e:
            self.logger.warning(f"Error calculating quality metrics: {e}")

        return metrics


# Global instance
rule_based_defeaturing = RuleBasedDefeaturing()


def apply_rule_based_defeaturing(mesh: trimesh.Trimesh,
                               rules: Optional[List[DefeaturingRule]] = None) -> DefeaturingResult:
    """Convenience function for rule-based defeaturing."""
    return rule_based_defeaturing.defeaturing(mesh, rules)
