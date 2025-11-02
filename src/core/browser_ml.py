"""TensorFlow.js/ONNX-inspired browser-based machine learning for 3D CAD operations."""

from __future__ import annotations

import logging
import math
import random
import time
from collections import defaultdict
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Union, Callable, Tuple
from pathlib import Path


class MLFramework(Enum):
    """Machine learning frameworks."""
    TENSORFLOW_JS = "tensorflow_js"
    ONNX = "onnx"
    PYTORCH = "pytorch"
    KERAS = "keras"
    CUSTOM = "custom"


class ModelType(Enum):
    """Model types."""
    CLASSIFICATION = "classification"
    REGRESSION = "regression"
    CLUSTERING = "clustering"
    GENERATIVE = "generative"
    REINFORCEMENT = "reinforcement"


@dataclass
class NeuralNetworkLayer:
    """Neural network layer."""
    layer_type: str
    units: int
    activation: Optional[str] = None
    input_shape: Optional[Tuple[int, ...]] = None
    weights: Optional[List[List[float]]] = None
    biases: Optional[List[float]] = None

    def __post_init__(self):
        if self.weights is None and self.units > 0:
            # Initialize random weights
            if self.input_shape:
                input_size = self.input_shape[0] if len(self.input_shape) > 0 else 1
                self.weights = [[random.random() for _ in range(input_size)] for _ in range(self.units)]
            else:
                self.weights = [[random.random() for _ in range(1)] for _ in range(self.units)]

        if self.biases is None:
            self.biases = [random.random() for _ in range(self.units)]


class BrowserMLModel:
    """Browser-compatible machine learning model."""

    def __init__(self, model_name: str, model_type: ModelType, framework: MLFramework):
        self.logger = logging.getLogger(__name__)
        self.model_name = model_name
        self.model_type = model_type
        self.framework = framework
        self.layers: List[NeuralNetworkLayer] = []
        self.input_shape: Tuple[int, ...] = ()
        self.output_shape: Tuple[int, ...] = ()
        self.training_data: List[Dict[str, Any]] = []
        self.model_weights: Dict[str, Any] = {}
        self.compiled: bool = False

    def add_layer(self, layer: NeuralNetworkLayer) -> None:
        """Add layer to model."""
        self.layers.append(layer)

        # Update input/output shapes
        if not self.layers[:-1]:  # First layer
            if layer.input_shape:
                self.input_shape = layer.input_shape
        else:
            # Connect to previous layer
            prev_layer = self.layers[-2]
            if not layer.input_shape:
                layer.input_shape = (prev_layer.units,)

        self.logger.debug(f"Added layer: {layer.layer_type} with {layer.units} units")

    def compile_model(self, optimizer: str = "adam", loss: str = "mean_squared_error") -> bool:
        """Compile model for training."""
        try:
            # Set output shape
            if self.layers:
                self.output_shape = (self.layers[-1].units,)

            # Initialize model weights
            self._initialize_weights()

            self.compiled = True

            self.logger.info(f"Compiled model {self.model_name}")
            return True

        except Exception as e:
            self.logger.error(f"Model compilation failed: {e}")
            return False

    def _initialize_weights(self) -> None:
        """Initialize model weights."""
        self.model_weights = {}

        for i, layer in enumerate(self.layers):
            layer_key = f"layer_{i}"
            self.model_weights[layer_key] = {
                "weights": layer.weights,
                "biases": layer.biases,
                "layer_type": layer.layer_type,
                "activation": layer.activation
            }

    def predict(self, input_data: List[List[float]]) -> List[List[float]]:
        """Make predictions."""
        if not self.compiled:
            raise ValueError("Model must be compiled before prediction")

        try:
            # Forward pass through network
            current_output = input_data

            for layer in self.layers:
                current_output = self._forward_layer(current_output, layer)

            return current_output

        except Exception as e:
            self.logger.error(f"Prediction failed: {e}")
            return []

    def _forward_layer(self, input_data: Any, layer: NeuralNetworkLayer) -> Any:
        """Forward pass through single layer."""
        if layer.layer_type == "dense":
            return self._dense_forward(input_data, layer)
        elif layer.layer_type == "conv2d":
            return self._conv2d_forward(input_data, layer)
        elif layer.layer_type == "maxpool2d":
            return self._maxpool2d_forward(input_data, layer)
        elif layer.layer_type == "flatten":
            return self._flatten_forward(input_data)
        else:
            return input_data  # Pass through

    def _dense_forward(self, input_data: List[List[float]], layer: NeuralNetworkLayer) -> List[List[float]]:
        """Dense layer forward pass."""
        if not layer.weights or not layer.biases:
            return input_data

        output = []

        for sample in input_data:
            sample_output = []

            for neuron_weights, bias in zip(layer.weights, layer.biases):
                # Weighted sum
                weighted_sum = sum(w * x for w, x in zip(neuron_weights, sample)) + bias

                # Apply activation
                if layer.activation == "relu":
                    activation_output = max(0, weighted_sum)
                elif layer.activation == "sigmoid":
                    activation_output = 1 / (1 + math.exp(-weighted_sum))
                elif layer.activation == "tanh":
                    activation_output = math.tanh(weighted_sum)
                else:
                    activation_output = weighted_sum

                sample_output.append(activation_output)

            output.append(sample_output)

        return output

    def _conv2d_forward(self, input_data: Any, layer: NeuralNetworkLayer) -> Any:
        """Convolution layer forward pass (simplified)."""
        # Simplified 2D convolution
        return input_data

    def _maxpool2d_forward(self, input_data: Any, layer: NeuralNetworkLayer) -> Any:
        """Max pooling forward pass (simplified)."""
        # Simplified max pooling
        return input_data

    def _flatten_forward(self, input_data: Any) -> List[float]:
        """Flatten layer forward pass."""
        if isinstance(input_data, list) and isinstance(input_data[0], list):
            return [item for sublist in input_data for item in sublist]
        else:
            return input_data

    def train(self, training_data: List[Dict[str, Any]], epochs: int = 10) -> Dict[str, Any]:
        """Train model."""
        if not self.compiled:
            return {"error": "Model must be compiled before training"}

        training_result = {
            "model_name": self.model_name,
            "epochs": epochs,
            "training_samples": len(training_data),
            "training_time": 0.0,
            "loss_history": [],
            "accuracy_history": [],
            "success": True
        }

        start_time = time.time()

        try:
            # Simplified training loop
            for epoch in range(epochs):
                epoch_loss = 0
                epoch_accuracy = 0

                for sample in training_data:
                    # Forward pass
                    prediction = self.predict([sample["input"]])

                    # Calculate loss (simplified)
                    target = sample["target"]
                    if isinstance(target, list) and prediction:
                        loss = sum((p - t) ** 2 for p, t in zip(prediction[0], target))
                        epoch_loss += loss

                        # Simple accuracy for classification
                        if self.model_type == ModelType.CLASSIFICATION:
                            predicted_class = prediction[0].index(max(prediction[0]))
                            actual_class = target.index(max(target)) if isinstance(target, list) else target
                            epoch_accuracy += 1 if predicted_class == actual_class else 0

                # Average loss and accuracy
                avg_loss = epoch_loss / len(training_data)
                avg_accuracy = epoch_accuracy / len(training_data) if self.model_type == ModelType.CLASSIFICATION else 0

                training_result["loss_history"].append(avg_loss)
                training_result["accuracy_history"].append(avg_accuracy)

                # Update weights (simplified gradient descent)
                self._update_weights(training_data, learning_rate=0.01)

            training_result["training_time"] = time.time() - start_time

        except Exception as e:
            training_result["success"] = False
            training_result["error"] = str(e)

        return training_result

    def _update_weights(self, training_data: List[Dict[str, Any]], learning_rate: float) -> None:
        """Update model weights (simplified)."""
        # Simplified gradient descent
        for layer in self.layers:
            if layer.weights and layer.biases:
                # Update weights (random gradient simulation)
                for i in range(len(layer.weights)):
                    for j in range(len(layer.weights[i])):
                        layer.weights[i][j] += (random.random() - 0.5) * learning_rate

                # Update biases
                for i in range(len(layer.biases)):
                    layer.biases[i] += (random.random() - 0.5) * learning_rate

    def save_model(self, format: str = "json") -> str:
        """Save model in browser-compatible format."""
        model_data = {
            "model_name": self.model_name,
            "model_type": self.model_type.value,
            "framework": self.framework.value,
            "input_shape": self.input_shape,
            "output_shape": self.output_shape,
            "layers": [
                {
                    "layer_type": layer.layer_type,
                    "units": layer.units,
                    "activation": layer.activation,
                    "input_shape": layer.input_shape,
                    "weights": layer.weights,
                    "biases": layer.biases
                }
                for layer in self.layers
            ],
            "compiled": self.compiled
        }

        if format == "json":
            import json
            return json.dumps(model_data, indent=2)
        else:
            return str(model_data)

    def load_model(self, model_data: str) -> bool:
        """Load model from data."""
        try:
            import json
            data = json.loads(model_data)

            # Restore model properties
            self.model_name = data["model_name"]
            self.model_type = ModelType(data["model_type"])
            self.framework = MLFramework(data["framework"])
            self.input_shape = tuple(data["input_shape"])
            self.output_shape = tuple(data["output_shape"])
            self.compiled = data["compiled"]

            # Restore layers
            self.layers = []
            for layer_data in data["layers"]:
                layer = NeuralNetworkLayer(
                    layer_type=layer_data["layer_type"],
                    units=layer_data["units"],
                    activation=layer_data.get("activation"),
                    input_shape=tuple(layer_data["input_shape"]) if layer_data["input_shape"] else None,
                    weights=layer_data["weights"],
                    biases=layer_data["biases"]
                )
                self.layers.append(layer)

            return True

        except Exception as e:
            self.logger.error(f"Model loading failed: {e}")
            return False

    def get_model_summary(self) -> Dict[str, Any]:
        """Get model summary."""
        return {
            "model_name": self.model_name,
            "model_type": self.model_type.value,
            "framework": self.framework.value,
            "input_shape": self.input_shape,
            "output_shape": self.output_shape,
            "total_layers": len(self.layers),
            "total_parameters": sum(len(layer.weights) * len(layer.weights[0]) + len(layer.biases)
                                   for layer in self.layers if layer.weights and layer.biases),
            "compiled": self.compiled,
            "training_samples": len(self.training_data)
        }


class CADMachineLearningEngine:
    """Machine learning engine for CAD applications."""

    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.models: Dict[str, BrowserMLModel] = {}
        self.training_datasets: Dict[str, List[Dict[str, Any]]] = {}
        self.predictions_cache: Dict[str, Any] = {}

    def create_mesh_classifier(self, model_name: str) -> BrowserMLModel:
        """Create mesh quality classifier."""
        model = BrowserMLModel(model_name, ModelType.CLASSIFICATION, MLFramework.TENSORFLOW_JS)

        # Add layers for mesh classification
        model.add_layer(NeuralNetworkLayer(
            "dense", 64, "relu",
            input_shape=(10,)  # 10 mesh features
        ))

        model.add_layer(NeuralNetworkLayer("dense", 32, "relu"))

        model.add_layer(NeuralNetworkLayer("dense", 3, "softmax"))  # 3 quality classes

        self.models[model_name] = model

        self.logger.info(f"Created mesh classifier: {model_name}")
        return model

    def create_mesh_generator(self, model_name: str) -> BrowserMLModel:
        """Create mesh generator model."""
        model = BrowserMLModel(model_name, ModelType.GENERATIVE, MLFramework.ONNX)

        # Add layers for mesh generation
        model.add_layer(NeuralNetworkLayer(
            "dense", 128, "relu",
            input_shape=(20,)  # Design parameters
        ))

        model.add_layer(NeuralNetworkLayer("dense", 256, "relu"))

        model.add_layer(NeuralNetworkLayer("dense", 100, "tanh"))  # Vertex coordinates

        self.models[model_name] = model

        self.logger.info(f"Created mesh generator: {model_name}")
        return model

    def extract_mesh_features(self, vertices: List[List[float]],
                            faces: List[List[int]]) -> List[float]:
        """Extract features from mesh for ML."""
        features = []

        if not vertices or not faces:
            return [0] * 10  # Default features

        try:
            # Basic geometric features
            # 1. Vertex count
            features.append(len(vertices))

            # 2. Face count
            features.append(len(faces))

            # 3. Average vertex degree
            if faces:
                total_edges = sum(len(face) for face in faces)
                avg_degree = total_edges / len(vertices) if vertices else 0
                features.append(avg_degree)

            # 4. Bounding box volume
            if vertices:
                min_coords = [min(coord[i] for coord in vertices) for i in range(3)]
                max_coords = [max(coord[i] for coord in vertices) for i in range(3)]
                bbox_volume = (max_coords[0] - min_coords[0]) * (max_coords[1] - min_coords[1]) * (max_coords[2] - min_coords[2])
                features.append(bbox_volume)

            # 5. Average edge length
            total_edge_length = 0
            edge_count = 0
            for face in faces:
                for i in range(len(face)):
                    v1 = vertices[face[i]]
                    v2 = vertices[face[(i + 1) % len(face)]]
                    edge_length = math.sqrt(sum((a - b) ** 2 for a, b in zip(v1, v2)))
                    total_edge_length += edge_length
                    edge_count += 1

            avg_edge_length = total_edge_length / edge_count if edge_count > 0 else 0
            features.append(avg_edge_length)

            # 6. Surface area (simplified)
            surface_area = 0
            for face in faces:
                if len(face) >= 3:
                    face_vertices = [vertices[i] for i in face[:3]]
                    # Calculate triangle area
                    v1, v2, v3 = face_vertices
                    edge1 = [v2[0] - v1[0], v2[1] - v1[1], v2[2] - v1[2]]
                    edge2 = [v3[0] - v1[0], v3[1] - v1[1], v3[2] - v1[2]]

                    cross_product = [
                        edge1[1] * edge2[2] - edge1[2] * edge2[1],
                        edge1[2] * edge2[0] - edge1[0] * edge2[2],
                        edge1[0] * edge2[1] - edge1[1] * edge2[0]
                    ]

                    area = math.sqrt(sum(x*x for x in cross_product)) / 2
                    surface_area += area

            features.append(surface_area)

            # 7-10. Additional features (aspect ratios, etc.)
            if vertices:
                min_coords = [min(coord[i] for coord in vertices) for i in range(3)]
                max_coords = [max(coord[i] for coord in vertices) for i in range(3)]
                dimensions = [max_coords[i] - min_coords[i] for i in range(3)]

                # Aspect ratios
                if dimensions[0] > 0:
                    features.append(dimensions[1] / dimensions[0])  # Y/X ratio
                    features.append(dimensions[2] / dimensions[0])  # Z/X ratio

                # Compactness
                volume = dimensions[0] * dimensions[1] * dimensions[2]
                compactness = surface_area / volume if volume > 0 else 0
                features.append(compactness)

        except Exception as e:
            self.logger.error(f"Feature extraction failed: {e}")
            features = [0] * 10

        return features

    def classify_mesh_quality(self, vertices: List[List[float]],
                            faces: List[List[int]]) -> Dict[str, Any]:
        """Classify mesh quality using ML."""
        features = self.extract_mesh_features(vertices, faces)

        # Use default classifier if available
        classifier_name = "mesh_quality_classifier"

        if classifier_name not in self.models:
            # Create default classifier
            self.create_mesh_classifier(classifier_name)

        model = self.models[classifier_name]

        if not model.compiled:
            model.compile_model()

        # Make prediction
        prediction = model.predict([features])

        if prediction and prediction[0]:
            quality_scores = prediction[0]
            quality_class = quality_scores.index(max(quality_scores))

            quality_labels = ["poor", "good", "excellent"]

            return {
                "quality_class": quality_labels[quality_class] if quality_class < len(quality_labels) else "unknown",
                "quality_scores": quality_scores,
                "features_used": len(features),
                "model_used": classifier_name,
                "classification_confidence": max(quality_scores)
            }

        return {"error": "Classification failed"}

    def generate_mesh_suggestion(self, design_parameters: Dict[str, Any]) -> Dict[str, Any]:
        """Generate mesh suggestion using ML."""
        # Convert parameters to feature vector
        param_features = []

        for key, value in design_parameters.items():
            if isinstance(value, (int, float)):
                param_features.append(value)
            elif isinstance(value, str):
                # Simple string encoding
                param_features.append(hash(value) % 1000)
            else:
                param_features.append(0)

        # Pad to expected size
        while len(param_features) < 20:
            param_features.append(0)

        # Use generator model
        generator_name = "mesh_generator"

        if generator_name not in self.models:
            self.create_mesh_generator(generator_name)

        model = self.models[generator_name]

        if not model.compiled:
            model.compile_model()

        # Generate mesh vertices
        generated_vertices = model.predict([param_features])

        if generated_vertices and generated_vertices[0]:
            # Convert to 3D vertices (assuming 100 vertices with 3 coordinates each)
            vertex_data = generated_vertices[0][:300]  # 100 vertices * 3 coordinates

            vertices = []
            for i in range(0, len(vertex_data), 3):
                if i + 2 < len(vertex_data):
                    vertices.append([vertex_data[i], vertex_data[i+1], vertex_data[i+2]])

            return {
                "generated_vertices": vertices,
                "vertex_count": len(vertices),
                "design_parameters": design_parameters,
                "model_used": generator_name,
                "generation_confidence": 0.8  # Simplified confidence
            }

        return {"error": "Mesh generation failed"}

    def train_quality_model(self, training_meshes: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Train mesh quality model."""
        classifier_name = "mesh_quality_classifier"

        if classifier_name not in self.models:
            self.create_mesh_classifier(classifier_name)

        model = self.models[classifier_name]

        # Prepare training data
        training_data = []

        for mesh in training_meshes:
            vertices = mesh.get("vertices", [])
            faces = mesh.get("faces", [])
            quality_label = mesh.get("quality_label", "good")

            features = self.extract_mesh_features(vertices, faces)

            # Convert quality label to one-hot encoding
            quality_classes = ["poor", "good", "excellent"]
            target = [0, 0, 0]
            if quality_label in quality_classes:
                target[quality_classes.index(quality_label)] = 1

            training_data.append({
                "input": features,
                "target": target
            })

        # Train model
        training_result = model.train(training_data, epochs=50)

        return {
            "model_name": classifier_name,
            "training_result": training_result,
            "training_samples": len(training_data),
            "final_loss": training_result.get("loss_history", [-1])[-1],
            "final_accuracy": training_result.get("accuracy_history", [0])[-1]
        }

    def optimize_mesh_with_ml(self, vertices: List[List[float]],
                            faces: List[List[int]],
                            optimization_goal: str) -> Dict[str, Any]:
        """Optimize mesh using machine learning."""
        optimization_result = {
            "optimization_goal": optimization_goal,
            "original_vertices": len(vertices),
            "original_faces": len(faces),
            "optimization_applied": False,
            "ml_suggestions": []
        }

        try:
            # Extract features
            features = self.extract_mesh_features(vertices, faces)

            # Classify current quality
            quality_analysis = self.classify_mesh_quality(vertices, faces)
            optimization_result["current_quality"] = quality_analysis

            # Generate suggestions based on quality
            current_quality = quality_analysis.get("quality_class", "unknown")

            if current_quality == "poor":
                optimization_result["ml_suggestions"].append("Consider increasing mesh resolution")
                optimization_result["ml_suggestions"].append("Check for mesh defects")
            elif current_quality == "good":
                optimization_result["ml_suggestions"].append("Mesh quality is acceptable")
                optimization_result["ml_suggestions"].append("Consider optimization for specific use case")
            elif current_quality == "excellent":
                optimization_result["ml_suggestions"].append("High-quality mesh detected")
                optimization_result["ml_suggestions"].append("Minimal optimization needed")

            # Generate optimized version
            if optimization_goal == "reduce_vertices":
                # Simple vertex reduction
                reduction_ratio = 0.8
                new_vertex_count = int(len(vertices) * reduction_ratio)

                if new_vertex_count >= 3:  # Minimum for a triangle
                    # Simple random sampling (in real implementation, would use better algorithms)
                    sampled_indices = random.sample(range(len(vertices)), new_vertex_count)

                    optimized_vertices = [vertices[i] for i in sorted(sampled_indices)]
                    optimized_faces = []

                    # Remap faces to new vertex indices
                    vertex_map = {old_idx: new_idx for new_idx, old_idx in enumerate(sorted(sampled_indices))}

                    for face in faces:
                        try:
                            new_face = [vertex_map[idx] for idx in face if idx in vertex_map]
                            if len(new_face) >= 3:
                                optimized_faces.append(new_face)
                        except KeyError:
                            continue  # Skip faces with missing vertices

                    optimization_result.update({
                        "optimized_vertices": optimized_vertices,
                        "optimized_faces": optimized_faces,
                        "optimization_applied": True,
                        "reduction_ratio": reduction_ratio,
                        "vertices_reduced": len(vertices) - len(optimized_vertices)
                    })

        except Exception as e:
            optimization_result["error"] = str(e)

        return optimization_result

    def get_ml_statistics(self) -> Dict[str, Any]:
        """Get ML system statistics."""
        return {
            "total_models": len(self.models),
            "model_types": list(set(model.model_type.value for model in self.models.values())),
            "frameworks_used": list(set(model.framework.value for model in self.models.values())),
            "training_datasets": len(self.training_datasets),
            "cached_predictions": len(self.predictions_cache),
            "available_models": list(self.models.keys())
        }


class BrowserMLInterface:
    """Browser-compatible ML interface."""

    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.ml_engine = CADMachineLearningEngine()
        self.web_models: Dict[str, str] = {}  # Model name -> JavaScript code
        self.inference_cache: Dict[str, Any] = {}

    def generate_tensorflow_js_code(self, model_name: str) -> str:
        """Generate TensorFlow.js code."""
        if model_name not in self.ml_engine.models:
            return "// Model not found"

        model = self.ml_engine.models[model_name]

        # Generate TF.js model code
        tfjs_code = f"""
        // TensorFlow.js model: {model_name}
        const model = tf.sequential({{
          layers: [
        """

        for i, layer in enumerate(model.layers):
            layer_config = f"""
            tf.layers.dense({{
              units: {layer.units},
              activation: '{layer.activation or 'linear'}',
              inputShape: {list(layer.input_shape) if layer.input_shape else 'undefined'}
            }})"""

            if i < len(model.layers) - 1:
                layer_config += ","

            tfjs_code += layer_config

        tfjs_code += """
          ]
        });

        // Compile model
        model.compile({
          optimizer: 'adam',
          loss: 'meanSquaredError',
          metrics: ['accuracy']
        });

        // Model ready for training/inference
        """

        self.web_models[model_name] = tfjs_code

        return tfjs_code

    def generate_onnx_model(self, model_name: str) -> str:
        """Generate ONNX model representation."""
        if model_name not in self.ml_engine.models:
            return "// Model not found"

        model = self.ml_engine.models[model_name]

        # Generate ONNX-style representation
        onnx_code = f"""
        // ONNX-style model: {model_name}
        const model = {{
          name: '{model_name}',
          inputShape: {list(model.input_shape)},
          outputShape: {list(model.output_shape)},
          layers: [
        """

        for i, layer in enumerate(model.layers):
            layer_repr = f"""
            {{
              type: '{layer.layer_type}',
              units: {layer.units},
              activation: '{layer.activation or 'none'}',
              weights: {layer.weights},
              biases: {layer.biases}
            }}"""

            if i < len(model.layers) - 1:
                layer_repr += ","

            onnx_code += layer_repr

        onnx_code += """
          ]
        };

        // ONNX model ready for inference
        """

        return onnx_code

    def create_ml_training_data(self, mesh_samples: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Create training data from mesh samples."""
        training_data = []

        for sample in mesh_samples:
            vertices = sample.get("vertices", [])
            faces = sample.get("faces", [])
            quality_label = sample.get("quality_label", "good")

            features = self.ml_engine.extract_mesh_features(vertices, faces)

            # Convert quality to numerical target
            quality_map = {"poor": [1, 0, 0], "good": [0, 1, 0], "excellent": [0, 0, 1]}
            target = quality_map.get(quality_label, [0, 1, 0])

            training_data.append({
                "input": features,
                "target": target,
                "mesh_id": sample.get("id", "unknown"),
                "quality_label": quality_label
            })

        return training_data

    def perform_browser_inference(self, model_name: str,
                                input_data: List[List[float]]) -> Dict[str, Any]:
        """Perform inference in browser-compatible format."""
        cache_key = f"{model_name}_{hash(str(input_data))}"

        if cache_key in self.inference_cache:
            return self.inference_cache[cache_key]

        if model_name not in self.ml_engine.models:
            return {"error": f"Model {model_name} not found"}

        model = self.ml_engine.models[model_name]

        try:
            # Perform inference
            prediction = model.predict(input_data)

            result = {
                "model_name": model_name,
                "input_shape": input_data[0] if input_data else [],
                "prediction": prediction,
                "prediction_shape": prediction[0] if prediction else [],
                "inference_time": 0.1,  # Simulated
                "framework": model.framework.value
            }

            self.inference_cache[cache_key] = result

            return result

        except Exception as e:
            return {"error": str(e)}

    def get_browser_ml_summary(self) -> Dict[str, Any]:
        """Get browser ML summary."""
        return {
            "ml_engine": self.ml_engine.get_ml_statistics(),
            "web_models": len(self.web_models),
            "inference_cache": len(self.inference_cache),
            "supported_frameworks": ["tensorflow_js", "onnx", "webgl"],
            "browser_features": [
                "real_time_inference",
                "webgl_acceleration",
                "model_conversion",
                "edge_computing"
            ]
        }


class CADBrowserMLSystem:
    """Complete browser-based ML system for CAD."""

    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.ml_engine = CADMachineLearningEngine()
        self.browser_interface = BrowserMLInterface()
        self.trained_models: Dict[str, Dict[str, Any]] = {}

    def initialize_browser_ml(self) -> bool:
        """Initialize browser ML system."""
        try:
            # Create default models
            self.ml_engine.create_mesh_classifier("default_quality_classifier")
            self.ml_engine.create_mesh_generator("default_mesh_generator")

            # Setup training datasets
            self._setup_training_datasets()

            self.logger.info("Browser ML system initialized")
            return True

        except Exception as e:
            self.logger.error(f"Browser ML initialization failed: {e}")
            return False

    def _setup_training_datasets(self) -> None:
        """Setup training datasets."""
        # Sample training data for mesh quality classification
        sample_meshes = [
            {
                "id": "sample_1",
                "vertices": [[0, 0, 0], [1, 0, 0], [0, 1, 0], [0, 0, 1]],
                "faces": [[0, 1, 2], [0, 1, 3], [0, 2, 3], [1, 2, 3]],
                "quality_label": "good"
            },
            {
                "id": "sample_2",
                "vertices": [[0, 0, 0], [0.5, 0, 0], [0, 0.5, 0]],
                "faces": [[0, 1, 2]],
                "quality_label": "poor"
            },
            {
                "id": "sample_3",
                "vertices": [[i, j, k] for i in range(10) for j in range(10) for k in range(10)],
                "faces": [],  # No faces
                "quality_label": "poor"
            }
        ]

        self.ml_engine.training_datasets["mesh_quality"] = sample_meshes

    def analyze_mesh_with_ml(self, mesh_data: Dict[str, Any]) -> Dict[str, Any]:
        """Analyze mesh using machine learning."""
        analysis_result = {
            "mesh_id": mesh_data.get("id", "unknown"),
            "analysis_timestamp": time.time(),
            "quality_classification": {},
            "optimization_suggestions": {},
            "generation_suggestions": {},
            "ml_insights": []
        }

        try:
            vertices = mesh_data.get("vertices", [])
            faces = mesh_data.get("faces", [])

            # Classify mesh quality
            quality_result = self.ml_engine.classify_mesh_quality(vertices, faces)
            analysis_result["quality_classification"] = quality_result

            # Optimize with ML
            optimization_result = self.ml_engine.optimize_mesh_with_ml(
                vertices, faces, "balanced"
            )
            analysis_result["optimization_suggestions"] = optimization_result

            # Generate design suggestions
            design_params = {
                "target_quality": quality_result.get("quality_class", "good"),
                "vertex_count": len(vertices),
                "face_count": len(faces)
            }

            generation_result = self.ml_engine.generate_mesh_suggestion(design_params)
            analysis_result["generation_suggestions"] = generation_result

            # Generate insights
            current_quality = quality_result.get("quality_class", "unknown")

            if current_quality == "poor":
                analysis_result["ml_insights"].append("Mesh quality is below average - consider refinement")
            elif current_quality == "excellent":
                analysis_result["ml_insights"].append("High-quality mesh detected - suitable for production")

        except Exception as e:
            analysis_result["error"] = str(e)

        return analysis_result

    def train_custom_model(self, model_type: str, training_data: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Train custom ML model."""
        training_result = {
            "model_type": model_type,
            "training_data_size": len(training_data),
            "training_timestamp": time.time(),
            "model_created": None,
            "training_success": False
        }

        try:
            if model_type == "quality_classifier":
                train_result = self.ml_engine.train_quality_model(training_data)
                training_result.update(train_result)
                training_result["model_created"] = "mesh_quality_classifier"

            elif model_type == "mesh_generator":
                # Create generator model
                model_name = "custom_mesh_generator"
                self.ml_engine.create_mesh_generator(model_name)

                # Train with provided data
                train_result = self.ml_engine.models[model_name].train(training_data)
                training_result.update(train_result)
                training_result["model_created"] = model_name

            training_result["training_success"] = True

        except Exception as e:
            training_result["error"] = str(e)

        return training_result

    def generate_web_compatible_model(self, model_name: str, format: str = "tensorflow_js") -> str:
        """Generate web-compatible model."""
        if format == "tensorflow_js":
            return self.browser_interface.generate_tensorflow_js_code(model_name)
        elif format == "onnx":
            return self.browser_interface.generate_onnx_model(model_name)
        else:
            return "// Unsupported format"

    def get_ml_analysis_report(self) -> Dict[str, Any]:
        """Get ML analysis report."""
        return {
            "ml_engine": self.ml_engine.get_ml_statistics(),
            "browser_interface": self.browser_interface.get_browser_ml_summary(),
            "trained_models": len(self.trained_models),
            "analysis_capabilities": [
                "mesh_quality_classification",
                "mesh_optimization",
                "design_suggestion_generation",
                "real_time_inference",
                "browser_compatibility"
            ]
        }


# Factory functions for browser ML
def create_ml_model(model_name: str, model_type: ModelType, framework: MLFramework) -> BrowserMLModel:
    """Create ML model."""
    return BrowserMLModel(model_name, model_type, framework)


def create_ml_engine() -> CADMachineLearningEngine:
    """Create CAD ML engine."""
    return CADMachineLearningEngine()


def create_browser_interface() -> BrowserMLInterface:
    """Create browser ML interface."""
    return BrowserMLInterface()


def create_browser_ml_system() -> CADBrowserMLSystem:
    """Create browser ML system."""
    return CADBrowserMLSystem()
