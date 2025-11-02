#!/usr/bin/env python3
"""
リアルタイムコード-視覚統合システム
OpenSCADの課題を解決するための双方向プログラミングインターフェース
"""

from __future__ import annotations

import ast
import json
import re
import time
from typing import Dict, List, Optional, Any, Tuple, Set
from dataclasses import dataclass, field
from enum import Enum

from ..core.config import get_config
from ..core.logging import get_logger
from ..core.i18n_optimized import get_text as _

class CodeElementType(Enum):
    """コード要素の種類"""
    MODULE = "module"
    FUNCTION = "function"
    VARIABLE = "variable"
    TRANSFORMATION = "transformation"
    GEOMETRY = "geometry"
    PARAMETER = "parameter"

@dataclass
class CodeElement:
    """コード要素"""
    id: str
    type: CodeElementType
    name: str
    line_number: int
    column_start: int
    column_end: int
    parent_id: Optional[str] = None
    children: List[str] = field(default_factory=list)
    properties: Dict[str, Any] = field(default_factory=dict)
    visual_representation: Dict[str, Any] = field(default_factory=dict)

@dataclass
class VisualElement:
    """視覚要素"""
    id: str
    code_element_id: str
    geometry_type: str  # "cube", "sphere", "cylinder", etc.
    position: Tuple[float, float, float] = (0, 0, 0)
    rotation: Tuple[float, float, float] = (0, 0, 0)
    scale: Tuple[float, float, float] = (1, 1, 1)
    color: Optional[str] = None
    material: Optional[str] = None
    bounding_box: Optional[Dict[str, Any]] = None

class OpenSCADParser:
    """OpenSCADコードパーサー"""

    def __init__(self):
        self.elements: Dict[str, CodeElement] = {}
        self.visual_elements: Dict[str, VisualElement] = {}
        self.root_elements: List[str] = []

    def parse_code(self, code: str) -> Dict[str, Any]:
        """コードを解析して要素を抽出"""
        try:
            # 簡易的なAST解析（実際にはより洗練されたパーサーを使用）
            lines = code.split('\n')
            self.elements.clear()
            self.visual_elements.clear()
            self.root_elements.clear()

            for line_num, line in enumerate(lines, 1):
                line = line.strip()
                if not line or line.startswith('//') or line.startswith('/*'):
                    continue

                self._parse_line(line, line_num)

            return {
                "elements": {k: v.__dict__ for k, v in self.elements.items()},
                "visual_elements": {k: v.__dict__ for k, v in self.visual_elements.items()},
                "root_elements": self.root_elements
            }

        except Exception as e:
            return {"error": str(e)}

    def _parse_line(self, line: str, line_num: int):
        """単一行を解析"""
        # モジュール定義の検出
        module_match = re.match(r'module\s+(\w+)\s*\((.*?)\)\s*{', line)
        if module_match:
            module_name = module_match.group(1)
            parameters = module_match.group(2)

            element = CodeElement(
                id=f"module_{module_name}_{line_num}",
                type=CodeElementType.MODULE,
                name=module_name,
                line_number=line_num,
                column_start=0,
                column_end=len(line),
                properties={"parameters": self._parse_parameters(parameters)}
            )
            self.elements[element.id] = element
            self.root_elements.append(element.id)
            return

        # 関数定義の検出
        function_match = re.match(r'function\s+(\w+)\s*\((.*?)\)\s*=', line)
        if function_match:
            func_name = function_match.group(1)
            parameters = function_match.group(2)

            element = CodeElement(
                id=f"function_{func_name}_{line_num}",
                type=CodeElementType.FUNCTION,
                name=func_name,
                line_number=line_num,
                column_start=0,
                column_end=len(line),
                properties={"parameters": self._parse_parameters(parameters)}
            )
            self.elements[element.id] = element
            return

        # 変数定義の検出
        var_match = re.match(r'(\w+)\s*=\s*(.+);', line)
        if var_match:
            var_name = var_match.group(1)
            value = var_match.group(2)

            element = CodeElement(
                id=f"var_{var_name}_{line_num}",
                type=CodeElementType.VARIABLE,
                name=var_name,
                line_number=line_num,
                column_start=0,
                column_end=len(line),
                properties={"value": value}
            )
            self.elements[element.id] = element
            return

        # ジオメトリプリミティブの検出
        self._parse_geometry_line(line, line_num)

    def _parse_geometry_line(self, line: str, line_num: int):
        """ジオメトリ行を解析"""
        # cube() の検出
        cube_match = re.match(r'cube\s*\(\s*\[([^\]]+)\]\s*(?:,\s*center\s*=\s*(\w+))?\s*\);', line)
        if cube_match:
            dimensions = cube_match.group(1)
            center = cube_match.group(2) == 'true'

            element_id = f"cube_{line_num}"
            element = CodeElement(
                id=element_id,
                type=CodeElementType.GEOMETRY,
                name="cube",
                line_number=line_num,
                column_start=0,
                column_end=len(line),
                properties={"dimensions": dimensions, "center": center}
            )
            self.elements[element_id] = element

            # 視覚要素を作成
            visual_element = VisualElement(
                id=f"visual_{element_id}",
                code_element_id=element_id,
                geometry_type="cube",
                bounding_box={"width": 20, "height": 20, "depth": 20}  # デフォルト値
            )
            self.visual_elements[visual_element.id] = visual_element
            return

        # sphere() の検出
        sphere_match = re.match(r'sphere\s*\(\s*r\s*=\s*([^\),]+)\s*\);', line)
        if sphere_match:
            radius = sphere_match.group(1)

            element_id = f"sphere_{line_num}"
            element = CodeElement(
                id=element_id,
                type=CodeElementType.GEOMETRY,
                name="sphere",
                line_number=line_num,
                column_start=0,
                column_end=len(line),
                properties={"radius": radius}
            )
            self.elements[element_id] = element

            visual_element = VisualElement(
                id=f"visual_{element_id}",
                code_element_id=element_id,
                geometry_type="sphere",
                bounding_box={"radius": float(radius)}
            )
            self.visual_elements[visual_element.id] = visual_element
            return

        # cylinder() の検出
        cylinder_match = re.match(r'cylinder\s*\(\s*r\s*=\s*([^\),]+)\s*,\s*h\s*=\s*([^\),]+)\s*(?:,\s*center\s*=\s*(\w+))?\s*\);', line)
        if cylinder_match:
            radius = cylinder_match.group(1)
            height = cylinder_match.group(2)
            center = cylinder_match.group(3) == 'true'

            element_id = f"cylinder_{line_num}"
            element = CodeElement(
                id=element_id,
                type=CodeElementType.GEOMETRY,
                name="cylinder",
                line_number=line_num,
                column_start=0,
                column_end=len(line),
                properties={"radius": radius, "height": height, "center": center}
            )
            self.elements[element_id] = element

            visual_element = VisualElement(
                id=f"visual_{element_id}",
                code_element_id=element_id,
                geometry_type="cylinder",
                bounding_box={"radius": float(radius), "height": float(height)}
            )
            self.visual_elements[visual_element.id] = visual_element
            return

        # translate() の検出
        translate_match = re.match(r'translate\s*\(\s*\[([^\]]+)\]\s*\)\s*(.+);', line)
        if translate_match:
            translation = translate_match.group(1)
            content = translate_match.group(2)

            element_id = f"translate_{line_num}"
            element = CodeElement(
                id=element_id,
                type=CodeElementType.TRANSFORMATION,
                name="translate",
                line_number=line_num,
                column_start=0,
                column_end=len(line),
                properties={"translation": translation}
            )
            self.elements[element_id] = element

            # 子要素を解析（簡易的に）
            child_match = re.match(r'.*(\w+)\s*\([^)]+\)\s*;\s*$', content)
            if child_match:
                child_name = child_match.group(1)
                if f"visual_{child_name}_{line_num}" in self.visual_elements:
                    visual_element = self.visual_elements[f"visual_{child_name}_{line_num}"]
                    # 移動を適用
                    tx, ty, tz = map(float, translation.split(','))
                    visual_element.position = (
                        visual_element.position[0] + tx,
                        visual_element.position[1] + ty,
                        visual_element.position[2] + tz
                    )
            return

    def _parse_parameters(self, params_str: str) -> List[str]:
        """パラメータ文字列を解析"""
        if not params_str.strip():
            return []

        # 簡易的なパラメータ解析
        params = [p.strip() for p in params_str.split(',')]
        return params

class RealtimeCodeVisualIntegrator:
    """リアルタイムコード-視覚統合システム"""

    def __init__(self):
        self.config = get_config()
        self.logger = get_logger(__name__)
        self.parser = OpenSCADParser()
        self.active_sessions: Dict[str, Dict[str, Any]] = {}

    def create_session(self, code: str = "", language: str = "ja") -> str:
        """新しいセッションを作成"""
        session_id = f"realtime_{int(time.time())}_{hash(code) % 10000}"

        self.active_sessions[session_id] = {
            "session_id": session_id,
            "code": code,
            "parsed_data": {},
            "last_modified": time.time(),
            "language": language,
            "visual_elements": {},
            "selected_element": None
        }

        # 初期コードを解析
        if code:
            self.update_code(session_id, code)

        self.logger.info(f"Created realtime session {session_id}")
        return session_id

    def update_code(self, session_id: str, code: str) -> Dict[str, Any]:
        """コードを更新してリアルタイムで視覚化を更新"""
        if session_id not in self.active_sessions:
            raise ValueError("Invalid session ID")

        session = self.active_sessions[session_id]
        session["code"] = code
        session["last_modified"] = time.time()

        # コードを解析
        parsed_data = self.parser.parse_code(code)
        session["parsed_data"] = parsed_data

        if "error" not in parsed_data:
            session["visual_elements"] = parsed_data["visual_elements"]

            # 視覚要素にコード要素をリンク
            for visual_id, visual_element in parsed_data["visual_elements"].items():
                if visual_element["code_element_id"] in parsed_data["elements"]:
                    code_element = parsed_data["elements"][visual_element["code_element_id"]]
                    visual_element["name"] = code_element["name"]
                    visual_element["line_number"] = code_element["line_number"]

        return {
            "success": True,
            "parsed_data": parsed_data,
            "visual_elements_count": len(session["visual_elements"])
        }

    def get_visual_representation(self, session_id: str) -> Dict[str, Any]:
        """視覚表現データを取得"""
        if session_id not in self.active_sessions:
            raise ValueError("Invalid session ID")

        session = self.active_sessions[session_id]

        return {
            "visual_elements": session["visual_elements"],
            "parsed_data": session["parsed_data"],
            "selected_element": session["selected_element"]
        }

    def select_element(self, session_id: str, element_id: str) -> Dict[str, Any]:
        """視覚要素を選択"""
        if session_id not in self.active_sessions:
            raise ValueError("Invalid session ID")

        session = self.active_sessions[session_id]

        if element_id in session["visual_elements"]:
            session["selected_element"] = element_id

            # 対応するコード要素を取得
            visual_element = session["visual_elements"][element_id]
            code_element_id = visual_element["code_element_id"]

            if code_element_id in session["parsed_data"].get("elements", {}):
                code_element = session["parsed_data"]["elements"][code_element_id]

                return {
                    "selected_element": element_id,
                    "code_element": code_element,
                    "visual_element": visual_element,
                    "highlight_info": {
                        "line_number": code_element["line_number"],
                        "element_type": code_element["type"],
                        "properties": code_element.get("properties", {})
                    }
                }
            else:
                return {"selected_element": element_id, "visual_element": visual_element}
        else:
            return {"error": "Element not found"}

    def modify_element_property(self, session_id: str, element_id: str, property_name: str, value: Any) -> Dict[str, Any]:
        """視覚要素のプロパティを修正"""
        if session_id not in self.active_sessions:
            raise ValueError("Invalid session ID")

        session = self.active_sessions[session_id]

        if element_id in session["visual_elements"]:
            visual_element = session["visual_elements"][element_id]
            visual_element[property_name] = value

            # 対応するコードを更新（簡易的に）
            code_element_id = visual_element["code_element_id"]
            if code_element_id in session["parsed_data"].get("elements", {}):
                code_element = session["parsed_data"]["elements"][code_element_id]
                if "properties" not in code_element:
                    code_element["properties"] = {}
                code_element["properties"][property_name] = value

                # コード文字列を再生成（簡易的に）
                session["code"] = self._regenerate_code(session["parsed_data"])

            return {
                "success": True,
                "modified_element": element_id,
                "property": property_name,
                "new_value": value,
                "updated_code": session["code"]
            }
        else:
            return {"error": "Element not found"}

    def _regenerate_code(self, parsed_data: Dict[str, Any]) -> str:
        """解析データからコードを再生成（簡易的に）"""
        lines = []

        for element_id, element in parsed_data.get("elements", {}).items():
            if element["type"] == CodeElementType.GEOMETRY.value:
                if element["name"] == "cube":
                    props = element.get("properties", {})
                    dimensions = props.get("dimensions", "[20, 20, 20]")
                    lines.append(f"cube({dimensions});")
                elif element["name"] == "sphere":
                    props = element.get("properties", {})
                    radius = props.get("radius", "10")
                    lines.append(f"sphere(r={radius});")
                elif element["name"] == "cylinder":
                    props = element.get("properties", {})
                    radius = props.get("radius", "10")
                    height = props.get("height", "20")
                    lines.append(f"cylinder(r={radius}, h={height});")

        return "\n".join(lines)

    def get_code_suggestions(self, session_id: str, cursor_position: Dict[str, int]) -> List[Dict[str, Any]]:
        """コードの提案を取得"""
        if session_id not in self.active_sessions:
            raise ValueError("Invalid session ID")

        session = self.active_sessions[session_id]

        # 文脈に基づいた提案を生成
        suggestions = []

        # 基本的なジオメトリプリミティブの提案
        suggestions.extend([
            {
                "type": "geometry",
                "label": "cube([width, height, depth])",
                "description": _("立方体を作成", "Create a cube"),
                "snippet": "cube([$1, $2, $3]);"
            },
            {
                "type": "geometry",
                "label": "sphere(r = radius)",
                "description": _("球体を作成", "Create a sphere"),
                "snippet": "sphere(r = $1);"
            },
            {
                "type": "geometry",
                "label": "cylinder(r = radius, h = height)",
                "description": _("円柱を作成", "Create a cylinder"),
                "snippet": "cylinder(r = $1, h = $2);"
            }
        ])

        # 変換の提案
        suggestions.extend([
            {
                "type": "transformation",
                "label": "translate([x, y, z])",
                "description": _("平行移動", "Translate object"),
                "snippet": "translate([$1, $2, $3])\n\t$0"
            },
            {
                "type": "transformation",
                "label": "rotate([x, y, z])",
                "description": _("回転", "Rotate object"),
                "snippet": "rotate([$1, $2, $3])\n\t$0"
            },
            {
                "type": "transformation",
                "label": "scale([x, y, z])",
                "description": _("スケール", "Scale object"),
                "snippet": "scale([$1, $2, $3])\n\t$0"
            }
        ])

        return suggestions

# グローバルインスタンス
_realtime_integrator = None

def get_realtime_integrator() -> RealtimeCodeVisualIntegrator:
    """リアルタイム統合システムのインスタンスを取得"""
    global _realtime_integrator
    if _realtime_integrator is None:
        _realtime_integrator = RealtimeCodeVisualIntegrator()
    return _realtime_integrator
