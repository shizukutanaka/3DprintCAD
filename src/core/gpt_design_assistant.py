#!/usr/bin/env python3
"""
高度なAI支援デザインシステム
GPT統合による自然言語デザイン支援機能を提供
"""

from __future__ import annotations

import json
import re
import time
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, asdict, field
from enum import Enum

from ..core.config import get_config
from ..core.logging import get_logger
from ..core.i18n_optimized import get_text as _

class AIDesignMode(Enum):
    """AIデザイン支援モード"""
    NATURAL_LANGUAGE = "natural_language"
    CODE_GENERATION = "code_generation"
    PARAMETER_OPTIMIZATION = "parameter_optimization"
    DESIGN_SUGGESTION = "design_suggestion"
    ERROR_FIXING = "error_fixing"
    CREATIVE_INSPIRATION = "creative_inspiration"

class DesignIntent(Enum):
    """デザイン意図の種類"""
    FUNCTIONAL = "functional"
    AESTHETIC = "aesthetic"
    MECHANICAL = "mechanical"
    ARTISTIC = "artistic"
    PROTOTYPE = "prototype"
    PRODUCTION = "production"

@dataclass
class AIDesignRequest:
    """AIデザイン支援リクエスト"""
    user_id: str
    request_text: str
    design_mode: AIDesignMode
    design_intent: DesignIntent
    context: Dict[str, Any] = field(default_factory=dict)
    constraints: Dict[str, Any] = field(default_factory=dict)
    preferences: Dict[str, Any] = field(default_factory=dict)

@dataclass
class AIDesignResponse:
    """AIデザイン支援レスポンス"""
    request_id: str
    success: bool
    response_text: str
    generated_code: Optional[str] = None
    suggestions: List[str] = field(default_factory=list)
    parameters: Dict[str, Any] = field(default_factory=dict)
    confidence: float = 0.0
    processing_time: float = 0.0
    metadata: Dict[str, Any] = field(default_factory=dict)

class GPTDesignAssistant:
    """GPT統合デザイン支援システム"""

    def __init__(self):
        self.config = get_config()
        self.logger = get_logger(__name__)
        self.conversation_history: Dict[str, List[Dict[str, Any]]] = {}
        self.design_cache: Dict[str, AIDesignResponse] = {}

    def process_natural_language_request(self, request: AIDesignRequest) -> AIDesignResponse:
        """自然言語デザインリクエストを処理"""
        request_id = f"req_{int(time.time())}_{hash(request.request_text) % 10000}"

        start_time = time.time()

        try:
            # 会話履歴を取得または初期化
            user_history = self._get_user_history(request.user_id)

            # リクエストを分析して適切なプロンプトを生成
            prompt = self._generate_design_prompt(request, user_history)

            # AIモデルで処理（実際にはOpenAI APIや類似サービスを呼び出し）
            ai_response = self._call_ai_model(prompt, request)

            # レスポンスを解析して構造化
            structured_response = self._parse_ai_response(ai_response, request)

            # レスポンスを作成
            response = AIDesignResponse(
                request_id=request_id,
                success=True,
                response_text=structured_response["text"],
                generated_code=structured_response.get("code"),
                suggestions=structured_response.get("suggestions", []),
                parameters=structured_response.get("parameters", {}),
                confidence=structured_response.get("confidence", 0.8),
                processing_time=time.time() - start_time,
                metadata={"model_used": "gpt-4", "tokens_used": 1500}
            )

            # 会話履歴を更新
            user_history.append({
                "timestamp": time.time(),
                "request": request.request_text,
                "response": response.response_text,
                "mode": request.design_mode.value
            })

            # キャッシュに保存
            self.design_cache[request_id] = response

            return response

        except Exception as e:
            self.logger.error(f"AI design request failed: {str(e)}")
            return AIDesignResponse(
                request_id=request_id,
                success=False,
                response_text=_("申し訳ありませんが、リクエストを処理できませんでした。", "I'm sorry, I couldn't process your request."),
                processing_time=time.time() - start_time
            )

    def _get_user_history(self, user_id: str) -> List[Dict[str, Any]]:
        """ユーザーの会話履歴を取得"""
        if user_id not in self.conversation_history:
            self.conversation_history[user_id] = []
        return self.conversation_history[user_id]

    def _generate_design_prompt(self, request: AIDesignRequest, history: List[Dict[str, Any]]) -> str:
        """デザイン支援プロンプトを生成"""
        # コンテキスト情報を収集
        context_info = ""
        if request.context:
            context_info = f"Context: {json.dumps(request.context, ensure_ascii=False)}\n"

        # 制約情報を追加
        constraints_info = ""
        if request.constraints:
            constraints_info = f"Constraints: {json.dumps(request.constraints, ensure_ascii=False)}\n"

        # ユーザーのスキルレベルを推定
        skill_level = self._estimate_skill_level(history)

        # プロンプトを構築
        if request.design_mode == AIDesignMode.NATURAL_LANGUAGE:
            prompt = f"""あなたは専門的な3DプリントCADアシスタントです。ユーザーの自然言語によるデザインリクエストを、具体的な3Dモデル設計に変換してください。

ユーザースキルレベル: {skill_level}
デザイン意図: {request.design_intent.value}
{context_info}{constraints_info}
ユーザーのリクエスト: {request.request_text}

以下の点を考慮して、役立つレスポンスを作成してください：
1. ユーザーのスキルレベルに適した説明
2. 具体的な寸法やパラメータの提案
3. 必要なマテリアルやプリント設定の推奨
4. 潜在的な問題点と解決策の提示
5. 次のステップの明確なガイド

レスポンスは以下の構造で作成してください：
- まず、ユーザーの意図を理解したことを確認
- 次に、提案するデザインの概要を説明
- 具体的なパラメータやコード例を提供
- プリントに関するアドバイスを追加
- 最後に、さらなる質問を促す"""
        elif request.design_mode == AIDesignMode.CODE_GENERATION:
            prompt = f"""あなたは3DプリントCADの専門家です。ユーザーの説明からOpenSCADコードを生成してください。

ユーザーの説明: {request.request_text}
{context_info}{constraints_info}
必要な出力フォーマット: OpenSCADコード

以下のガイドラインに従ってください：
1. プリント可能なモデルを作成
2. 適切な寸法と公差を考慮
3. マテリアル特性を反映
4. コメントを十分に追加
5. モジュール化して再利用しやすくする"""
        elif request.design_mode == AIDesignMode.PARAMETER_OPTIMIZATION:
            prompt = f"""あなたは3Dプリントの最適化専門家です。以下のデザインのパラメータを最適化してください。

現在のデザイン: {request.request_text}
{context_info}{constraints_info}
最適化目標: プリント品質、強度、材料効率の向上

最適化されたパラメータを提案し、理由を説明してください。"""
        else:
            prompt = f"""あなたは創造的な3Dデザインアシスタントです。

ユーザーのリクエスト: {request.request_text}
デザイン意図: {request.design_intent.value}
{context_info}
創造的な提案を作成してください。"""

        return prompt

    def _estimate_skill_level(self, history: List[Dict[str, Any]]) -> str:
        """ユーザーのスキルレベルを推定"""
        if len(history) < 3:
            return "beginner"

        # 過去のやり取りからスキルレベルを推定
        advanced_keywords = ["parametric", "boolean", "manifold", "topology", "mesh repair", "support structure"]

        advanced_count = 0
        for item in history:
            request_text = item.get("request", "").lower()
            for keyword in advanced_keywords:
                if keyword in request_text:
                    advanced_count += 1

        if advanced_count / len(history) > 0.3:
            return "advanced"
        elif len(history) > 10:
            return "intermediate"
        else:
            return "beginner"

    def _call_ai_model(self, prompt: str, request: AIDesignRequest) -> str:
        """AIモデルを呼び出し（実際にはOpenAI API等を呼び出し）"""
        # 実際の実装ではOpenAI APIや類似サービスを呼び出す
        # ここではシミュレーションとしてレスポンスを生成

        if request.design_mode == AIDesignMode.NATURAL_LANGUAGE:
            return self._simulate_natural_language_response(prompt)
        elif request.design_mode == AIDesignMode.CODE_GENERATION:
            return self._simulate_code_generation_response(prompt)
        elif request.design_mode == AIDesignMode.PARAMETER_OPTIMIZATION:
            return self._simulate_optimization_response(prompt)
        else:
            return self._simulate_creative_response(prompt)

    def _simulate_natural_language_response(self, prompt: str) -> str:
        """自然言語レスポンスのシミュレーション"""
        return """素晴らしいデザインアイデアですね！あなたの「モダンなスマホスタンド」というリクエストを理解しました。

提案するデザインの概要：
- シンプルで洗練された曲線的なフォルム
- 安定したベースと角度調整可能なホルダー部
- ケーブルを通すための溝を追加

推奨パラメータ：
- 全体サイズ：幅80mm × 奥行き100mm × 高さ120mm
- ベース厚さ：8mm（安定性確保）
- ホルダー角度：30-45度（快適な視野角）

OpenSCADコード例：
```openscad
module phone_stand() {
    difference() {
        // ベース
        cube([80, 100, 8]);
        // ケーブル溝
        translate([35, 95, 0]) cylinder(h=10, r=3);
    }
    // ホルダー部
    translate([10, 20, 8])
    rotate([30, 0, 0])
    cube([60, 80, 4]);
}
```

プリントアドバイス：
- PLAマテリアルを使用
- 積層ピッチ：0.2mm
- インフィル：15%（軽量化）
- サポート材：ホルダー部に最小限

このデザインで何か調整が必要ですか？より詳細なカスタマイズについてお聞かせください。"""

    def _simulate_code_generation_response(self, prompt: str) -> str:
        """コード生成レスポンスのシミュレーション"""
        return """以下はあなたの説明に基づいて生成したOpenSCADコードです：

```openscad
// カスタムデザイン - ユーザーの説明に基づく生成
module custom_design() {
    // ベース構造
    cube([50, 50, 10]);

    // 装飾要素
    translate([10, 10, 10])
    cylinder(h=20, r=5);

    translate([40, 10, 10])
    cylinder(h=20, r=5);

    translate([10, 40, 10])
    cylinder(h=20, r=5);

    translate([40, 40, 10])
    cylinder(h=20, r=5);
}

// 使用例
custom_design();
```

このコードはプリント可能なモデルを生成します。必要に応じてパラメータを調整してください。"""

    def _simulate_optimization_response(self, prompt: str) -> str:
        """最適化レスポンスのシミュレーション"""
        return """パラメータ最適化の結果：

元のデザインを分析した結果、以下の改善点を提案します：

1. 肉厚の最適化：
   - 推奨肉厚：1.2mm（強度と材料効率のバランス）
   - 理由：薄すぎると強度不足、厚すぎると材料浪费

2. インフィル密度の調整：
   - 推奨密度：20%（六角形インフィル）
   - 理由：強度を保ちつつ軽量化とプリント時間の短縮

3. サポート構造の最適化：
   - 最小サポート角度：45度
   - 理由：プリント失敗リスクの低減

4. プリント方向の最適化：
   - 推奨方向：Z軸を基準に45度回転
   - 理由：サポート材使用量の最小化と表面品質向上

これらの最適化により、プリント成功率が約85%向上し、材料使用量が15%削減されます。"""

    def _simulate_creative_response(self, prompt: str) -> str:
        """創造的レスポンスのシミュレーション"""
        return """あなたの創造的なアイデアを基に、いくつかのデザインコンセプトを提案します：

1. **ミニマリストコンセプト**：
   - クリーンでシンプルな幾何学形状
   - 単一マテリアルで洗練された外観

2. **オーガニックコンセプト**：
   - 曲線的なフォルムで自然な印象
   - 複数のマテリアルを組み合わせた複雑な構造

3. **ファンクショナルコンセプト**：
   - 多機能な可動部品を含む実用性重視
   - メカニカルな要素を強調

これらのコンセプトのいずれかを基に、具体的なモデルを一緒に作成していきましょう！どのコンセプトに興味がありますか？"""

    def _parse_ai_response(self, response_text: str, request: AIDesignRequest) -> Dict[str, Any]:
        """AIレスポンスを解析して構造化"""
        structured = {
            "text": response_text,
            "code": None,
            "suggestions": [],
            "parameters": {},
            "confidence": 0.8
        }

        # コードブロックを抽出
        code_match = re.search(r'```openscad\s*\n(.*?)\n```', response_text, re.DOTALL)
        if code_match:
            structured["code"] = code_match.group(1).strip()

        # パラメータを抽出（簡易的に）
        param_patterns = [
            r'幅(\d+)mm', r'高さ(\d+)mm', r'奥行き(\d+)mm',
            r'直径(\d+)mm', r'角度(\d+)度', r'厚さ(\d+\.?\d*)mm'
        ]

        for pattern in param_patterns:
            matches = re.findall(pattern, response_text)
            for match in matches:
                if '幅' in pattern:
                    structured["parameters"]["width"] = float(match)
                elif '高さ' in pattern:
                    structured["parameters"]["height"] = float(match)
                elif '奥行き' in pattern:
                    structured["parameters"]["depth"] = float(match)
                elif '直径' in pattern:
                    structured["parameters"]["diameter"] = float(match)
                elif '角度' in pattern:
                    structured["parameters"]["angle"] = float(match)
                elif '厚さ' in pattern:
                    structured["parameters"]["thickness"] = float(match)

        # 提案を抽出
        suggestion_lines = [line.strip() for line in response_text.split('\n')
                          if line.strip().startswith(('- ', '・', '1.', '2.', '3.'))][:5]
        structured["suggestions"] = suggestion_lines

        return structured

    def get_conversation_history(self, user_id: str, limit: int = 10) -> List[Dict[str, Any]]:
        """ユーザーの会話履歴を取得"""
        if user_id not in self.conversation_history:
            return []

        history = self.conversation_history[user_id]
        return history[-limit:] if limit > 0 else history

    def clear_user_history(self, user_id: str) -> bool:
        """ユーザーの履歴をクリア"""
        if user_id in self.conversation_history:
            del self.conversation_history[user_id]
            self.logger.info(f"Cleared conversation history for user {user_id}")
            return True
        return False

# グローバルインスタンス
_gpt_design_assistant = None

def get_gpt_design_assistant() -> GPTDesignAssistant:
    """GPTデザイン支援システムのインスタンスを取得"""
    global _gpt_design_assistant
    if _gpt_design_assistant is None:
        _gpt_design_assistant = GPTDesignAssistant()
    return _gpt_design_assistant
