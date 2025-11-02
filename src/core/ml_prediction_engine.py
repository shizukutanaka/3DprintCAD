"""Advanced machine learning features for predictive analytics and optimization."""

import numpy as np
import pandas as pd
import time
import logging
from typing import Dict, List, Any, Optional, Tuple, Callable, Union
from dataclasses import dataclass, field
from enum import Enum
import json
from pathlib import Path
import threading


class PredictionModel(Enum):
    """Types of prediction models."""
    PRINT_SUCCESS = "print_success"
    MATERIAL_USAGE = "material_usage"
    PRINT_TIME = "print_time"
    QUALITY_SCORE = "quality_score"
    MAINTENANCE_NEED = "maintenance_need"
    COST_ESTIMATION = "cost_estimation"


@dataclass
class TrainingData:
    """Training data for machine learning models."""
    features: np.ndarray
    targets: np.ndarray
    feature_names: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class PredictionResult:
    """Result of a prediction."""
    model_type: PredictionModel
    prediction: float
    confidence: float
    feature_importance: Dict[str, float] = field(default_factory=dict)
    explanation: str = ""
    timestamp: float = field(default_factory=time.time)


class FeatureExtractor:
    """Extracts features from 3D printing data for machine learning."""

    def __init__(self):
        """Initialize feature extractor."""
        self.logger = logging.getLogger(__name__)

    def extract_mesh_features(self, mesh_data: Dict[str, Any]) -> Dict[str, float]:
        """Extract features from mesh data.

        Args:
            mesh_data: Dictionary containing mesh information

        Returns:
            Dictionary of extracted features
        """
        features = {}

        try:
            # Basic mesh properties
            if 'vertices' in mesh_data:
                vertices = np.array(mesh_data['vertices'])
                features['vertex_count'] = len(vertices)
                features['bounding_box_volume'] = self._calculate_bounding_box_volume(vertices)
                features['surface_area'] = self._calculate_surface_area(mesh_data)
                features['mesh_complexity'] = self._calculate_mesh_complexity(vertices)

            # STL/OBJ specific features
            if 'file_size' in mesh_data:
                features['file_size_mb'] = mesh_data['file_size'] / (1024 * 1024)

            if 'triangle_count' in mesh_data:
                features['triangle_count'] = mesh_data['triangle_count']

            # Material features if available
            if 'material' in mesh_data:
                material = mesh_data['material']
                features['material_density'] = self._get_material_density(material)
                features['material_strength'] = self._get_material_strength(material)

        except Exception as e:
            self.logger.error(f"Error extracting mesh features: {e}")

        return features

    def extract_printer_features(self, printer_data: Dict[str, Any]) -> Dict[str, float]:
        """Extract features from printer data.

        Args:
            printer_data: Dictionary containing printer information

        Returns:
            Dictionary of extracted features
        """
        features = {}

        try:
            # Printer specifications
            features['printer_volume_x'] = printer_data.get('build_volume_x', 200)
            features['printer_volume_y'] = printer_data.get('build_volume_y', 200)
            features['printer_volume_z'] = printer_data.get('build_volume_z', 200)
            features['nozzle_diameter'] = printer_data.get('nozzle_diameter', 0.4)
            features['max_temperature'] = printer_data.get('max_temperature', 300)

            # Printer condition
            features['printer_age_days'] = self._calculate_printer_age(printer_data)
            features['maintenance_score'] = printer_data.get('maintenance_score', 100)
            features['calibration_score'] = printer_data.get('calibration_score', 100)

        except Exception as e:
            self.logger.error(f"Error extracting printer features: {e}")

        return features

    def extract_environmental_features(self, env_data: Dict[str, Any]) -> Dict[str, float]:
        """Extract environmental features.

        Args:
            env_data: Dictionary containing environmental data

        Returns:
            Dictionary of extracted features
        """
        features = {}

        try:
            features['temperature'] = env_data.get('temperature', 25.0)
            features['humidity'] = env_data.get('humidity', 50.0)
            features['air_quality'] = env_data.get('air_quality', 100)
            features['vibration_level'] = env_data.get('vibration_level', 0.0)

        except Exception as e:
            self.logger.error(f"Error extracting environmental features: {e}")

        return features

    def _calculate_bounding_box_volume(self, vertices: np.ndarray) -> float:
        """Calculate bounding box volume."""
        if len(vertices) == 0:
            return 0.0

        min_coords = np.min(vertices, axis=0)
        max_coords = np.max(vertices, axis=0)
        dimensions = max_coords - min_coords

        return float(np.prod(dimensions))

    def _calculate_surface_area(self, mesh_data: Dict[str, Any]) -> float:
        """Calculate approximate surface area."""
        # Simplified calculation based on triangle count
        triangle_count = mesh_data.get('triangle_count', 0)
        avg_triangle_area = mesh_data.get('avg_triangle_area', 1.0)

        return float(triangle_count * avg_triangle_area)

    def _calculate_mesh_complexity(self, vertices: np.ndarray) -> float:
        """Calculate mesh complexity score."""
        if len(vertices) < 4:
            return 0.0

        # Calculate average distance from centroid
        centroid = np.mean(vertices, axis=0)
        distances = np.linalg.norm(vertices - centroid, axis=1)
        avg_distance = np.mean(distances)

        # Normalize by bounding box diagonal
        min_coords = np.min(vertices, axis=0)
        max_coords = np.max(vertices, axis=0)
        diagonal = np.linalg.norm(max_coords - min_coords)

        return float(avg_distance / diagonal) if diagonal > 0 else 0.0

    def _get_material_density(self, material: str) -> float:
        """Get material density."""
        densities = {
            'PLA': 1.24, 'ABS': 1.04, 'PETG': 1.27, 'TPU': 1.20,
            'ASA': 1.07, 'PC': 1.20, 'NYLON': 1.14, 'WOOD': 1.30
        }
        return densities.get(material.upper(), 1.20)

    def _get_material_strength(self, material: str) -> float:
        """Get material strength."""
        strengths = {
            'PLA': 60, 'ABS': 45, 'PETG': 50, 'TPU': 35,
            'ASA': 55, 'PC': 70, 'NYLON': 65, 'WOOD': 40
        }
        return strengths.get(material.upper(), 50)

    def _calculate_printer_age(self, printer_data: Dict[str, Any]) -> float:
        """Calculate printer age in days."""
        purchase_date = printer_data.get('purchase_date')
        if purchase_date:
            try:
                from datetime import datetime
                purchase = datetime.fromisoformat(purchase_date.replace('Z', '+00:00'))
                age = datetime.now() - purchase
                return age.days
            except:
                pass
        return 365  # Default to 1 year


class PredictiveModel:
    """Base class for predictive models."""

    def __init__(self, model_type: PredictionModel, feature_extractor: FeatureExtractor):
        """Initialize predictive model.

        Args:
            model_type: Type of prediction model
            feature_extractor: Feature extractor instance
        """
        self.logger = logging.getLogger(__name__)
        self.model_type = model_type
        self.feature_extractor = feature_extractor
        self.model = None
        self.is_trained = False
        self.training_stats = {}

    def train(self, training_data: TrainingData) -> bool:
        """Train the predictive model.

        Args:
            training_data: Training data

        Returns:
            True if training successful
        """
        try:
            self.logger.info(f"Training {self.model_type.value} model...")

            # This would integrate with actual ML libraries like scikit-learn, TensorFlow, etc.
            # For now, we'll implement a simple linear regression as placeholder

            from sklearn.linear_model import LinearRegression
            from sklearn.model_selection import train_test_split
            from sklearn.metrics import mean_squared_error, r2_score

            # Split data
            X_train, X_test, y_train, y_test = train_test_split(
                training_data.features, training_data.targets,
                test_size=0.2, random_state=42
            )

            # Train model
            self.model = LinearRegression()
            self.model.fit(X_train, y_train)

            # Evaluate model
            y_pred = self.model.predict(X_test)
            mse = mean_squared_error(y_test, y_pred)
            r2 = r2_score(y_test, y_pred)

            self.is_trained = True
            self.training_stats = {
                'training_samples': len(training_data.features),
                'test_samples': len(X_test),
                'mse': mse,
                'r2_score': r2,
                'feature_count': training_data.features.shape[1]
            }

            self.logger.info(f"Model trained successfully. R² = {r2:.3f}, MSE = {mse:.3f}")
            return True

        except Exception as e:
            self.logger.error(f"Failed to train model: {e}")
            return False

    def predict(self, features: Dict[str, float]) -> PredictionResult:
        """Make a prediction.

        Args:
            features: Input features

        Returns:
            Prediction result
        """
        if not self.is_trained or self.model is None:
            raise ValueError(f"Model {self.model_type.value} is not trained")

        try:
            # Convert features to array
            feature_vector = self._features_to_vector(features)

            # Make prediction
            prediction = self.model.predict([feature_vector])[0]

            # Calculate confidence (simplified)
            confidence = min(0.95, max(0.5, 1.0 - abs(prediction * 0.1)))

            # Generate explanation
            explanation = self._generate_explanation(features, prediction)

            # Calculate feature importance (simplified)
            feature_importance = self._calculate_feature_importance(features)

            return PredictionResult(
                model_type=self.model_type,
                prediction=prediction,
                confidence=confidence,
                feature_importance=feature_importance,
                explanation=explanation
            )

        except Exception as e:
            self.logger.error(f"Prediction failed: {e}")
            raise

    def _features_to_vector(self, features: Dict[str, float]) -> np.ndarray:
        """Convert feature dictionary to vector."""
        # This would need to match the feature order used during training
        # For now, return a placeholder
        return np.array(list(features.values()))

    def _generate_explanation(self, features: Dict[str, float], prediction: float) -> str:
        """Generate human-readable explanation for prediction."""
        # Simplified explanation generation
        return f"Prediction based on {len(features)} features with confidence in the model."

    def _calculate_feature_importance(self, features: Dict[str, float]) -> Dict[str, float]:
        """Calculate feature importance."""
        # Simplified importance calculation
        total = sum(features.values())
        if total == 0:
            return {k: 0.0 for k in features.keys()}

        return {k: v / total for k, v in features.items()}


class PrintSuccessPredictor(PredictiveModel):
    """Predicts print job success probability."""

    def __init__(self, feature_extractor: FeatureExtractor):
        """Initialize print success predictor."""
        super().__init__(PredictionModel.PRINT_SUCCESS, feature_extractor)

    def predict_print_success(self, mesh_data: Dict[str, Any],
                            printer_data: Dict[str, Any],
                            settings: Dict[str, Any]) -> PredictionResult:
        """Predict print success probability.

        Args:
            mesh_data: Mesh information
            printer_data: Printer information
            settings: Print settings

        Returns:
            Success prediction result
        """
        # Extract features
        mesh_features = self.feature_extractor.extract_mesh_features(mesh_data)
        printer_features = self.feature_extractor.extract_printer_features(printer_data)

        # Combine features
        all_features = {**mesh_features, **printer_features}

        # Add print settings features
        all_features['layer_height'] = settings.get('layer_height', 0.2)
        all_features['infill_density'] = settings.get('infill_density', 20)
        all_features['print_speed'] = settings.get('print_speed', 50)

        return self.predict(all_features)


class MaterialUsagePredictor(PredictiveModel):
    """Predicts material usage for print jobs."""

    def __init__(self, feature_extractor: FeatureExtractor):
        """Initialize material usage predictor."""
        super().__init__(PredictionModel.MATERIAL_USAGE, feature_extractor)

    def predict_material_usage(self, mesh_data: Dict[str, Any],
                              settings: Dict[str, Any]) -> PredictionResult:
        """Predict material usage in grams.

        Args:
            mesh_data: Mesh information
            settings: Print settings

        Returns:
            Material usage prediction
        """
        # Extract features
        mesh_features = self.feature_extractor.extract_mesh_features(mesh_data)

        # Add print settings features
        all_features = {**mesh_features}
        all_features['infill_density'] = settings.get('infill_density', 20)
        all_features['layer_height'] = settings.get('layer_height', 0.2)
        all_features['support_enabled'] = 1 if settings.get('supports', False) else 0

        return self.predict(all_features)


class PrintTimePredictor(PredictiveModel):
    """Predicts print job duration."""

    def __init__(self, feature_extractor: FeatureExtractor):
        """Initialize print time predictor."""
        super().__init__(PredictionModel.PRINT_TIME, feature_extractor)

    def predict_print_time(self, mesh_data: Dict[str, Any],
                          printer_data: Dict[str, Any],
                          settings: Dict[str, Any]) -> PredictionResult:
        """Predict print time in minutes.

        Args:
            mesh_data: Mesh information
            printer_data: Printer information
            settings: Print settings

        Returns:
            Print time prediction
        """
        # Extract features
        mesh_features = self.feature_extractor.extract_mesh_features(mesh_data)
        printer_features = self.feature_extractor.extract_printer_features(printer_data)

        # Combine features
        all_features = {**mesh_features, **printer_features}
        all_features['print_speed'] = settings.get('print_speed', 50)
        all_features['layer_height'] = settings.get('layer_height', 0.2)

        return self.predict(all_features)


class MaintenancePredictor(PredictiveModel):
    """Predicts when maintenance is needed."""

    def __init__(self, feature_extractor: FeatureExtractor):
        """Initialize maintenance predictor."""
        super().__init__(PredictionModel.MAINTENANCE_NEED, feature_extractor)

    def predict_maintenance_need(self, printer_data: Dict[str, Any],
                                usage_history: List[Dict[str, Any]]) -> PredictionResult:
        """Predict maintenance needs.

        Args:
            printer_data: Current printer information
            usage_history: Historical usage data

        Returns:
            Maintenance prediction
        """
        # Extract features
        printer_features = self.feature_extractor.extract_printer_features(printer_data)

        # Calculate usage statistics
        total_print_time = sum(entry.get('print_time', 0) for entry in usage_history)
        total_failures = sum(1 for entry in usage_history if not entry.get('success', True))

        all_features = {**printer_features}
        all_features['total_print_time_hours'] = total_print_time / 60
        all_features['failure_rate'] = total_failures / max(len(usage_history), 1)

        return self.predict(all_features)


class MLPredictionEngine:
    """Main engine for machine learning predictions."""

    def __init__(self):
        """Initialize ML prediction engine."""
        self.logger = logging.getLogger(__name__)
        self.feature_extractor = FeatureExtractor()
        self.models: Dict[PredictionModel, PredictiveModel] = {}
        self.training_data_dir = Path("data/training")
        self.models_dir = Path("data/models")

        # Create directories
        self.training_data_dir.mkdir(parents=True, exist_ok=True)
        self.models_dir.mkdir(parents=True, exist_ok=True)

        # Initialize models
        self._initialize_models()

    def _initialize_models(self):
        """Initialize all prediction models."""
        model_classes = [
            (PredictionModel.PRINT_SUCCESS, PrintSuccessPredictor),
            (PredictionModel.MATERIAL_USAGE, MaterialUsagePredictor),
            (PredictionModel.PRINT_TIME, PrintTimePredictor),
            (PredictionModel.MAINTENANCE_NEED, MaintenancePredictor),
        ]

        for model_type, model_class in model_classes:
            self.models[model_type] = model_class(self.feature_extractor)
            self.logger.info(f"Initialized {model_type.value} prediction model")

    def train_all_models(self, force_retrain: bool = False) -> Dict[str, bool]:
        """Train all available models.

        Args:
            force_retrain: Force retraining even if models exist

        Returns:
            Dictionary mapping model names to training success
        """
        results = {}

        for model_type, model in self.models.items():
            try:
                # Load or generate training data
                training_data = self._load_training_data(model_type)

                if training_data is None or force_retrain:
                    # Generate synthetic training data for demonstration
                    training_data = self._generate_synthetic_training_data(model_type)

                # Train model
                success = model.train(training_data)
                results[model_type.value] = success

                if success:
                    self._save_model(model_type, model)

            except Exception as e:
                self.logger.error(f"Failed to train {model_type.value} model: {e}")
                results[model_type.value] = False

        return results

    def _load_training_data(self, model_type: PredictionModel) -> Optional[TrainingData]:
        """Load training data for a model."""
        data_file = self.training_data_dir / f"{model_type.value}_training.npy"

        if not data_file.exists():
            return None

        try:
            data = np.load(data_file, allow_pickle=True).item()
            return TrainingData(**data)
        except Exception as e:
            self.logger.error(f"Failed to load training data for {model_type.value}: {e}")
            return None

    def _generate_synthetic_training_data(self, model_type: PredictionModel) -> TrainingData:
        """Generate synthetic training data for demonstration."""
        # Generate synthetic data based on model type
        num_samples = 1000

        if model_type == PredictionModel.PRINT_SUCCESS:
            # Features: mesh complexity, printer age, material strength, layer height
            features = np.random.rand(num_samples, 4)
            # Target: print success probability (0-1)
            targets = 0.5 + 0.3 * features[:, 0] - 0.2 * features[:, 1] + 0.1 * features[:, 2] + np.random.normal(0, 0.1, num_samples)
            targets = np.clip(targets, 0, 1)

        elif model_type == PredictionModel.MATERIAL_USAGE:
            # Features: mesh volume, infill density, layer height
            features = np.random.rand(num_samples, 3) * [100, 100, 1]  # Scale appropriately
            # Target: material usage in grams
            targets = 10 + 0.5 * features[:, 0] + 0.1 * features[:, 1] + 5 * features[:, 2] + np.random.normal(0, 2, num_samples)

        elif model_type == PredictionModel.PRINT_TIME:
            # Features: mesh complexity, print volume, print speed
            features = np.random.rand(num_samples, 3) * [10, 1000, 100]
            # Target: print time in minutes
            targets = 30 + 2 * features[:, 0] + 0.1 * features[:, 1] - 0.2 * features[:, 2] + np.random.normal(0, 5, num_samples)
            targets = np.maximum(targets, 1)

        else:
            # Default synthetic data
            features = np.random.rand(num_samples, 3)
            targets = np.random.rand(num_samples)

        feature_names = [f"feature_{i}" for i in range(features.shape[1])]

        return TrainingData(
            features=features,
            targets=targets,
            feature_names=feature_names,
            metadata={'synthetic': True, 'samples': num_samples}
        )

    def _save_model(self, model_type: PredictionModel, model: PredictiveModel):
        """Save trained model."""
        model_file = self.models_dir / f"{model_type.value}_model.pkl"

        try:
            import pickle
            with open(model_file, 'wb') as f:
                pickle.dump({
                    'model': model.model,
                    'model_type': model_type,
                    'training_stats': model.training_stats,
                    'is_trained': model.is_trained
                }, f)

            self.logger.info(f"Saved {model_type.value} model to {model_file}")

        except Exception as e:
            self.logger.error(f"Failed to save {model_type.value} model: {e}")

    def predict_print_success(self, mesh_data: Dict[str, Any],
                            printer_data: Dict[str, Any],
                            settings: Dict[str, Any]) -> PredictionResult:
        """Predict print success probability."""
        model = self.models[PredictionModel.PRINT_SUCCESS]
        return model.predict_print_success(mesh_data, printer_data, settings)

    def predict_material_usage(self, mesh_data: Dict[str, Any],
                              settings: Dict[str, Any]) -> PredictionResult:
        """Predict material usage."""
        model = self.models[PredictionModel.MATERIAL_USAGE]
        return model.predict_material_usage(mesh_data, settings)

    def predict_print_time(self, mesh_data: Dict[str, Any],
                          printer_data: Dict[str, Any],
                          settings: Dict[str, Any]) -> PredictionResult:
        """Predict print time."""
        model = self.models[PredictionModel.PRINT_TIME]
        return model.predict_print_time(mesh_data, printer_data, settings)

    def predict_maintenance_need(self, printer_data: Dict[str, Any],
                                usage_history: List[Dict[str, Any]]) -> PredictionResult:
        """Predict maintenance needs."""
        model = self.models[PredictionModel.MAINTENANCE_NEED]
        return model.predict_maintenance_need(printer_data, usage_history)

    def get_model_stats(self) -> Dict[str, Any]:
        """Get statistics for all models."""
        stats = {}

        for model_type, model in self.models.items():
            stats[model_type.value] = {
                'is_trained': model.is_trained,
                'training_stats': model.training_stats
            }

        return stats


# Global ML prediction engine
ml_engine = MLPredictionEngine()
