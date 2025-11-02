#!/usr/bin/env python3
"""
リアルタイム3DプレビューとAR統合システム（拡張版）
WebXRによる没入型デザイン体験を提供
"""

from __future__ import annotations

import json
import time
import asyncio
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, asdict, field
from enum import Enum

from ..core.config import get_config
from ..core.logging import get_logger
from ..core.i18n_optimized import get_text as _

class ARMode(Enum):
    """ARモードの種類"""
    MARKER_BASED = "marker_based"
    MARKERLESS = "markerless"
    WORLD_ANCHORED = "world_anchored"
    FACE_TRACKING = "face_tracking"
    HAND_TRACKING = "hand_tracking"

class XRDevice(Enum):
    """XRデバイスの種類"""
    OCULUS_QUEST = "oculus_quest"
    HTC_VIVE = "htc_vive"
    HOLOLENS = "hololens"
    MOBILE_AR = "mobile_ar"
    DESKTOP_VR = "desktop_vr"

@dataclass
class XRSession:
    """XRセッション"""
    session_id: str
    user_id: str
    device_type: XRDevice
    ar_mode: ARMode
    model_data: Dict[str, Any]
    position: Tuple[float, float, float] = (0, 0, 0)
    rotation: Tuple[float, float, float] = (0, 0, 0)
    scale: float = 1.0
    lighting: Dict[str, Any] = field(default_factory=dict)
    annotations: List[Dict[str, Any]] = field(default_factory=list)

@dataclass
class ARAnnotation:
    """AR注釈"""
    id: str
    position: Tuple[float, float, float]
    content: str
    type: str = "text"  # text, image, model
    color: str = "#ffffff"
    size: float = 1.0
    duration: Optional[float] = None  # 永久表示の場合None

class WebXRIntegrationManager:
    """WebXR統合管理システム"""

    def __init__(self):
        self.config = get_config()
        self.logger = get_logger(__name__)
        self.active_sessions: Dict[str, XRSession] = {}
        self.annotation_database: Dict[str, List[ARAnnotation]] = {}

    def create_xr_session(self, user_id: str, model_data: Dict[str, Any],
                         device_type: XRDevice = XRDevice.DESKTOP_VR,
                         ar_mode: ARMode = ARMode.WORLD_ANCHORED) -> str:
        """XRセッションを作成"""
        session_id = f"xr_session_{int(time.time())}_{hash(str(model_data)) % 10000}"

        session = XRSession(
            session_id=session_id,
            user_id=user_id,
            device_type=device_type,
            ar_mode=ar_mode,
            model_data=model_data
        )

        self.active_sessions[session_id] = session

        # セッション初期化
        self._initialize_session(session)

        self.logger.info(f"Created XR session {session_id} for user {user_id}")
        return session_id

    def _initialize_session(self, session: XRSession) -> None:
        """セッションを初期化"""
        # デフォルトの照明設定
        session.lighting = {
            "ambient": {"color": "#ffffff", "intensity": 0.6},
            "directional": {"color": "#ffffff", "intensity": 0.8, "direction": [1, -1, 1]},
            "point": []
        }

        # デフォルトの注釈を追加
        session.annotations = [
            ARAnnotation(
                id=f"default_{session.session_id}",
                position=(0, 0, 0),
                content=_("モデルをここに配置", "Place model here"),
                type="text"
            )
        ]

    def update_session_transform(self, session_id: str,
                               position: Tuple[float, float, float] = None,
                               rotation: Tuple[float, float, float] = None,
                               scale: float = None) -> Dict[str, Any]:
        """セッションのトランスフォームを更新"""
        if session_id not in self.active_sessions:
            raise ValueError("Session not found")

        session = self.active_sessions[session_id]

        if position is not None:
            session.position = position
        if rotation is not None:
            session.rotation = rotation
        if scale is not None:
            session.scale = scale

        # リアルタイム更新を通知
        asyncio.create_task(self._broadcast_session_update(session))

        return {
            "success": True,
            "transform": {
                "position": session.position,
                "rotation": session.rotation,
                "scale": session.scale
            }
        }

    def add_ar_annotation(self, session_id: str, annotation: ARAnnotation) -> Dict[str, Any]:
        """AR注釈を追加"""
        if session_id not in self.active_sessions:
            raise ValueError("Session not found")

        session = self.active_sessions[session_id]
        session.annotations.append(annotation)

        # アノテーションデータベースに保存
        if session_id not in self.annotation_database:
            self.annotation_database[session_id] = []
        self.annotation_database[session_id].append(annotation)

        return {
            "success": True,
            "annotation_id": annotation.id,
            "total_annotations": len(session.annotations)
        }

    def remove_ar_annotation(self, session_id: str, annotation_id: str) -> Dict[str, Any]:
        """AR注釈を削除"""
        if session_id not in self.active_sessions:
            raise ValueError("Session not found")

        session = self.active_sessions[session_id]

        # アノテーションを検索して削除
        original_count = len(session.annotations)
        session.annotations = [ann for ann in session.annotations if ann.id != annotation_id]

        if len(session.annotations) < original_count:
            # データベースからも削除
            if session_id in self.annotation_database:
                self.annotation_database[session_id] = [
                    ann for ann in self.annotation_database[session_id]
                    if ann.id != annotation_id
                ]

            return {
                "success": True,
                "removed_annotation_id": annotation_id
            }
        else:
            return {"error": "Annotation not found"}

    def get_session_data(self, session_id: str) -> Dict[str, Any]:
        """セッションデータを取得"""
        if session_id not in self.active_sessions:
            raise ValueError("Session not found")

        session = self.active_sessions[session_id]

        return {
            "session_id": session.session_id,
            "user_id": session.user_id,
            "device_type": session.device_type.value,
            "ar_mode": session.ar_mode.value,
            "model_data": session.model_data,
            "transform": {
                "position": session.position,
                "rotation": session.rotation,
                "scale": session.scale
            },
            "lighting": session.lighting,
            "annotations": [asdict(ann) for ann in session.annotations],
            "created_at": time.time()
        }

    def generate_webxr_html(self, session_id: str) -> str:
        """WebXR対応HTMLを生成"""
        if session_id not in self.active_sessions:
            raise ValueError("Session not found")

        session_data = self.get_session_data(session_id)

        html_content = f"""<!DOCTYPE html>
<html lang="ja">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>3D Print CAD - WebXR Preview</title>

    <!-- WebXR Support -->
    <script src="https://cdn.jsdelivr.net/npm/three@0.150.0/build/three.min.js"></script>
    <script src="https://cdn.jsdelivr.net/npm/three@0.150.0/examples/js/loaders/GLTFLoader.js"></script>
    <script src="https://cdn.jsdelivr.net/npm/three@0.150.0/examples/js/controls/OrbitControls.js"></script>
    <script src="https://cdn.jsdelivr.net/npm/webxr-polyfill@latest/build/webxr-polyfill.js"></script>

    <style>
        body {{
            margin: 0;
            padding: 0;
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            background: #1a1a1a;
            color: white;
            overflow: hidden;
        }}

        #info {{
            position: absolute;
            top: 10px;
            left: 10px;
            z-index: 100;
            background: rgba(0, 0, 0, 0.8);
            padding: 10px;
            border-radius: 8px;
            font-size: 14px;
        }}

        #controls {{
            position: absolute;
            bottom: 10px;
            left: 10px;
            z-index: 100;
            display: flex;
            gap: 10px;
        }}

        .control-btn {{
            background: rgba(255, 255, 255, 0.1);
            border: 1px solid rgba(255, 255, 255, 0.3);
            color: white;
            padding: 8px 16px;
            border-radius: 6px;
            cursor: pointer;
            transition: background 0.3s;
        }}

        .control-btn:hover {{
            background: rgba(255, 255, 255, 0.2);
        }}

        #ar-button {{
            background: #007bff;
            border: none;
            padding: 12px 24px;
            border-radius: 8px;
            color: white;
            font-weight: bold;
            cursor: pointer;
        }}

        #ar-button:disabled {{
            opacity: 0.6;
            cursor: not-allowed;
        }}
    </style>
</head>
<body>
    <div id="info">
        <div>セッションID: {session_id}</div>
        <div>デバイス: {session_data['device_type']}</div>
        <div>モード: {session_data['ar_mode']}</div>
    </div>

    <div id="controls">
        <button class="control-btn" onclick="resetView()">リセット</button>
        <button class="control-btn" onclick="toggleWireframe()">ワイヤーフレーム</button>
        <button class="control-btn" onclick="toggleAnnotations()">注釈</button>
        <button id="ar-button" onclick="startAR()">ARモード開始</button>
    </div>

    <script>
        let scene, camera, renderer, controls, model;
        let annotations = [];
        let isARMode = false;

        // Three.jsシーン初期化
        function init() {{
            scene = new THREE.Scene();
            scene.background = new THREE.Color(0x1a1a1a);

            camera = new THREE.PerspectiveCamera(75, window.innerWidth / window.innerHeight, 0.1, 1000);
            camera.position.set(0, 0, 5);

            renderer = new THREE.WebGLRenderer({{ antialias: true }});
            renderer.setSize(window.innerWidth, window.innerHeight);
            renderer.xr.enabled = true;
            document.body.appendChild(renderer.domElement);

            // 照明設定
            const ambientLight = new THREE.AmbientLight(0xffffff, 0.6);
            scene.add(ambientLight);

            const directionalLight = new THREE.DirectionalLight(0xffffff, 0.8);
            directionalLight.position.set(1, -1, 1);
            scene.add(directionalLight);

            // コントローラー設定
            controls = new THREE.OrbitControls(camera, renderer.domElement);
            controls.enableDamping = true;
            controls.dampingFactor = 0.05;

            // モデルをロード
            loadModel();

            // 注釈をロード
            loadAnnotations();

            // リサイズ対応
            window.addEventListener('resize', onWindowResize);

            // アニメーションループ
            animate();
        }}

        function loadModel() {{
            // モデルデータを取得してロード
            const modelData = {json.dumps(session_data['model_data'])};

            if (modelData.format === 'gltf' || modelData.format === 'glb') {{
                const loader = new THREE.GLTFLoader();
                loader.parse(modelData.data, '', (gltf) => {{
                    model = gltf.scene;
                    model.position.copy(new THREE.Vector3(...{list(session_data['transform']['position'])}));
                    model.rotation.set(...{list(session_data['transform']['rotation'])});
                    model.scale.setScalar({session_data['transform']['scale']});
                    scene.add(model);
                }});
            }}
        }}

        function loadAnnotations() {{
            const sessionAnnotations = {json.dumps([asdict(ann) for ann in session_data['annotations']])};

            sessionAnnotations.forEach(ann => {{
                const annotation = createAnnotation(ann);
                annotations.push(annotation);
                scene.add(annotation);
            }});
        }}

        function createAnnotation(annData) {{
            const geometry = new THREE.SphereGeometry(0.05);
            const material = new THREE.MeshBasicMaterial({{ color: annData.color }});
            const sphere = new THREE.Mesh(geometry, material);

            sphere.position.set(...annData.position);

            // 注釈テキスト（簡易的にスフィアで表現）
            return sphere;
        }}

        function startAR() {{
            if (navigator.xr) {{
                navigator.xr.requestSession('immersive-ar', {{
                    requiredFeatures: ['local-floor']
                }}).then((session) => {{
                    renderer.xr.setSession(session);
                    isARMode = true;

                    // ARモード用の設定
                    document.getElementById('ar-button').textContent = 'ARモード終了';
                    document.getElementById('ar-button').onclick = stopAR;
                }}).catch((error) => {{
                    console.error('AR session failed:', error);
                    alert('ARモードを開始できませんでした');
                }});
            }} else {{
                alert('WebXRがサポートされていません');
            }}
        }}

        function stopAR() {{
            if (renderer.xr.getSession()) {{
                renderer.xr.getSession().end();
                isARMode = false;
                document.getElementById('ar-button').textContent = 'ARモード開始';
                document.getElementById('ar-button').onclick = startAR;
            }}
        }}

        function resetView() {{
            camera.position.set(0, 0, 5);
            controls.reset();
        }}

        function toggleWireframe() {{
            if (model) {{
                model.traverse((child) => {{
                    if (child.isMesh) {{
                        child.material.wireframe = !child.material.wireframe;
                    }}
                }});
            }}
        }}

        function toggleAnnotations() {{
            annotations.forEach(ann => {{
                ann.visible = !ann.visible;
            }});
        }}

        function onWindowResize() {{
            camera.aspect = window.innerWidth / window.innerHeight;
            camera.updateProjectionMatrix();
            renderer.setSize(window.innerWidth, window.innerHeight);
        }}

        function animate() {{
            renderer.setAnimationLoop(render);
        }}

        function render() {{
            controls.update();
            renderer.render(scene, camera);
        }}

        // 初期化
        if (document.readyState === 'loading') {{
            document.addEventListener('DOMContentLoaded', init);
        }} else {{
            init();
        }}
    </script>
</body>
</html>"""

        return html_content

    def _broadcast_session_update(self, session: XRSession) -> None:
        """セッション更新をブロードキャスト"""
        # 実際の実装ではWebSocket等でリアルタイム更新を通知
        update_data = {
            "session_id": session.session_id,
            "transform": {
                "position": session.position,
                "rotation": session.rotation,
                "scale": session.scale
            },
            "timestamp": time.time()
        }

        self.logger.debug(f"Broadcasting session update: {update_data}")

    def get_ar_capabilities(self, device_type: XRDevice) -> Dict[str, Any]:
        """AR機能を取得"""
        capabilities = {
            XRDevice.OCULUS_QUEST: {
                "supported_modes": [ARMode.WORLD_ANCHORED, ARMode.HAND_TRACKING],
                "max_annotations": 50,
                "supported_features": ["hand_tracking", "eye_tracking", "voice_commands"]
            },
            XRDevice.HTC_VIVE: {
                "supported_modes": [ARMode.MARKER_BASED, ARMode.WORLD_ANCHORED],
                "max_annotations": 30,
                "supported_features": ["controller_tracking", "room_scale"]
            },
            XRDevice.HOLOLENS: {
                "supported_modes": [ARMode.WORLD_ANCHORED, ARMode.FACE_TRACKING],
                "max_annotations": 100,
                "supported_features": ["eye_tracking", "voice_commands", "gesture_recognition"]
            },
            XRDevice.MOBILE_AR: {
                "supported_modes": [ARMode.MARKER_BASED, ARMode.MARKERLESS],
                "max_annotations": 20,
                "supported_features": ["gyroscope", "accelerometer", "camera"]
            },
            XRDevice.DESKTOP_VR: {
                "supported_modes": [ARMode.WORLD_ANCHORED],
                "max_annotations": 25,
                "supported_features": ["mouse_keyboard", "gamepad"]
            }
        }

        return capabilities.get(device_type, capabilities[XRDevice.DESKTOP_VR])

    def generate_ar_marker(self, session_id: str, marker_type: str = "qr") -> Dict[str, Any]:
        """ARマーカーを生成"""
        if session_id not in self.active_sessions:
            raise ValueError("Session not found")

        # マーカーデータを生成（実際には画像生成ライブラリを使用）
        marker_data = {
            "marker_id": f"marker_{session_id}",
            "marker_type": marker_type,
            "session_id": session_id,
            "data_url": f"data:image/svg+xml;base64,{self._generate_qr_code(session_id)}",
            "physical_size": 50  # mm
        }

        return marker_data

    def _generate_qr_code(self, session_id: str) -> str:
        """QRコードを生成（簡易的に）"""
        # 実際にはqrcodeライブラリ等を使用
        import base64

        # 簡易的なSVG QRコード生成
        qr_svg = f'''<svg xmlns="http://www.w3.org/2000/svg" width="50" height="50">
            <rect width="50" height="50" fill="#000"/>
            <text x="25" y="30" text-anchor="middle" fill="#fff" font-size="8">
                {session_id[:8]}
            </text>
        </svg>'''

        return base64.b64encode(qr_svg.encode('utf-8')).decode('utf-8')

    def get_supported_devices(self) -> List[Dict[str, Any]]:
        """サポートされているデバイス一覧を取得"""
        devices = []

        for device in XRDevice:
            capabilities = self.get_ar_capabilities(device)
            devices.append({
                "device_type": device.value,
                "name": device.name.replace("_", " ").title(),
                "capabilities": capabilities
            })

        return devices

# グローバルインスタンス
_webxr_manager = None

def get_webxr_manager() -> WebXRIntegrationManager:
    """WebXR統合管理システムのインスタンスを取得"""
    global _webxr_manager
    if _webxr_manager is None:
        _webxr_manager = WebXRIntegrationManager()
    return _webxr_manager
