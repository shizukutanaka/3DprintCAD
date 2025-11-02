"""Print readiness evaluation utilities with bilingual summaries."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Tuple

from ..core.analysis.mesh_validator import (
    MeshValidationMetrics,
    MeshValidationResult,
    ValidationIssue,
)


@dataclass(frozen=True)
class ReadinessChecklistItem:
    """Represents a single checklist entry for production readiness."""

    key: str
    status_en: str
    status_ja: str
    detail_en: str
    detail_ja: str

    def as_dict(self) -> Dict[str, str]:
        return {
            "key": self.key,
            "status_en": self.status_en,
            "status_ja": self.status_ja,
            "detail_en": self.detail_en,
            "detail_ja": self.detail_ja,
        }


# Selected bilingual translations for common validation issues.
_ISSUE_TRANSLATIONS_EN_JA: Dict[str, Tuple[str, str]] = {
    "GEOM_WATERTIGHT": (
        "Mesh is not watertight. Repair openings before production.",
        "メッシュは水密性が不足しています。造形前に穴や隙間を修復してください。",
    ),
    "GEOM_WALL_THICKNESS": (
        "Measured wall thickness falls below configured limits.",
        "最低肉厚を下回る領域が見つかりました。強度確保のため補強が必要です。",
    ),
    "GEOM_OVERHANG": (
        "Overhang exceeds allowable angle. Review support plan.",
        "許容角度を超えるオーバーハングが検出されました。サポート配置を再検討してください。",
    ),
    "GEOM_BED_ADHESION": (
        "Bed adhesion area is insufficient for stable printing.",
        "ベッド接触面積が不足しています。ブリムやラフトの利用を検討してください。",
    ),
    "GEOM_SURFACE_ROUGHNESS": (
        "Average surface roughness exceeds quality policy.",
        "表面粗さが基準値を超えています。仕上げ工程や設定を調整してください。",
    ),
    "GEOM_SELF_INTERSECTION": (
        "Self-intersections detected. Repair geometry before release.",
        "自己交差が検出され、造形が阻害される可能性があります。",
    ),
    "GEOM_SMALL_FEATURE": (
        "Features below minimum size may fail during print.",
        "最小フィーチャサイズを下回る部分があります。形状を太くしてください。",
    ),
    "GEOM_SMALL_HOLE": (
        "Hole diameter below configured threshold may close during print.",
        "最小穴径を下回る穴があり、造形時に塞がる恐れがあります。",
    ),
    "GEOM_SCALE": (
        "Model dimensions fall outside validated range.",
        "モデル寸法が設定範囲外です。スケール設定を確認してください。",
    ),
    "GEOM_MULTIPLE_COMPONENTS": (
        "Multiple detached components detected. Confirm assembly intent.",
        "複数の非接続コンポーネントが存在します。配置や結合を見直してください。",
    ),
    "GEOM_OBJ_MATERIAL": (
        "OBJ material definitions missing. Re-export with material library.",
        "OBJのマテリアル定義が不足しています。マテリアルライブラリ付きで再エクスポートしてください。",
    ),
    "GEOM_THIN_TIP": (
        "Thin protrusions detected. Reinforce or add supports.",
        "細い突出が検出されました。補強またはサポート追加を検討してください。",
    ),
    "GEOM_CAVITIES": (
        "Internal cavities may trap resin or powder.",
        "内部空洞が樹脂や粉末を滞留させる恐れがあります。",
    ),
    "GEOM_ASPECT_RATIO": (
        "High aspect ratio triangles can reduce surface quality.",
        "高アスペクト比の三角形は表面品質を低下させる場合があります。",
    ),
    "GEOM_SHARP_INTERNAL_CORNER": (
        "Sharp internal corners exceed stress limits.",
        "鋭い内角が応力限界を超えています。",
    ),
    "GEOM_BED_ADHESION": (
        "Bed adhesion area is below policy minimum.",
        "ベッド接触面積がポリシーの下限を満たしていません。",
    ),
    "GEOM_FLATNESS": (
        "Critical mating surfaces exceed flatness tolerance.",
        "重要な嵌合面の平面度が許容値を超えています。",
    ),
}


_STATUS_MAP: Dict[str, Dict[str, str]] = {
    "ready": {
        "status_en": "Production Ready",
        "status_ja": "造形準備完了",
        "summary_en": "Model passes critical checks and is cleared for production.",
        "summary_ja": "主要検証を通過し、造形実行が可能な状態です。",
    },
    "attention": {
        "status_en": "Ready with Attention",
        "status_ja": "注意点あり",
        "summary_en": "Model is printable but requires attention to highlighted warnings.",
        "summary_ja": "造形は可能ですが、警告項目に対する対策が推奨されます。",
    },
    "remediation": {
        "status_en": "Needs Remediation",
        "status_ja": "改善が必要",
        "summary_en": "Resolve listed issues before releasing to production.",
        "summary_ja": "造形前に指摘された課題を解消してください。",
    },
    "blocked": {
        "status_en": "Not Ready",
        "status_ja": "造形準備不足",
        "summary_en": "Critical errors block production until remediated.",
        "summary_ja": "重大な不具合により造形を進められません。",
    },
}


def evaluate_print_readiness(
    validation_result: MeshValidationResult,
    *,
    recommendations: Optional[Dict[str, Any]] = None,
    repair: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """Calculate a readiness score, bilingual summary, and actionable checklist."""

    issues: List[ValidationIssue] = validation_result.issues or []
    errors = [issue for issue in issues if issue.severity == "error"]
    warnings = [issue for issue in issues if issue.severity != "error"]

    score = max(0, min(100, 100 - len(errors) * 25 - len(warnings) * 8))

    metrics = validation_result.metrics
    status_key = _determine_status_key(validation_result.success, score, metrics)
    status_info = _STATUS_MAP[status_key]

    checklist = _build_checklist(metrics, issues, recommendations)

    translated_issues = []
    for issue in issues[:10]:
        fallback_en = issue.message
        fallback_ja = issue.message
        translated = _ISSUE_TRANSLATIONS_EN_JA.get(issue.code)
        if translated:
            fallback_en, fallback_ja = translated
        translated_issues.append(
            {
                "code": issue.code,
                "severity": issue.severity,
                "message_en": fallback_en,
                "message_ja": fallback_ja,
            }
        )

    readiness: Dict[str, Any] = {
        "score": score,
        "status_en": status_info["status_en"],
        "status_ja": status_info["status_ja"],
        "summary_en": status_info["summary_en"],
        "summary_ja": status_info["summary_ja"],
        "issues": translated_issues,
        "checklist": [item.as_dict() for item in checklist],
    }

    if repair and repair.get("repair_success") is False:
        readiness.setdefault("notes", []).append(
            {
                "note_en": "Automatic repair did not resolve all issues.",
                "note_ja": "自動修復では全ての課題を解消できませんでした。",
            }
        )

    if recommendations and recommendations.get("error"):
        readiness.setdefault("notes", []).append(
            {
                "note_en": "Recommendation engine encountered an error. Settings were not generated.",
                "note_ja": "推奨設定の生成に失敗しました。手動で造形条件を確認してください。",
            }
        )

    return readiness


def _determine_status_key(success: bool, score: int, metrics: Optional[MeshValidationMetrics]) -> str:
    if not success or metrics is None:
        return "blocked"
    if score >= 85:
        return "ready"
    if score >= 70:
        return "attention"
    return "remediation"


def _build_checklist(
    metrics: Optional[MeshValidationMetrics],
    issues: List[ValidationIssue],
    recommendations: Optional[Dict[str, Any]],
) -> List[ReadinessChecklistItem]:
    has_issue = {issue.code for issue in issues}

    checklist: List[ReadinessChecklistItem] = []

    geometry_status = _status_labels(
        passed=len([i for i in issues if i.severity == "error"]) == 0
    )
    geometry_detail_en = "All critical geometry checks passed." if geometry_status[0] == "PASS" else "Resolve blocking geometry errors."
    geometry_detail_ja = "重要なジオメトリ検証を通過しました。" if geometry_status[0] == "PASS" else "造形を阻害するジオメトリエラーを解消してください。"
    checklist.append(
        ReadinessChecklistItem(
            key="geometry_integrity",
            status_en=geometry_status[0],
            status_ja=geometry_status[1],
            detail_en=geometry_detail_en,
            detail_ja=geometry_detail_ja,
        )
    )

    wall_pass = "GEOM_WALL_THICKNESS" not in has_issue and "GEOM_SMALL_FEATURE" not in has_issue
    wall_status = _status_labels(passed=wall_pass)
    wall_detail_en = "Minimum wall thickness and feature size meet policy." if wall_status[0] == "PASS" else "Thin walls or small features require reinforcement."
    wall_detail_ja = "最小肉厚とフィーチャサイズはポリシーを満たしています。" if wall_status[0] == "PASS" else "薄肉や微小フィーチャの補強が必要です。"
    checklist.append(
        ReadinessChecklistItem(
            key="structural_stability",
            status_en=wall_status[0],
            status_ja=wall_status[1],
            detail_en=wall_detail_en,
            detail_ja=wall_detail_ja,
        )
    )

    overhang_flag = "GEOM_OVERHANG" in has_issue
    support_status = _status_labels(passed=not overhang_flag)
    support_detail_en = "Support requirements within configured limits." if support_status[0] == "PASS" else "Review support strategy for steep overhangs."
    support_detail_ja = "サポート要件は設定範囲内です。" if support_status[0] == "PASS" else "急峻なオーバーハングに対するサポート配置を見直してください。"
    checklist.append(
        ReadinessChecklistItem(
            key="support_strategy",
            status_en=support_status[0],
            status_ja=support_status[1],
            detail_en=support_detail_en,
            detail_ja=support_detail_ja,
        )
    )

    adhesion_flag = "GEOM_BED_ADHESION" in has_issue
    adhesion_status = _status_labels(passed=not adhesion_flag)
    adhesion_detail_en = "Bed adhesion area meets configured minimums." if adhesion_status[0] == "PASS" else "Increase adhesion using brim, raft, or plate adjustments."
    adhesion_detail_ja = "ベッド接触面積は設定値を満たしています。" if adhesion_status[0] == "PASS" else "ブリムやラフトの利用などで密着性を高めてください。"
    checklist.append(
        ReadinessChecklistItem(
            key="bed_adhesion",
            status_en=adhesion_status[0],
            status_ja=adhesion_status[1],
            detail_en=adhesion_detail_en,
            detail_ja=adhesion_detail_ja,
        )
    )

    if recommendations and not recommendations.get("error"):
        rec_status = _status_labels(passed=not bool(recommendations.get("supports_required", False)))
        rec_detail_en = (
            "Recommended parameters generated successfully." if rec_status[0] == "PASS" else "Follow generated support and process parameters before printing."
        )
        rec_detail_ja = (
            "推奨パラメータを正常に生成しました。" if rec_status[0] == "PASS" else "造形前に推奨されたサポートと工程パラメータを適用してください。"
        )
    else:
        rec_status = ("REVIEW", "要確認")
        rec_detail_en = "Generate or verify print parameter recommendations manually."
        rec_detail_ja = "推奨造形条件を手動で確認してください。"

    checklist.append(
        ReadinessChecklistItem(
            key="process_parameters",
            status_en=rec_status[0],
            status_ja=rec_status[1],
            detail_en=rec_detail_en,
            detail_ja=rec_detail_ja,
        )
    )

    return checklist


def _status_labels(*, passed: bool) -> Tuple[str, str]:
    if passed:
        return "PASS", "合格"
    return "REVIEW", "要確認"
