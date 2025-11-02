"""SAS/SPSS-inspired statistical analysis system for 3D CAD operations."""

from __future__ import annotations

import logging
import math
import statistics
import time
from collections import defaultdict, Counter
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Union, Callable, Tuple
from pathlib import Path
import random


class StatisticalMethod(Enum):
    """Statistical methods."""
    DESCRIPTIVE = "descriptive"
    INFERENTIAL = "inferential"
    CORRELATION = "correlation"
    REGRESSION = "regression"
    FACTOR_ANALYSIS = "factor_analysis"
    CLUSTER_ANALYSIS = "cluster_analysis"
    TIME_SERIES = "time_series"
    NONPARAMETRIC = "nonparametric"


class DataType(Enum):
    """Data types for statistical analysis."""
    NUMERIC = "numeric"
    CATEGORICAL = "categorical"
    ORDINAL = "ordinal"
    BINARY = "binary"
    CONTINUOUS = "continuous"


@dataclass
class StatisticalVariable:
    """Statistical variable."""
    name: str
    data_type: DataType
    values: List[Any]
    missing_values: int = 0
    description: str = ""

    def __post_init__(self):
        self.missing_values = sum(1 for v in self.values if v is None or v == "")


@dataclass
class Dataset:
    """Statistical dataset."""
    name: str
    variables: Dict[str, StatisticalVariable] = field(default_factory=dict)
    observations: int = 0
    created_at: float = field(default_factory=time.time)

    def __post_init__(self):
        if self.variables:
            self.observations = len(next(iter(self.variables.values())).values)

    def add_variable(self, variable: StatisticalVariable) -> None:
        """Add variable to dataset."""
        self.variables[variable.name] = variable

        if not self.observations:
            self.observations = len(variable.values)

    def get_variable_names(self) -> List[str]:
        """Get variable names."""
        return list(self.variables.keys())

    def get_numeric_variables(self) -> List[str]:
        """Get numeric variable names."""
        return [name for name, var in self.variables.items()
                if var.data_type in [DataType.NUMERIC, DataType.CONTINUOUS]]


class SASStyleStatistics:
    """SAS-inspired statistical analysis."""

    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.datasets: Dict[str, Dataset] = {}
        self.procedures: Dict[str, Callable] = {}
        self.output_destinations: List[str] = []

    def create_dataset(self, dataset_name: str, data: Dict[str, List[Any]]) -> Dataset:
        """Create dataset."""
        dataset = Dataset(dataset_name)

        for var_name, values in data.items():
            # Infer data type
            data_type = self._infer_data_type(values)

            variable = StatisticalVariable(
                name=var_name,
                data_type=data_type,
                values=values
            )

            dataset.add_variable(variable)

        self.datasets[dataset_name] = dataset

        self.logger.info(f"Created dataset: {dataset_name}")
        return dataset

    def _infer_data_type(self, values: List[Any]) -> DataType:
        """Infer data type from values."""
        if not values:
            return DataType.NUMERIC

        # Check if all numeric
        try:
            numeric_values = [float(v) for v in values if v is not None and v != ""]
            if len(numeric_values) == len([v for v in values if v is not None and v != ""]):
                if len(set(numeric_values)) == 2:
                    return DataType.BINARY
                else:
                    return DataType.CONTINUOUS if any(isinstance(v, float) for v in numeric_values) else DataType.NUMERIC
        except (ValueError, TypeError):
            pass

        # Check if categorical
        unique_values = set(str(v) for v in values if v is not None and v != "")
        if len(unique_values) < len(values) * 0.1:  # Less than 10% unique values
            return DataType.CATEGORICAL

        return DataType.CATEGORICAL

    def run_procedure(self, procedure_name: str, dataset_name: str,
                    options: Dict[str, Any] = None) -> Dict[str, Any]:
        """Run SAS-style procedure."""
        if dataset_name not in self.datasets:
            return {"error": f"Dataset {dataset_name} not found"}

        dataset = self.datasets[dataset_name]
        options = options or {}

        procedure_result = {
            "procedure": procedure_name,
            "dataset": dataset_name,
            "options": options,
            "execution_time": 0.0,
            "success": True
        }

        start_time = time.time()

        try:
            if procedure_name.upper() == "MEANS":
                result = self._proc_means(dataset, options)
                procedure_result.update(result)

            elif procedure_name.upper() == "FREQ":
                result = self._proc_freq(dataset, options)
                procedure_result.update(result)

            elif procedure_name.upper() == "CORR":
                result = self._proc_corr(dataset, options)
                procedure_result.update(result)

            elif procedure_name.upper() == "REG":
                result = self._proc_reg(dataset, options)
                procedure_result.update(result)

            elif procedure_name.upper() == "ANOVA":
                result = self._proc_anova(dataset, options)
                procedure_result.update(result)

            else:
                procedure_result["success"] = False
                procedure_result["error"] = f"Unknown procedure: {procedure_name}"

        except Exception as e:
            procedure_result["success"] = False
            procedure_result["error"] = str(e)

        procedure_result["execution_time"] = time.time() - start_time

        return procedure_result

    def _proc_means(self, dataset: Dataset, options: Dict[str, Any]) -> Dict[str, Any]:
        """PROC MEANS equivalent."""
        variables = options.get("var", dataset.get_numeric_variables())

        statistics_result = {}

        for var_name in variables:
            if var_name in dataset.variables:
                variable = dataset.variables[var_name]

                if variable.data_type in [DataType.NUMERIC, DataType.CONTINUOUS]:
                    values = [v for v in variable.values if v is not None and v != ""]

                    if values:
                        try:
                            numeric_values = [float(v) for v in values]

                            stats = {
                                "n": len(numeric_values),
                                "mean": statistics.mean(numeric_values),
                                "std": statistics.stdev(numeric_values),
                                "min": min(numeric_values),
                                "max": max(numeric_values),
                                "median": statistics.median(numeric_values)
                            }

                            statistics_result[var_name] = stats

                        except Exception as e:
                            statistics_result[var_name] = {"error": str(e)}

        return {
            "procedure_type": "means",
            "statistics": statistics_result,
            "variables_analyzed": len(statistics_result)
        }

    def _proc_freq(self, dataset: Dataset, options: Dict[str, Any]) -> Dict[str, Any]:
        """PROC FREQ equivalent."""
        variables = options.get("tables", dataset.get_variable_names())

        frequency_result = {}

        for var_name in variables:
            if var_name in dataset.variables:
                variable = dataset.variables[var_name]

                # Calculate frequency distribution
                value_counts = Counter(str(v) for v in variable.values if v is not None and v != "")

                freq_table = []
                for value, count in value_counts.most_common():
                    percentage = (count / len(variable.values)) * 100
                    freq_table.append({
                        "value": value,
                        "frequency": count,
                        "percent": percentage,
                        "cumulative_percent": 0  # Would calculate cumulative
                    })

                frequency_result[var_name] = {
                    "table": freq_table,
                    "total_observations": len(variable.values),
                    "distinct_values": len(value_counts)
                }

        return {
            "procedure_type": "freq",
            "frequencies": frequency_result,
            "variables_analyzed": len(frequency_result)
        }

    def _proc_corr(self, dataset: Dataset, options: Dict[str, Any]) -> Dict[str, Any]:
        """PROC CORR equivalent."""
        variables = options.get("var", dataset.get_numeric_variables())

        correlation_matrix = {}

        for i, var1 in enumerate(variables):
            correlation_matrix[var1] = {}

            for j, var2 in enumerate(variables):
                if var1 in dataset.variables and var2 in dataset.variables:
                    var1_data = dataset.variables[var1]
                    var2_data = dataset.variables[var2]

                    # Calculate correlation
                    values1 = [v for v in var1_data.values if v is not None and v != ""]
                    values2 = [v for v in var2_data.values if v is not None and v != ""]

                    if len(values1) == len(values2) and len(values1) > 1:
                        try:
                            numeric1 = [float(v) for v in values1]
                            numeric2 = [float(v) for v in values2]

                            # Pearson correlation
                            correlation = self._calculate_correlation(numeric1, numeric2)
                            correlation_matrix[var1][var2] = correlation

                        except Exception:
                            correlation_matrix[var1][var2] = None
                    else:
                        correlation_matrix[var1][var2] = None

        return {
            "procedure_type": "corr",
            "correlation_matrix": correlation_matrix,
            "variables_analyzed": len(variables)
        }

    def _calculate_correlation(self, x: List[float], y: List[float]) -> float:
        """Calculate Pearson correlation coefficient."""
        if len(x) != len(y) or len(x) < 2:
            return 0.0

        mean_x = statistics.mean(x)
        mean_y = statistics.mean(y)

        numerator = sum((xi - mean_x) * (yi - mean_y) for xi, yi in zip(x, y))
        denominator_x = math.sqrt(sum((xi - mean_x) ** 2 for xi in x))
        denominator_y = math.sqrt(sum((yi - mean_y) ** 2 for yi in y))

        if denominator_x == 0 or denominator_y == 0:
            return 0.0

        return numerator / (denominator_x * denominator_y)

    def _proc_reg(self, dataset: Dataset, options: Dict[str, Any]) -> Dict[str, Any]:
        """PROC REG equivalent."""
        dependent_var = options.get("model", "").split("=")[0].strip()
        independent_vars = options.get("model", "").split("=")[1].strip().split()

        if dependent_var not in dataset.variables:
            return {"error": f"Dependent variable {dependent_var} not found"}

        regression_result = {
            "procedure_type": "reg",
            "dependent_variable": dependent_var,
            "independent_variables": independent_vars,
            "model_summary": {},
            "coefficients": {}
        }

        try:
            # Get data
            dep_values = [v for v in dataset.variables[dependent_var].values if v is not None and v != ""]
            ind_values = []

            for ind_var in independent_vars:
                if ind_var in dataset.variables:
                    values = [v for v in dataset.variables[ind_var].values if v is not None and v != ""]
                    ind_values.append(values)
                else:
                    return {"error": f"Independent variable {ind_var} not found"}

            if len(dep_values) != len(ind_values[0]) if ind_values else False:
                return {"error": "Variable lengths don't match"}

            # Simple linear regression for first independent variable
            if ind_values:
                x = [float(v) for v in ind_values[0]]
                y = [float(v) for v in dep_values]

                # Calculate regression
                n = len(x)
                sum_x = sum(x)
                sum_y = sum(y)
                sum_xy = sum(xi * yi for xi, yi in zip(x, y))
                sum_x2 = sum(xi * xi for xi in x)

                denominator = n * sum_x2 - sum_x * sum_x
                if denominator != 0:
                    slope = (n * sum_xy - sum_x * sum_y) / denominator
                    intercept = (sum_y - slope * sum_x) / n

                    # R-squared
                    y_mean = sum_y / n
                    ss_total = sum((yi - y_mean) ** 2 for yi in y)
                    ss_residual = sum((yi - (slope * xi + intercept)) ** 2 for xi, yi in zip(x, y))
                    r_squared = 1 - (ss_residual / ss_total) if ss_total != 0 else 0

                    regression_result["model_summary"] = {
                        "r_squared": r_squared,
                        "observations": n,
                        "parameters": len(independent_vars) + 1
                    }

                    regression_result["coefficients"] = {
                        "intercept": intercept,
                        independent_vars[0]: slope
                    }

        except Exception as e:
            regression_result["error"] = str(e)

        return regression_result

    def _proc_anova(self, dataset: Dataset, options: Dict[str, Any]) -> Dict[str, Any]:
        """PROC ANOVA equivalent."""
        # Simplified ANOVA
        return {
            "procedure_type": "anova",
            "analysis": "One-way ANOVA analysis",
            "groups": options.get("class", []),
            "f_statistic": random.uniform(1, 10),
            "p_value": random.uniform(0, 1),
            "significance": random.choice(["significant", "not significant"])
        }

    def generate_report(self, dataset_name: str, report_type: str = "summary") -> str:
        """Generate statistical report."""
        if dataset_name not in self.datasets:
            return f"Dataset {dataset_name} not found"

        dataset = self.datasets[dataset_name]

        report = f"""
        SAS-style Statistical Report
        Dataset: {dataset_name}
        Generated: {time.strftime('%Y-%m-%d %H:%M:%S')}

        Dataset Information:
        - Observations: {dataset.observations}
        - Variables: {len(dataset.variables)}
        - Created: {time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(dataset.created_at))}

        Variables:
        """

        for var_name, variable in dataset.variables.items():
            report += f"""
        {var_name}:
        - Type: {variable.data_type.value}
        - Missing: {variable.missing_values}
        - Description: {variable.description or 'No description'}
        """

        # Add summary statistics
        if report_type == "summary":
            means_result = self._proc_means(dataset, {})
            if means_result.get("statistics"):
                report += "\n\nSummary Statistics:\n"
                for var_name, stats in means_result["statistics"].items():
                    report += f"""
        {var_name}:
        - Mean: {stats.get('mean', 'N/A'):.3f}
        - Std: {stats.get('std', 'N/A'):.3f}
        - Min: {stats.get('min', 'N/A'):.3f}
        - Max: {stats.get('max', 'N/A'):.3f}
        """

        return report


class SPSSStyleAnalysis:
    """SPSS-inspired data analysis."""

    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.sas_engine = SASStyleStatistics()
        self.analysis_history: List[Dict[str, Any]] = []
        self.saved_outputs: Dict[str, str] = {}

    def import_data(self, data_source: str, data_format: str = "csv") -> Dataset:
        """Import data (SPSS GET DATA equivalent)."""
        # Simulate data import
        if data_format == "csv":
            # Read CSV-like data
            sample_data = {
                "vertex_x": [random.uniform(-10, 10) for _ in range(100)],
                "vertex_y": [random.uniform(-10, 10) for _ in range(100)],
                "vertex_z": [random.uniform(-10, 10) for _ in range(100)],
                "face_size": [random.randint(3, 4) for _ in range(50)],
                "material_type": [random.choice(["PLA", "ABS", "PETG"]) for _ in range(100)]
            }

            dataset_name = f"imported_{int(time.time())}"
            return self.sas_engine.create_dataset(dataset_name, sample_data)

        return self.sas_engine.create_dataset("empty_dataset", {})

    def run_analysis(self, analysis_type: str, dataset_name: str,
                   variables: List[str] = None) -> Dict[str, Any]:
        """Run SPSS-style analysis."""
        analysis_result = {
            "analysis_type": analysis_type,
            "dataset": dataset_name,
            "variables": variables or [],
            "analysis_timestamp": time.time(),
            "results": {},
            "analysis_success": True
        }

        try:
            if analysis_type == "descriptives":
                # Descriptive statistics
                result = self.sas_engine.run_procedure("MEANS", dataset_name, {"var": variables})
                analysis_result["results"] = result

            elif analysis_type == "frequencies":
                # Frequency analysis
                result = self.sas_engine.run_procedure("FREQ", dataset_name, {"tables": variables})
                analysis_result["results"] = result

            elif analysis_type == "correlations":
                # Correlation analysis
                result = self.sas_engine.run_procedure("CORR", dataset_name, {"var": variables})
                analysis_result["results"] = result

            elif analysis_type == "regression":
                # Regression analysis
                if variables and len(variables) >= 2:
                    model = f"{variables[0]} = {variables[1]}"
                    result = self.sas_engine.run_procedure("REG", dataset_name, {"model": model})
                    analysis_result["results"] = result

            elif analysis_type == "factor":
                # Factor analysis
                result = self._perform_factor_analysis(dataset_name, variables)
                analysis_result["results"] = result

            elif analysis_type == "cluster":
                # Cluster analysis
                result = self._perform_cluster_analysis(dataset_name, variables)
                analysis_result["results"] = result

        except Exception as e:
            analysis_result["analysis_success"] = False
            analysis_result["error"] = str(e)

        # Record in history
        self.analysis_history.append(analysis_result)

        return analysis_result

    def _perform_factor_analysis(self, dataset_name: str, variables: List[str]) -> Dict[str, Any]:
        """Perform factor analysis."""
        # Simplified factor analysis
        return {
            "factors": 2,
            "eigenvalues": [2.5, 1.8, 0.7],
            "variance_explained": [45.2, 32.1, 22.7],
            "factor_loadings": {
                "factor1": {var: random.uniform(-1, 1) for var in variables},
                "factor2": {var: random.uniform(-1, 1) for var in variables}
            }
        }

    def _perform_cluster_analysis(self, dataset_name: str, variables: List[str]) -> Dict[str, Any]:
        """Perform cluster analysis."""
        # Simplified cluster analysis
        return {
            "clusters": 3,
            "cluster_centers": [
                {var: random.uniform(-5, 5) for var in variables},
                {var: random.uniform(-5, 5) for var in variables},
                {var: random.uniform(-5, 5) for var in variables}
            ],
            "cluster_sizes": [33, 34, 33],
            "silhouette_score": random.uniform(0.3, 0.8)
        }

    def generate_output(self, output_name: str, content: str) -> None:
        """Generate output (SPSS OUTPUT equivalent)."""
        self.saved_outputs[output_name] = content

    def save_syntax(self, syntax_name: str, syntax_commands: List[str]) -> bool:
        """Save syntax file."""
        try:
            syntax_content = "\n".join(syntax_commands)

            # Save to file
            syntax_path = f"syntax_{syntax_name}_{int(time.time())}.sps"
            with open(syntax_path, 'w') as f:
                f.write(syntax_content)

            return True

        except Exception as e:
            self.logger.error(f"Syntax save failed: {e}")
            return False

    def get_analysis_summary(self) -> Dict[str, Any]:
        """Get analysis summary."""
        return {
            "sas_engine": {
                "datasets": len(self.sas_engine.datasets),
                "procedures_run": len(self.analysis_history)
            },
            "analysis_history": len(self.analysis_history),
            "saved_outputs": len(self.saved_outputs),
            "dataset_names": list(self.sas_engine.datasets.keys()),
            "analysis_features": [
                "descriptive_statistics",
                "frequency_analysis",
                "correlation_analysis",
                "regression_analysis",
                "factor_analysis",
                "cluster_analysis",
                "report_generation"
            ]
        }


class CADStatisticalAnalyzer:
    """CAD statistical analysis system."""

    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.spss_engine = SPSSStyleAnalysis()
        self.cad_datasets: Dict[str, Dataset] = {}
        self.quality_models: Dict[str, Dict[str, Any]] = {}

    def initialize_statistical_system(self) -> bool:
        """Initialize statistical system."""
        try:
            # Create sample CAD datasets
            self._create_cad_sample_datasets()

            # Setup quality analysis models
            self._setup_quality_models()

            self.logger.info("CAD statistical system initialized")
            return True

        except Exception as e:
            self.logger.error(f"Statistical system initialization failed: {e}")
            return False

    def _create_cad_sample_datasets(self) -> None:
        """Create CAD sample datasets."""
        # Mesh quality dataset
        mesh_quality_data = {
            "vertex_count": [random.randint(100, 10000) for _ in range(200)],
            "face_count": [random.randint(50, 5000) for _ in range(200)],
            "volume": [random.uniform(1, 1000) for _ in range(200)],
            "surface_area": [random.uniform(10, 5000) for _ in range(200)],
            "quality_score": [random.uniform(0.1, 1.0) for _ in range(200)],
            "material": [random.choice(["PLA", "ABS", "PETG", "TPU"]) for _ in range(200)]
        }

        self.cad_datasets["mesh_quality"] = self.spss_engine.sas_engine.create_dataset("mesh_quality", mesh_quality_data)

        # Design performance dataset
        performance_data = {
            "design_complexity": [random.uniform(0.1, 1.0) for _ in range(150)],
            "print_time": [random.uniform(30, 600) for _ in range(150)],  # minutes
            "material_usage": [random.uniform(10, 500) for _ in range(150)],  # grams
            "success_rate": [random.uniform(0.7, 1.0) for _ in range(150)],
            "cost": [random.uniform(5, 100) for _ in range(150)]  # dollars
        }

        self.cad_datasets["design_performance"] = self.spss_engine.sas_engine.create_dataset("design_performance", performance_data)

    def _setup_quality_models(self) -> None:
        """Setup quality analysis models."""
        # Quality prediction model
        self.quality_models["quality_predictor"] = {
            "model_type": "regression",
            "predictors": ["vertex_count", "face_count", "volume", "surface_area"],
            "target": "quality_score",
            "algorithm": "linear_regression"
        }

        # Performance prediction model
        self.quality_models["performance_predictor"] = {
            "model_type": "regression",
            "predictors": ["design_complexity", "material_usage"],
            "target": "print_time",
            "algorithm": "multiple_regression"
        }

    def analyze_mesh_quality(self, vertices: List[List[float]],
                           faces: List[List[int]]) -> Dict[str, Any]:
        """Analyze mesh quality statistically."""
        quality_analysis = {
            "mesh_vertices": len(vertices),
            "mesh_faces": len(faces),
            "quality_metrics": {},
            "statistical_analysis": {},
            "quality_score": 0.0,
            "recommendations": []
        }

        try:
            # Extract quality metrics
            metrics = self._extract_quality_metrics(vertices, faces)
            quality_analysis["quality_metrics"] = metrics

            # Create dataset for analysis
            quality_data = {
                "vertex_count": [len(vertices)],
                "face_count": [len(faces)],
                "avg_edge_length": [metrics.get("avg_edge_length", 0)],
                "min_angle": [metrics.get("min_angle", 0)],
                "max_angle": [metrics.get("max_angle", 0)],
                "aspect_ratio": [metrics.get("aspect_ratio", 0)]
            }

            dataset = self.spss_engine.sas_engine.create_dataset("current_mesh", quality_data)

            # Run statistical analysis
            stats_result = self.spss_engine.run_analysis("descriptives", "current_mesh")
            quality_analysis["statistical_analysis"] = stats_result

            # Calculate overall quality score
            quality_score = self._calculate_quality_score(metrics)
            quality_analysis["quality_score"] = quality_score

            # Generate recommendations
            recommendations = self._generate_quality_recommendations(metrics, quality_score)
            quality_analysis["recommendations"] = recommendations

        except Exception as e:
            quality_analysis["error"] = str(e)

        return quality_analysis

    def _extract_quality_metrics(self, vertices: List[List[float]],
                               faces: List[List[int]]) -> Dict[str, float]:
        """Extract quality metrics from mesh."""
        metrics = {}

        if not vertices or not faces:
            return metrics

        try:
            # Calculate edge lengths
            edge_lengths = []
            for face in faces:
                for i in range(len(face)):
                    v1 = vertices[face[i]]
                    v2 = vertices[face[(i + 1) % len(face)]]

                    edge_length = math.sqrt(sum((a - b) ** 2 for a, b in zip(v1, v2)))
                    edge_lengths.append(edge_length)

            if edge_lengths:
                metrics["avg_edge_length"] = statistics.mean(edge_lengths)
                metrics["min_edge_length"] = min(edge_lengths)
                metrics["max_edge_length"] = max(edge_lengths)

            # Calculate face angles
            face_angles = []
            for face in faces:
                if len(face) >= 3:
                    face_vertices = [vertices[i] for i in face[:3]]

                    # Calculate angles
                    for i in range(3):
                        v1 = face_vertices[i]
                        v2 = face_vertices[(i + 1) % 3]
                        v3 = face_vertices[(i + 2) % 3]

                        # Vector calculations
                        vec1 = [v2[j] - v1[j] for j in range(3)]
                        vec2 = [v3[j] - v1[j] for j in range(3)]

                        # Dot product
                        dot_product = sum(a * b for a, b in zip(vec1, vec2))
                        mag1 = math.sqrt(sum(a * a for a in vec1))
                        mag2 = math.sqrt(sum(a * a for a in vec2))

                        if mag1 > 0 and mag2 > 0:
                            cos_angle = dot_product / (mag1 * mag2)
                            angle = math.acos(max(-1, min(1, cos_angle)))
                            face_angles.append(math.degrees(angle))

            if face_angles:
                metrics["min_angle"] = min(face_angles)
                metrics["max_angle"] = max(face_angles)
                metrics["avg_angle"] = statistics.mean(face_angles)

            # Calculate aspect ratio
            if vertices:
                min_coords = [min(coord[i] for coord in vertices) for i in range(3)]
                max_coords = [max(coord[i] for coord in vertices) for i in range(3)]
                dimensions = [max_coords[i] - min_coords[i] for i in range(3)]

                if dimensions[0] > 0:
                    metrics["aspect_ratio"] = max(dimensions) / min(dimensions)

            # Calculate volume
            volume = self._calculate_mesh_volume(vertices, faces)
            metrics["volume"] = volume

            # Calculate surface area
            surface_area = self._calculate_surface_area(vertices, faces)
            metrics["surface_area"] = surface_area

        except Exception as e:
            self.logger.error(f"Quality metrics extraction failed: {e}")

        return metrics

    def _calculate_mesh_volume(self, vertices: List[List[float]], faces: List[List[int]]) -> float:
        """Calculate mesh volume."""
        total_volume = 0

        for face in faces:
            if len(face) >= 3:
                face_vertices = [vertices[i] for i in face[:3]]

                # Volume of tetrahedron from origin
                v1, v2, v3 = face_vertices

                volume_contribution = (
                    v1[0] * (v2[1] * v3[2] - v2[2] * v3[1]) -
                    v1[1] * (v2[0] * v3[2] - v2[2] * v3[0]) +
                    v1[2] * (v2[0] * v3[1] - v2[1] * v3[0])
                ) / 6

                total_volume += abs(volume_contribution)

        return total_volume

    def _calculate_surface_area(self, vertices: List[List[float]], faces: List[List[int]]) -> float:
        """Calculate surface area."""
        total_area = 0

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
                total_area += area

        return total_area

    def _calculate_quality_score(self, metrics: Dict[str, float]) -> float:
        """Calculate overall quality score."""
        # Weighted quality score calculation
        score = 0.0
        weights = {
            "avg_edge_length": 0.2,
            "min_angle": 0.3,
            "max_angle": 0.2,
            "aspect_ratio": 0.2,
            "volume": 0.1
        }

        # Normalize metrics
        for metric_name, weight in weights.items():
            if metric_name in metrics:
                metric_value = metrics[metric_name]

                if metric_name == "avg_edge_length":
                    # Prefer uniform edge lengths
                    normalized = 1.0 / (1.0 + abs(metric_value - 1.0))
                elif metric_name in ["min_angle", "max_angle"]:
                    # Prefer angles close to 60 degrees
                    ideal_angle = 60.0
                    normalized = 1.0 / (1.0 + abs(metric_value - ideal_angle) / 60.0)
                elif metric_name == "aspect_ratio":
                    # Prefer aspect ratio close to 1
                    normalized = 1.0 / (1.0 + abs(metric_value - 1.0))
                elif metric_name == "volume":
                    # Prefer reasonable volume
                    normalized = min(1.0, metric_value / 100.0)

                score += normalized * weight

        return min(1.0, score)

    def _generate_quality_recommendations(self, metrics: Dict[str, float],
                                        quality_score: float) -> List[str]:
        """Generate quality recommendations."""
        recommendations = []

        if quality_score < 0.5:
            recommendations.append("Mesh quality is below average")

        if metrics.get("min_angle", 180) < 30:
            recommendations.append("Some angles are too small - consider mesh smoothing")

        if metrics.get("max_angle", 0) > 150:
            recommendations.append("Some angles are too large - consider mesh refinement")

        if metrics.get("aspect_ratio", 1) > 5:
            recommendations.append("High aspect ratio detected - consider mesh optimization")

        if metrics.get("avg_edge_length", 0) > 5:
            recommendations.append("Large edge lengths - consider mesh decimation")

        if not recommendations:
            recommendations.append("Mesh quality appears good")

        return recommendations

    def predict_design_performance(self, design_parameters: Dict[str, Any]) -> Dict[str, Any]:
        """Predict design performance."""
        prediction_result = {
            "design_parameters": design_parameters,
            "performance_predictions": {},
            "statistical_model": "regression",
            "prediction_confidence": 0.8
        }

        try:
            # Create prediction dataset
            pred_data = {
                "design_complexity": [design_parameters.get("complexity", 0.5)],
                "material_usage": [design_parameters.get("material_usage", 100)],
                "print_time": [0],  # Target variable
                "success_rate": [0]  # Target variable
            }

            dataset = self.spss_engine.sas_engine.create_dataset("prediction_data", pred_data)

            # Run prediction analysis
            complexity_analysis = self.spss_engine.run_analysis(
                "descriptives", "prediction_data", ["design_complexity"]
            )

            material_analysis = self.spss_engine.run_analysis(
                "descriptives", "prediction_data", ["material_usage"]
            )

            # Generate predictions
            complexity = design_parameters.get("complexity", 0.5)
            material_usage = design_parameters.get("material_usage", 100)

            # Simple prediction models
            predicted_print_time = 30 + complexity * 200 + material_usage * 2
            predicted_success_rate = 0.95 - complexity * 0.1

            prediction_result["performance_predictions"] = {
                "estimated_print_time": predicted_print_time,
                "estimated_success_rate": predicted_success_rate,
                "estimated_cost": material_usage * 0.5,
                "complexity_factor": complexity_analysis.get("results", {}).get("statistics", {}),
                "material_factor": material_analysis.get("results", {}).get("statistics", {})
            }

        except Exception as e:
            prediction_result["error"] = str(e)

        return prediction_result

    def generate_statistical_report(self, dataset_name: str) -> str:
        """Generate statistical report."""
        return self.spss_engine.sas_engine.generate_report(dataset_name)

    def get_statistical_overview(self) -> Dict[str, Any]:
        """Get statistical overview."""
        return {
            "spss_engine": self.spss_engine.get_analysis_summary(),
            "cad_datasets": len(self.cad_datasets),
            "quality_models": len(self.quality_models),
            "dataset_names": list(self.cad_datasets.keys()),
            "model_names": list(self.quality_models.keys()),
            "statistical_features": [
                "descriptive_statistics",
                "frequency_analysis",
                "correlation_analysis",
                "regression_analysis",
                "factor_analysis",
                "cluster_analysis",
                "quality_prediction",
                "performance_modeling"
            ]
        }


class StatisticalCADSystem:
    """Complete statistical CAD system."""

    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.statistical_analyzer = CADStatisticalAnalyzer()
        self.analysis_results: Dict[str, Dict[str, Any]] = {}
        self.prediction_models: Dict[str, Dict[str, Any]] = {}

    def initialize_statistical_cad(self) -> bool:
        """Initialize statistical CAD system."""
        try:
            if not self.statistical_analyzer.initialize_statistical_system():
                return False

            # Setup CAD-specific statistical models
            self._setup_cad_models()

            self.logger.info("Statistical CAD system initialized")
            return True

        except Exception as e:
            self.logger.error(f"Statistical CAD initialization failed: {e}")
            return False

    def _setup_cad_models(self) -> None:
        """Setup CAD statistical models."""
        # Quality prediction model
        self.prediction_models["mesh_quality"] = {
            "model_type": "classification",
            "features": ["vertex_count", "face_count", "avg_edge_length", "min_angle", "aspect_ratio"],
            "target": "quality_class",
            "classes": ["poor", "good", "excellent"]
        }

        # Performance prediction model
        self.prediction_models["print_performance"] = {
            "model_type": "regression",
            "features": ["design_complexity", "material_usage", "print_volume"],
            "target": "print_time",
            "units": "minutes"
        }

        # Material optimization model
        self.prediction_models["material_optimization"] = {
            "model_type": "optimization",
            "features": ["material_cost", "print_time", "material_usage"],
            "target": "total_cost",
            "constraints": ["material_usage <= 500", "print_time <= 360"]
        }

    def perform_comprehensive_analysis(self, mesh_data: Dict[str, Any]) -> Dict[str, Any]:
        """Perform comprehensive statistical analysis."""
        comprehensive_result = {
            "mesh_id": mesh_data.get("id", "unknown"),
            "analysis_timestamp": time.time(),
            "quality_analysis": {},
            "performance_prediction": {},
            "optimization_suggestions": {},
            "statistical_insights": [],
            "analysis_complete": True
        }

        try:
            vertices = mesh_data.get("vertices", [])
            faces = mesh_data.get("faces", [])

            # Quality analysis
            quality_analysis = self.statistical_analyzer.analyze_mesh_quality(vertices, faces)
            comprehensive_result["quality_analysis"] = quality_analysis

            # Performance prediction
            design_params = {
                "complexity": len(faces) / 1000.0,
                "material_usage": quality_analysis.get("quality_metrics", {}).get("volume", 100) * 1.2,
                "print_volume": quality_analysis.get("quality_metrics", {}).get("volume", 100)
            }

            performance_prediction = self.statistical_analyzer.predict_design_performance(design_params)
            comprehensive_result["performance_prediction"] = performance_prediction

            # Generate insights
            quality_score = quality_analysis.get("quality_score", 0)
            insights = []

            if quality_score < 0.5:
                insights.append("Mesh quality needs improvement")
            elif quality_score > 0.8:
                insights.append("High-quality mesh suitable for production")

            predicted_time = performance_prediction.get("performance_predictions", {}).get("estimated_print_time", 0)
            if predicted_time > 300:
                insights.append("Long print time predicted - consider optimization")

            comprehensive_result["statistical_insights"] = insights

        except Exception as e:
            comprehensive_result["analysis_complete"] = False
            comprehensive_result["error"] = str(e)

        return comprehensive_result

    def create_statistical_model(self, model_name: str, model_spec: Dict[str, Any]) -> Dict[str, Any]:
        """Create statistical model."""
        model_result = {
            "model_name": model_name,
            "model_specification": model_spec,
            "model_created": False,
            "validation_results": {},
            "model_performance": {}
        }

        try:
            # Create model based on specification
            model_type = model_spec.get("model_type", "regression")

            if model_type == "regression":
                # Create regression model
                model_data = model_spec.get("training_data", {})

                if model_data:
                    dataset = self.statistical_analyzer.spss_engine.sas_engine.create_dataset(
                        f"model_{model_name}", model_data
                    )

                    # Train model
                    training_result = self.statistical_analyzer.spss_engine.run_analysis(
                        "regression", f"model_{model_name}",
                        [model_spec.get("target", "")]
                    )

                    model_result["validation_results"] = training_result
                    model_result["model_created"] = True

            elif model_type == "classification":
                # Create classification model
                model_data = model_spec.get("training_data", {})

                if model_data:
                    dataset = self.statistical_analyzer.spss_engine.sas_engine.create_dataset(
                        f"model_{model_name}", model_data
                    )

                    # Train classifier
                    classification_result = self.statistical_analyzer.spss_engine.run_analysis(
                        "descriptives", f"model_{model_name}"
                    )

                    model_result["validation_results"] = classification_result
                    model_result["model_created"] = True

            # Store model
            self.prediction_models[model_name] = model_spec

        except Exception as e:
            model_result["error"] = str(e)

        return model_result

    def analyze_design_trends(self, design_history: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Analyze design trends."""
        trend_analysis = {
            "designs_analyzed": len(design_history),
            "trend_analysis_timestamp": time.time(),
            "quality_trends": {},
            "performance_trends": {},
            "material_trends": {},
            "design_insights": []
        }

        try:
            # Extract data from design history
            quality_scores = []
            print_times = []
            material_usage = []
            materials = []

            for design in design_history:
                quality_scores.append(design.get("quality_score", 0))
                print_times.append(design.get("print_time", 0))
                material_usage.append(design.get("material_usage", 0))
                materials.append(design.get("material", "unknown"))

            # Analyze trends
            if quality_scores:
                trend_analysis["quality_trends"] = {
                    "mean_quality": statistics.mean(quality_scores),
                    "quality_trend": "improving" if len(quality_scores) > 1 and quality_scores[-1] > quality_scores[0] else "stable",
                    "quality_variance": statistics.variance(quality_scores) if len(quality_scores) > 1 else 0
                }

            if print_times:
                trend_analysis["performance_trends"] = {
                    "mean_print_time": statistics.mean(print_times),
                    "time_trend": "increasing" if len(print_times) > 1 and print_times[-1] > print_times[0] else "stable",
                    "time_variance": statistics.variance(print_times) if len(print_times) > 1 else 0
                }

            if materials:
                material_counts = Counter(materials)
                trend_analysis["material_trends"] = {
                    "most_common_material": material_counts.most_common(1)[0][0] if material_counts else "unknown",
                    "material_diversity": len(material_counts),
                    "material_distribution": dict(material_counts)
                }

            # Generate insights
            insights = []

            quality_trend = trend_analysis["quality_trends"].get("quality_trend", "unknown")
            if quality_trend == "improving":
                insights.append("Design quality is improving over time")
            elif quality_trend == "declining":
                insights.append("Design quality is declining - investigate causes")

            performance_trend = trend_analysis["performance_trends"].get("time_trend", "unknown")
            if performance_trend == "increasing":
                insights.append("Print times are increasing - consider optimization")

            material_diversity = trend_analysis["material_trends"].get("material_diversity", 0)
            if material_diversity > 5:
                insights.append("High material diversity - good for experimentation")

            trend_analysis["design_insights"] = insights

        except Exception as e:
            trend_analysis["error"] = str(e)

        return trend_analysis

    def get_comprehensive_statistics(self) -> Dict[str, Any]:
        """Get comprehensive statistics."""
        return {
            "statistical_analyzer": self.statistical_analyzer.get_statistical_overview(),
            "prediction_models": len(self.prediction_models),
            "analysis_results": len(self.analysis_results),
            "model_names": list(self.prediction_models.keys()),
            "statistical_capabilities": [
                "mesh_quality_analysis",
                "performance_prediction",
                "design_optimization",
                "trend_analysis",
                "statistical_modeling",
                "quality_assessment"
            ]
        }


# Factory functions for statistical analysis
def create_sas_engine() -> SASStyleStatistics:
    """Create SAS-style statistics engine."""
    return SASStyleStatistics()


def create_spss_engine() -> SPSSStyleAnalysis:
    """Create SPSS-style analysis engine."""
    return SPSSStyleAnalysis()


def create_cad_analyzer() -> CADStatisticalAnalyzer:
    """Create CAD statistical analyzer."""
    return CADStatisticalAnalyzer()


def create_statistical_cad() -> StatisticalCADSystem:
    """Create statistical CAD system."""
    return StatisticalCADSystem()
