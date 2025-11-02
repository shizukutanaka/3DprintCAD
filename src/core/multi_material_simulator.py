#!/usr/bin/env python3
"""
複合マテリアルプリントのリアルタイムシミュレーションシステム
マテリアル行動の可視化と最適化機能を提供
"""

from __future__ import annotations

import json
import math
import time
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, asdict, field
from enum import Enum
import numpy as np

from ..core.config import get_config
from ..core.logging import get_logger
from ..core.i18n_optimized import get_text as _

class SimulationType(Enum):
    """シミュレーションの種類"""
    THERMAL = "thermal"
    STRUCTURAL = "structural"
    FLOW = "flow"
    MULTI_MATERIAL = "multi_material"
    WARPING = "warping"
    ADHESION = "adhesion"

class MaterialBehavior(Enum):
    """マテリアル行動の種類"""
    THERMAL_EXPANSION = "thermal_expansion"
    SHRINKAGE = "shrinkage"
    FLOW_VISCOSITY = "flow_viscosity"
    ADHESION_STRENGTH = "adhesion_strength"
    CRYSTALLIZATION = "crystallization"
    PHASE_CHANGE = "phase_change"

@dataclass
class MaterialLayer:
    """マテリアルレイヤー"""
    material_id: str
    thickness: float
    temperature: float
    position: Tuple[float, float, float]
    properties: Dict[str, Any]
    stress: Optional[Dict[str, float]] = None
    strain: Optional[Dict[str, float]] = None

@dataclass
class SimulationPoint:
    """シミュレーションポイント"""
    position: Tuple[float, float, float]
    temperature: float
    stress: Tuple[float, float, float]
    displacement: Tuple[float, float, float]
    material_id: str
    layer_index: int

class MultiMaterialSimulator:
    """複合マテリアルシミュレーター"""

    def __init__(self):
        self.config = get_config()
        self.logger = get_logger(__name__)
        self.material_database = self._load_material_database()
        self.simulation_cache: Dict[str, Dict[str, Any]] = {}

    def _load_material_database(self) -> Dict[str, Dict[str, Any]]:
        """マテリアルデータベースをロード"""
        # 簡易的なマテリアルデータベース（実際にはデータベースからロード）
        return {
            "PLA": {
                "type": "thermoplastic",
                "density": 1.24,  # g/cm³
                "thermal_conductivity": 0.13,  # W/m·K
                "specific_heat": 1800,  # J/kg·K
                "glass_transition_temp": 60,  # °C
                "melting_temp": 150,  # °C
                "thermal_expansion": 68e-6,  # 1/K
                "elastic_modulus": 3.5e9,  # Pa
                "poisson_ratio": 0.36,
                "shrinkage": 0.0025,  # 線収縮率
                "viscosity": 1000,  # Pa·s (溶融時)
                "adhesion_strength": 45,  # MPa
                "color": "#FFA500"
            },
            "ABS": {
                "type": "thermoplastic",
                "density": 1.04,
                "thermal_conductivity": 0.17,
                "specific_heat": 1670,
                "glass_transition_temp": 105,
                "melting_temp": 200,
                "thermal_expansion": 95e-6,
                "elastic_modulus": 2.3e9,
                "poisson_ratio": 0.35,
                "shrinkage": 0.0045,
                "viscosity": 800,
                "adhesion_strength": 52,
                "color": "#FFD700"
            },
            "PETG": {
                "type": "thermoplastic",
                "density": 1.27,
                "thermal_conductivity": 0.21,
                "specific_heat": 1200,
                "glass_transition_temp": 80,
                "melting_temp": 230,
                "thermal_expansion": 60e-6,
                "elastic_modulus": 2.1e9,
                "poisson_ratio": 0.37,
                "shrinkage": 0.002,
                "viscosity": 600,
                "adhesion_strength": 48,
                "color": "#00CED1"
            },
            "TPU": {
                "type": "flexible",
                "density": 1.2,
                "thermal_conductivity": 0.19,
                "specific_heat": 1500,
                "glass_transition_temp": -30,
                "melting_temp": 180,
                "thermal_expansion": 150e-6,
                "elastic_modulus": 20e6,  # 柔らかい
                "poisson_ratio": 0.48,
                "shrinkage": 0.01,
                "viscosity": 2000,
                "adhesion_strength": 35,
                "color": "#FF69B4"
            }
        }

    def simulate_multi_material_print(self,
                                    geometry_data: Dict[str, Any],
                                    materials: List[Dict[str, Any]],
                                    print_settings: Dict[str, Any],
                                    simulation_type: SimulationType = SimulationType.THERMAL) -> Dict[str, Any]:
        """複合マテリアルプリントをシミュレート"""

        simulation_id = f"sim_{int(time.time())}_{hash(str(geometry_data)) % 10000}"

        # キャッシュチェック
        cache_key = f"{simulation_type.value}_{hash(str(geometry_data))}_{hash(str(materials))}"
        if cache_key in self.simulation_cache:
            return self.simulation_cache[cache_key]

        try:
            # ジオメトリを解析
            layers = self._analyze_geometry(geometry_data, materials)

            # シミュレーション実行
            if simulation_type == SimulationType.THERMAL:
                results = self._simulate_thermal_behavior(layers, print_settings)
            elif simulation_type == SimulationType.STRUCTURAL:
                results = self._simulate_structural_behavior(layers, print_settings)
            elif simulation_type == SimulationType.MULTI_MATERIAL:
                results = self._simulate_multi_material_interaction(layers, print_settings)
            elif simulation_type == SimulationType.WARPING:
                results = self._simulate_warping_behavior(layers, print_settings)
            else:
                raise ValueError(f"Unsupported simulation type: {simulation_type}")

            # 結果をキャッシュ
            self.simulation_cache[cache_key] = {
                "simulation_id": simulation_id,
                "success": True,
                "results": results,
                "recommendations": self._generate_recommendations(results, materials)
            }

            return self.simulation_cache[cache_key]

        except Exception as e:
            self.logger.error(f"Simulation failed: {str(e)}")
            return {
                "simulation_id": simulation_id,
                "success": False,
                "error": str(e)
            }

    def _analyze_geometry(self, geometry_data: Dict[str, Any], materials: List[Dict[str, Any]]) -> List[MaterialLayer]:
        """ジオメトリを解析してレイヤー構造を作成"""
        layers = []

        # 簡易的なレイヤー解析（実際にはより複雑なアルゴリズムが必要）
        total_height = geometry_data.get("height", 100)
        layer_count = max(10, int(total_height / 0.2))  # 0.2mmレイヤー想定

        for i in range(layer_count):
            z_position = i * (total_height / layer_count)

            # マテリアルを選択（簡易的に交互に配置）
            material_index = i % len(materials)
            material_id = materials[material_index]["id"]

            # マテリアルプロパティを取得
            material_props = self.material_database.get(material_id, {})

            layer = MaterialLayer(
                material_id=material_id,
                thickness=total_height / layer_count,
                temperature=material_props.get("melting_temp", 200),
                position=(0, 0, z_position),
                properties=material_props
            )

            layers.append(layer)

        return layers

    def _simulate_thermal_behavior(self, layers: List[MaterialLayer], settings: Dict[str, Any]) -> Dict[str, Any]:
        """熱行動をシミュレート"""
        results = {
            "temperature_distribution": [],
            "cooling_time": 0,
            "hot_spots": [],
            "thermal_stress": []
        }

        # 簡易的な熱シミュレーション
        ambient_temp = settings.get("ambient_temperature", 25)
        bed_temp = settings.get("bed_temperature", 60)

        for i, layer in enumerate(layers):
            # 熱伝導計算（簡易的）
            temp_drop = (layer.temperature - ambient_temp) * math.exp(-0.1 * i)
            final_temp = max(ambient_temp, layer.temperature - temp_drop)

            # 熱応力計算
            thermal_strain = layer.properties.get("thermal_expansion", 0) * (layer.temperature - final_temp)
            thermal_stress = thermal_strain * layer.properties.get("elastic_modulus", 1e9)

            layer.temperature = final_temp
            layer.stress = {"thermal": thermal_stress}

            results["temperature_distribution"].append({
                "layer": i,
                "position": layer.position,
                "temperature": final_temp,
                "thermal_stress": thermal_stress
            })

            # ホットスポットを検出
            if thermal_stress > 50e6:  # 50MPa閾値
                results["hot_spots"].append({
                    "layer": i,
                    "position": layer.position,
                    "stress": thermal_stress
                })

        # 冷却時間を計算
        results["cooling_time"] = self._calculate_cooling_time(layers, settings)

        return results

    def _simulate_structural_behavior(self, layers: List[MaterialLayer], settings: Dict[str, Any]) -> Dict[str, Any]:
        """構造行動をシミュレート"""
        results = {
            "displacement_field": [],
            "stress_distribution": [],
            "safety_factor": 1.0,
            "weak_points": []
        }

        # 重力と材料特性に基づく簡易構造解析
        gravity = 9.81  # m/s²

        for i, layer in enumerate(layers):
            material_props = layer.properties

            # 簡易的な応力計算
            stress = material_props.get("density", 1) * gravity * layer.position[2] * 1000  # Paに変換
            displacement = stress / material_props.get("elastic_modulus", 1e9) * 1000  # mmに変換

            layer.stress = {"structural": stress}
            layer.strain = {"structural": displacement}

            results["stress_distribution"].append({
                "layer": i,
                "position": layer.position,
                "stress": stress,
                "displacement": displacement
            })

            # 弱点を検出
            if stress > material_props.get("elastic_modulus", 1e9) * 0.8:  # 80%の降伏応力
                results["weak_points"].append({
                    "layer": i,
                    "position": layer.position,
                    "stress_ratio": stress / material_props.get("elastic_modulus", 1e9)
                })

        # 安全率を計算
        max_stress = max([point["stress"] for point in results["stress_distribution"]], default=0)
        material_strength = min([layer.properties.get("elastic_modulus", 1e9) for layer in layers])
        results["safety_factor"] = material_strength / max_stress if max_stress > 0 else 1.0

        return results

    def _simulate_multi_material_interaction(self, layers: List[MaterialLayer], settings: Dict[str, Any]) -> Dict[str, Any]:
        """複合マテリアル相互作用をシミュレート"""
        results = {
            "interface_stress": [],
            "delamination_risk": [],
            "compatibility_score": 0.0,
            "recommended_modifications": []
        }

        # 隣接レイヤー間の相互作用を分析
        for i in range(len(layers) - 1):
            current_layer = layers[i]
            next_layer = layers[i + 1]

            current_props = current_layer.properties
            next_props = next_layer.properties

            # 接着強度を計算
            adhesion_diff = abs(current_props.get("adhesion_strength", 0) - next_props.get("adhesion_strength", 0))

            # 熱膨張係数の違いによる応力
            thermal_expansion_diff = abs(current_props.get("thermal_expansion", 0) - next_props.get("thermal_expansion", 0))

            interface_stress = adhesion_diff * 1e6 + thermal_expansion_diff * 1e9

            results["interface_stress"].append({
                "interface": f"{i}-{i+1}",
                "materials": [current_layer.material_id, next_layer.material_id],
                "stress": interface_stress,
                "adhesion_compatibility": 1.0 / (1.0 + adhesion_diff / 10)
            })

            # 剥離リスクを評価
            if interface_stress > 100e6 or adhesion_diff > 20:  # リスク閾値
                results["delamination_risk"].append({
                    "interface": f"{i}-{i+1}",
                    "risk_level": "high",
                    "stress": interface_stress,
                    "recommendation": _("インターフェース処理を強化してください", "Enhance interface treatment")
                })

        # 互換性スコアを計算
        if results["interface_stress"]:
            avg_compatibility = sum([iface["adhesion_compatibility"] for iface in results["interface_stress"]]) / len(results["interface_stress"])
            results["compatibility_score"] = avg_compatibility

        return results

    def _simulate_warping_behavior(self, layers: List[MaterialLayer], settings: Dict[str, Any]) -> Dict[str, Any]:
        """反り行動をシミュレート"""
        results = {
            "warping_displacement": [],
            "corner_lift": [],
            "recommended_bed_temp": 60,
            "brim_needed": False
        }

        # 熱収縮による反り計算
        for layer in layers:
            material_props = layer.properties

            # 簡易的な反り計算
            shrinkage = material_props.get("shrinkage", 0.003)
            thermal_contraction = shrinkage * (layer.temperature - 25)  # 室温まで冷却

            # コーナー持ち上がり計算
            corner_lift = thermal_contraction * math.sqrt(layer.position[0]**2 + layer.position[1]**2) * 1000  # mm

            results["warping_displacement"].append({
                "layer": layers.index(layer),
                "position": layer.position,
                "warping": corner_lift
            })

            if corner_lift > 0.5:  # 0.5mm以上の持ち上がり
                results["corner_lift"].append({
                    "position": layer.position,
                    "lift_amount": corner_lift,
                    "severity": "high" if corner_lift > 1.0 else "medium"
                })

        # ブリムが必要か判断
        if results["corner_lift"]:
            max_lift = max([point["lift_amount"] for point in results["corner_lift"]])
            results["brim_needed"] = max_lift > 0.3

        # 推奨ベッド温度を計算
        avg_glass_temp = sum([layer.properties.get("glass_transition_temp", 60) for layer in layers]) / len(layers)
        results["recommended_bed_temp"] = max(60, min(80, avg_glass_temp + 10))

        return results

    def _calculate_cooling_time(self, layers: List[MaterialLayer], settings: Dict[str, Any]) -> float:
        """冷却時間を計算"""
        # 簡易的な冷却時間計算
        max_temp = max([layer.temperature for layer in layers])
        ambient_temp = settings.get("ambient_temperature", 25)
        layer_thickness = layers[0].thickness if layers else 0.2

        # 簡易熱伝達計算
        cooling_rate = 0.1  # °C/s
        temp_diff = max_temp - ambient_temp

        if temp_diff > 0:
            cooling_time = temp_diff / cooling_rate
        else:
            cooling_time = 0

        return cooling_time

    def _generate_recommendations(self, results: Dict[str, Any], materials: List[Dict[str, Any]]) -> List[str]:
        """シミュレーション結果に基づいて推奨事項を生成"""
        recommendations = []

        # 熱関連の推奨
        if "temperature_distribution" in results:
            hot_spots = [p for p in results["temperature_distribution"] if p.get("thermal_stress", 0) > 50e6]
            if hot_spots:
                recommendations.append(_("高温領域を冷却するための追加のファンまたは冷却システムを検討してください", "Consider additional fans or cooling systems for high-temperature areas"))

        # 構造関連の推奨
        if "stress_distribution" in results:
            weak_points = [p for p in results.get("weak_points", []) if p.get("stress_ratio", 0) > 0.8]
            if weak_points:
                recommendations.append(_("構造的な弱点を強化するために、インフィル密度を増加してください", "Increase infill density to reinforce structural weak points"))

        # 複合マテリアル関連の推奨
        if "compatibility_score" in results and results["compatibility_score"] < 0.7:
            recommendations.append(_("マテリアル間の接着を改善するために、インターフェース処理を強化してください", "Enhance interface treatment to improve material adhesion"))

        # 反り関連の推奨
        if "warping_displacement" in results:
            high_warping = [p for p in results["warping_displacement"] if p.get("warping", 0) > 0.5]
            if high_warping:
                recommendations.append(_("反りを防ぐために、ブリムまたはラフトを追加してください", "Add brim or raft to prevent warping"))

        return recommendations

    def get_visualization_data(self, simulation_results: Dict[str, Any]) -> Dict[str, Any]:
        """可視化データを生成"""
        visualization = {
            "points": [],
            "vectors": [],
            "colors": [],
            "annotations": []
        }

        # 温度分布の可視化
        if "temperature_distribution" in simulation_results["results"]:
            for point in simulation_results["results"]["temperature_distribution"]:
                temp = point["temperature"]
                # 温度に基づく色設定（赤:高温、青:低温）
                if temp > 150:
                    color = [1.0, 0.2, 0.2, 0.8]  # 赤
                elif temp > 100:
                    color = [1.0, 0.6, 0.0, 0.8]  # オレンジ
                elif temp > 50:
                    color = [1.0, 1.0, 0.0, 0.8]  # 黄
                else:
                    color = [0.2, 0.8, 1.0, 0.8]  # 青

                visualization["points"].append({
                    "position": point["position"],
                    "color": color,
                    "size": 2.0,
                    "label": f"Temp: {temp:.1f}°C"
                })

        # 応力分布の可視化
        if "stress_distribution" in simulation_results["results"]:
            for point in simulation_results["results"]["stress_distribution"]:
                stress = point["stress"]
                # 応力に基づくベクター表示
                displacement = point["displacement"]
                if displacement > 0.1:  # 0.1mm以上の変位
                    visualization["vectors"].append({
                        "start": point["position"],
                        "end": (
                            point["position"][0] + displacement * 0.1,
                            point["position"][1] + displacement * 0.1,
                            point["position"][2]
                        ),
                        "color": [1.0, 0.0, 1.0, 0.6]  # マゼンタ
                    })

        return visualization

    def generate_simulation_report(self, simulation_results: Dict[str, Any]) -> str:
        """シミュレーション報告書を生成"""
        results = simulation_results["results"]

        report = f"""
# 複合マテリアルプリントシミュレーション報告書

## 概要
シミュレーションID: {simulation_results["simulation_id"]}
実行時刻: {time.strftime("%Y-%m-%d %H:%M:%S")}

## 結果サマリー
"""

        # 熱シミュレーション結果
        if "temperature_distribution" in results:
            max_temp = max([p["temperature"] for p in results["temperature_distribution"]])
            avg_temp = sum([p["temperature"] for p in results["temperature_distribution"]]) / len(results["temperature_distribution"])

            report += f"""
### 熱特性
- 最高温度: {max_temp:.1f}°C
- 平均温度: {avg_temp:.1f}°C
- 冷却時間: {results.get("cooling_time", 0):.1f}秒

ホットスポット検出:
"""
            for spot in results.get("hot_spots", []):
                report += f"- レイヤー {spot['layer']}: 応力 {spot['stress']/1e6:.1f} MPa\n"

        # 構造シミュレーション結果
        if "stress_distribution" in results:
            max_stress = max([p["stress"] for p in results["stress_distribution"]])
            safety_factor = results.get("safety_factor", 1.0)

            report += f"""
### 構造特性
- 最大応力: {max_stress/1e6:.1f} MPa
- 安全率: {safety_factor:.2f}

弱点検出:
"""
            for weak in results.get("weak_points", []):
                report += f"- レイヤー {weak['layer']}: 応力率 {weak['stress_ratio']:.2f}\n"

        # 複合マテリアル結果
        if "compatibility_score" in results:
            compatibility = results["compatibility_score"]
            report += f"""
### マテリアル互換性
- 互換性スコア: {compatibility:.2f}
- 評価: {'良好' if compatibility > 0.8 else '注意が必要' if compatibility > 0.6 else '改善が必要'}

剥離リスク:
"""
            for risk in results.get("delamination_risk", []):
                report += f"- インターフェース {risk['interface']}: {risk['risk_level']}\n"

        # 推奨事項
        recommendations = simulation_results.get("recommendations", [])
        if recommendations:
            report += "
## 推奨事項
"
            for rec in recommendations:
                report += f"- {rec}\n"

        return report

# グローバルインスタンス
_multi_material_simulator = None

def get_multi_material_simulator() -> MultiMaterialSimulator:
    """複合マテリアルシミュレーターのインスタンスを取得"""
    global _multi_material_simulator
    if _multi_material_simulator is None:
        _multi_material_simulator = MultiMaterialSimulator()
    return _multi_material_simulator
