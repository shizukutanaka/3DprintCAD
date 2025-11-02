"""R/Octave-inspired statistical computing and data analysis for 3D CAD operations."""

from __future__ import annotations

import logging
import math
import statistics
from collections import defaultdict
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Union
from pathlib import Path


class StatisticalMethod(Enum):
    """Statistical methods."""
    DESCRIPTIVE = "descriptive"
    INFERENTIAL = "inferential"
    REGRESSION = "regression"
    CLUSTERING = "clustering"
    TIME_SERIES = "time_series"


class DataFrame:
    """R data.frame equivalent."""

    def __init__(self, data: Dict[str, List[Any]] = None):
        self.logger = logging.getLogger(__name__)
        self.data = data or {}
        self.columns = list(self.data.keys())
        self.row_count = len(next(iter(self.data.values()), []))

    def __getitem__(self, column: str) -> List[Any]:
        """Get column data."""
        if column not in self.data:
            raise KeyError(f"Column {column} not found")
        return self.data[column]

    def __setitem__(self, column: str, values: List[Any]) -> None:
        """Set column data."""
        self.data[column] = values
        if column not in self.columns:
            self.columns.append(column)

        # Update row count
        self.row_count = len(next(iter(self.data.values()), []))

    def add_row(self, row_data: Dict[str, Any]) -> None:
        """Add row to data frame."""
        for column, value in row_data.items():
            if column not in self.data:
                self.data[column] = []

            self.data[column].append(value)

        self.row_count = len(next(iter(self.data.values()), []))

    def to_dict(self) -> Dict[str, List[Any]]:
        """Convert to dictionary."""
        return self.data.copy()

    def summary(self) -> Dict[str, Any]:
        """Get summary statistics."""
        summary_stats = {}

        for column, values in self.data.items():
            if not values:
                continue

            try:
                if isinstance(values[0], (int, float)):
                    summary_stats[column] = {
                        "mean": statistics.mean(values),
                        "median": statistics.median(values),
                        "std": statistics.stdev(values),
                        "min": min(values),
                        "max": max(values),
                        "count": len(values)
                    }
                else:
                    summary_stats[column] = {
                        "unique": len(set(values)),
                        "most_common": max(set(values), key=values.count),
                        "count": len(values)
                    }

            except Exception as e:
                self.logger.error(f"Summary calculation failed for {column}: {e}")

        return summary_stats


class StatisticalAnalysisEngine:
    """R-inspired statistical analysis."""

    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.datasets: Dict[str, DataFrame] = {}
        self.models: Dict[str, Any] = {}

    def load_dataset(self, name: str, data: Dict[str, List[Any]]) -> None:
        """Load dataset (R data.frame equivalent)."""
        self.datasets[name] = DataFrame(data)
        self.logger.info(f"Loaded dataset: {name}")

    def descriptive_statistics(self, dataset_name: str, column: str) -> Dict[str, Any]:
        """Compute descriptive statistics."""
        if dataset_name not in self.datasets:
            return {"error": f"Dataset {dataset_name} not found"}

        dataset = self.datasets[dataset_name]
        values = dataset[column]

        if not values:
            return {"error": "Empty column"}

        try:
            if isinstance(values[0], (int, float)):
                stats = {
                    "mean": statistics.mean(values),
                    "median": statistics.median(values),
                    "mode": statistics.mode(values),
                    "std": statistics.stdev(values),
                    "variance": statistics.variance(values),
                    "min": min(values),
                    "max": max(values),
                    "range": max(values) - min(values),
                    "q25": statistics.quantiles(values)[0] if len(values) > 1 else values[0],
                    "q75": statistics.quantiles(values)[2] if len(values) > 3 else values[-1],
                    "count": len(values),
                    "method": "descriptive_statistics"
                }
            else:
                # Categorical data
                from collections import Counter
                counts = Counter(values)
                stats = {
                    "unique_values": len(counts),
                    "most_common": counts.most_common(5),
                    "least_common": counts.most_common()[-5:],
                    "count": len(values),
                    "method": "categorical_statistics"
                }

            return stats

        except Exception as e:
            return {"error": f"Statistics calculation failed: {e}"}

    def linear_regression(self, dataset_name: str, x_column: str, y_column: str) -> Dict[str, Any]:
        """Perform linear regression (R lm equivalent)."""
        if dataset_name not in self.datasets:
            return {"error": f"Dataset {dataset_name} not found"}

        dataset = self.datasets[dataset_name]
        x_values = dataset[x_column]
        y_values = dataset[y_column]

        if len(x_values) != len(y_values):
            return {"error": "X and Y must have same length"}

        try:
            n = len(x_values)
            sum_x = sum(x_values)
            sum_y = sum(y_values)
            sum_xy = sum(x * y for x, y in zip(x_values, y_values))
            sum_x2 = sum(x * x for x in x_values)

            # Calculate slope and intercept
            denominator = n * sum_x2 - sum_x * sum_x
            if denominator == 0:
                return {"error": "Cannot compute regression"}

            slope = (n * sum_xy - sum_x * sum_y) / denominator
            intercept = (sum_y - slope * sum_x) / n

            # Calculate R-squared
            y_mean = sum_y / n
            ss_total = sum((y - y_mean) ** 2 for y in y_values)
            ss_residual = sum((y - (slope * x + intercept)) ** 2 for x, y in zip(x_values, y_values))

            r_squared = 1 - (ss_residual / ss_total) if ss_total != 0 else 0

            return {
                "slope": slope,
                "intercept": intercept,
                "r_squared": r_squared,
                "equation": f"y = {slope:.3f}x + {intercept:.3f}",
                "method": "linear_regression"
            }

        except Exception as e:
            return {"error": f"Regression failed: {e}"}

    def correlation_analysis(self, dataset_name: str, columns: List[str]) -> Dict[str, Any]:
        """Correlation analysis (R cor equivalent)."""
        if dataset_name not in self.datasets:
            return {"error": f"Dataset {dataset_name} not found"}

        dataset = self.datasets[dataset_name]

        try:
            correlation_matrix = {}

            for i, col1 in enumerate(columns):
                correlation_matrix[col1] = {}

                for j, col2 in enumerate(columns):
                    if i <= j:
                        values1 = dataset[col1]
                        values2 = dataset[col2]

                        # Calculate correlation
                        if len(values1) != len(values2):
                            corr = 0
                        else:
                            mean1 = statistics.mean(values1)
                            mean2 = statistics.mean(values2)

                            numerator = sum((x - mean1) * (y - mean2) for x, y in zip(values1, values2))
                            denom1 = math.sqrt(sum((x - mean1) ** 2 for x in values1))
                            denom2 = math.sqrt(sum((y - mean2) ** 2 for y in values2))

                            corr = numerator / (denom1 * denom2) if denom1 != 0 and denom2 != 0 else 0

                        correlation_matrix[col1][col2] = corr
                        if col1 != col2:
                            correlation_matrix[col2][col1] = corr

            return {
                "correlation_matrix": correlation_matrix,
                "columns": columns,
                "method": "pearson_correlation"
            }

        except Exception as e:
            return {"error": f"Correlation analysis failed: {e}"}

    def clustering_analysis(self, dataset_name: str, columns: List[str], n_clusters: int = 3) -> Dict[str, Any]:
        """Clustering analysis (R kmeans equivalent)."""
        if dataset_name not in self.datasets:
            return {"error": f"Dataset {dataset_name} not found"}

        dataset = self.datasets[dataset_name]

        try:
            # Extract data for clustering
            data_points = []
            for i in range(len(dataset[columns[0]])):
                point = [dataset[col][i] for col in columns]
                data_points.append(point)

            # Simple k-means clustering
            centroids, labels = self._kmeans(data_points, n_clusters)

            return {
                "centroids": centroids,
                "labels": labels,
                "n_clusters": n_clusters,
                "columns": columns,
                "method": "kmeans"
            }

        except Exception as e:
            return {"error": f"Clustering failed: {e}"}

    def _kmeans(self, data: List[List[float]], n_clusters: int) -> tuple:
        """Simple k-means clustering."""
        import random

        # Initialize centroids
        centroids = random.sample(data, n_clusters)

        for _ in range(100):  # Max iterations
            # Assign labels
            labels = []
            for point in data:
                distances = [math.sqrt(sum((p - c) ** 2 for p, c in zip(point, centroid)))
                           for centroid in centroids]
                labels.append(distances.index(min(distances)))

            # Update centroids
            new_centroids = []
            for cluster_id in range(n_clusters):
                cluster_points = [data[i] for i, label in enumerate(labels) if label == cluster_id]

                if cluster_points:
                    new_centroid = [sum(dim) / len(cluster_points) for dim in zip(*cluster_points)]
                    new_centroids.append(new_centroid)
                else:
                    new_centroids.append(centroids[cluster_id])

            if new_centroids == centroids:
                break

            centroids = new_centroids

        return centroids, labels


class DataVisualizationEngine:
    """R ggplot2/Octave plotting equivalent."""

    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.plots: Dict[str, Dict[str, Any]] = {}

    def create_scatter_plot(self, x_data: List[float], y_data: List[float],
                          title: str = "Scatter Plot") -> Dict[str, Any]:
        """Create scatter plot."""
        try:
            plot_data = {
                "type": "scatter",
                "x_data": x_data,
                "y_data": y_data,
                "x_label": "X",
                "y_label": "Y",
                "title": title,
                "created_at": time.time()
            }

            plot_id = f"scatter_{hash(str(x_data))}_{hash(str(y_data))}"
            self.plots[plot_id] = plot_data

            return {
                "plot_id": plot_id,
                "plot_type": "scatter",
                "data_points": len(x_data),
                "title": title
            }

        except Exception as e:
            return {"error": f"Scatter plot creation failed: {e}"}

    def create_histogram(self, data: List[float], bins: int = 10,
                        title: str = "Histogram") -> Dict[str, Any]:
        """Create histogram."""
        try:
            # Simple histogram calculation
            min_val, max_val = min(data), max(data)
            bin_width = (max_val - min_val) / bins

            histogram_data = [0] * bins

            for value in data:
                if min_val <= value <= max_val:
                    bin_index = int((value - min_val) / bin_width)
                    if bin_index < bins:
                        histogram_data[bin_index] += 1

            plot_data = {
                "type": "histogram",
                "data": histogram_data,
                "bins": bins,
                "bin_edges": [min_val + i * bin_width for i in range(bins + 1)],
                "title": title,
                "created_at": time.time()
            }

            plot_id = f"histogram_{hash(str(data))}_{bins}"
            self.plots[plot_id] = plot_data

            return {
                "plot_id": plot_id,
                "plot_type": "histogram",
                "bins": bins,
                "data_points": len(data),
                "title": title
            }

        except Exception as e:
            return {"error": f"Histogram creation failed: {e}"}

    def create_box_plot(self, datasets: Dict[str, List[float]],
                       title: str = "Box Plot") -> Dict[str, Any]:
        """Create box plot."""
        try:
            plot_data = {
                "type": "box",
                "datasets": datasets,
                "title": title,
                "created_at": time.time()
            }

            plot_id = f"box_{hash(str(datasets))}"
            self.plots[plot_id] = plot_data

            return {
                "plot_id": plot_id,
                "plot_type": "box",
                "datasets": list(datasets.keys()),
                "title": title
            }

        except Exception as e:
            return {"error": f"Box plot creation failed: {e}"}


class CADDataAnalyzer:
    """R-inspired data analysis for CAD."""

    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.stats_engine = StatisticalAnalysisEngine()
        self.visualization = DataVisualizationEngine()
        self.analysis_results: Dict[str, Any] = {}

    def analyze_mesh_data(self, mesh_data: Dict[str, Any]) -> Dict[str, Any]:
        """Analyze mesh data statistically."""
        analysis = {
            "mesh_id": mesh_data.get("id", "unknown"),
            "analysis_timestamp": time.time(),
            "statistical_analysis": {},
            "visualizations": [],
            "recommendations": []
        }

        try:
            vertices = mesh_data.get("vertices", [])
            faces = mesh_data.get("faces", [])

            if vertices:
                # Load vertex data
                vertex_data = {
                    "x": [v[0] for v in vertices],
                    "y": [v[1] for v in vertices],
                    "z": [v[2] for v in vertices]
                }

                self.stats_engine.load_dataset("vertices", vertex_data)

                # Analyze each coordinate
                for coord in ["x", "y", "z"]:
                    stats = self.stats_engine.descriptive_statistics("vertices", coord)
                    analysis["statistical_analysis"][coord] = stats

                # Create visualizations
                scatter_xz = self.visualization.create_scatter_plot(vertex_data["x"], vertex_data["z"])
                analysis["visualizations"].append(scatter_xz)

                histogram_z = self.visualization.create_histogram(vertex_data["z"])
                analysis["visualizations"].append(histogram_z)

            if faces:
                # Analyze face data
                face_data = {
                    "face_size": [len(face) for face in faces],
                    "face_area": [self._calculate_face_area(vertices, face) for face in faces]
                }

                self.stats_engine.load_dataset("faces", face_data)

                face_stats = self.stats_engine.descriptive_statistics("faces", "face_area")
                analysis["statistical_analysis"]["faces"] = face_stats

                # Recommendations
                if face_stats.get("mean", 0) > 1.0:
                    analysis["recommendations"].append("Consider mesh decimation for large faces")

                if len(vertices) > 100000:
                    analysis["recommendations"].append("Large mesh detected - consider optimization")

        except Exception as e:
            self.logger.error(f"Mesh analysis failed: {e}")
            analysis["error"] = str(e)

        return analysis

    def _calculate_face_area(self, vertices: List[List[float]], face: List[int]) -> float:
        """Calculate face area."""
        if len(face) < 3:
            return 0.0

        # Get face vertices
        face_vertices = [vertices[i] for i in face[:3]]

        # Calculate area using cross product
        v1, v2, v3 = face_vertices

        edge1 = [v2[0] - v1[0], v2[1] - v1[1], v2[2] - v1[2]]
        edge2 = [v3[0] - v1[0], v3[1] - v1[1], v3[2] - v1[2]]

        cross = [
            edge1[1] * edge2[2] - edge1[2] * edge2[1],
            edge1[2] * edge2[0] - edge1[0] * edge2[2],
            edge1[0] * edge2[1] - edge1[1] * edge2[0]
        ]

        return math.sqrt(sum(x*x for x in cross)) / 2.0

    def perform_correlation_analysis(self, dataset_name: str, columns: List[str]) -> Dict[str, Any]:
        """Perform correlation analysis."""
        return self.stats_engine.correlation_analysis(dataset_name, columns)

    def create_visualization_report(self, analysis_results: Dict[str, Any]) -> Dict[str, Any]:
        """Create visualization report."""
        return {
            "analysis_id": analysis_results.get("mesh_id", "unknown"),
            "plots_created": len(analysis_results.get("visualizations", [])),
            "statistical_insights": analysis_results.get("statistical_analysis", {}),
            "recommendations": analysis_results.get("recommendations", []),
            "visualization_timestamp": time.time()
        }


# Factory functions
def create_statistical_engine() -> StatisticalAnalysisEngine:
    """Create statistical analysis engine."""
    return StatisticalAnalysisEngine()


def create_visualization_engine() -> DataVisualizationEngine:
    """Create data visualization engine."""
    return DataVisualizationEngine()


def create_cad_data_analyzer() -> CADDataAnalyzer:
    """Create CAD data analyzer."""
    return CADDataAnalyzer()
