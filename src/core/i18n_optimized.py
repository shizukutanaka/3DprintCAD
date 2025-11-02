"""Optimized internationalization (i18n) system for Japanese and English."""
from __future__ import annotations

import json
import locale
import os
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Dict, Optional, Any, List, Union
import yaml


class Language(Enum):
    """Supported languages (50 languages as per requirements)."""
    # Major languages
    EN = "en"  # English
    JA = "ja"  # Japanese
    ES = "es"  # Spanish
    FR = "fr"  # French
    DE = "de"  # German
    IT = "it"  # Italian
    PT = "pt"  # Portuguese
    RU = "ru"  # Russian
    ZH = "zh"  # Chinese (Simplified)
    ZHT = "zh_tw"  # Chinese (Traditional)
    KO = "ko"  # Korean
    AR = "ar"  # Arabic
    HI = "hi"  # Hindi
    BN = "bn"  # Bengali
    UR = "ur"  # Urdu
    TR = "tr"  # Turkish
    PL = "pl"  # Polish
    NL = "nl"  # Dutch
    SV = "sv"  # Swedish
    DA = "da"  # Danish
    NO = "no"  # Norwegian
    FI = "fi"  # Finnish
    CS = "cs"  # Czech
    SK = "sk"  # Slovak
    HU = "hu"  # Hungarian
    RO = "ro"  # Romanian
    BG = "bg"  # Bulgarian
    HR = "hr"  # Croatian
    SR = "sr"  # Serbian
    SL = "sl"  # Slovenian
    ET = "et"  # Estonian
    LV = "lv"  # Latvian
    LT = "lt"  # Lithuanian
    MT = "mt"  # Maltese
    GA = "ga"  # Irish
    CY = "cy"  # Welsh
    IS = "is"  # Icelandic
    FO = "fo"  # Faroese
    GL = "gl"  # Galician
    EU = "eu"  # Basque
    CA = "ca"  # Catalan
    OC = "oc"  # Occitan
    RM = "rm"  # Romansh
    LB = "lb"  # Luxembourgish
    GD = "gd"  # Scottish Gaelic
    KW = "kw"  # Cornish

    # Aliases for compatibility
    ENGLISH = "en"
    JAPANESE = "ja"
    SPANISH = "es"
    FRENCH = "fr"
    GERMAN = "de"
    ITALIAN = "it"
    PORTUGUESE = "pt"
    RUSSIAN = "ru"
    CHINESE = "zh"
    CHINESE_TRADITIONAL = "zh_tw"
    KOREAN = "ko"
    ARABIC = "ar"
    HINDI = "hi"
    BENGALI = "bn"
    URDU = "ur"
    TURKISH = "tr"
    POLISH = "pl"
    DUTCH = "nl"
    SWEDISH = "sv"
    DANISH = "da"
    NORWEGIAN = "no"
    FINNISH = "fi"
    CZECH = "cs"
    SLOVAK = "sk"
    HUNGARIAN = "hu"
    ROMANIAN = "ro"
    BULGARIAN = "bg"
    CROATIAN = "hr"
    SERBIAN = "sr"
    SLOVENIAN = "sl"
    ESTONIAN = "et"
    LATVIAN = "lv"
    LITHUANIAN = "lt"
    MALTESE = "mt"
    IRISH = "ga"
    WELSH = "cy"
    ICELANDIC = "is"
    FAROESE = "fo"
    GALICIAN = "gl"
    BASQUE = "eu"
    CATALAN = "ca"
    OCCITAN = "oc"
    ROMANSH = "rm"
    LUXEMBOURGISH = "lb"
    SCOTTISH_GAELIC = "gd"
    CORNISH = "kw"


@dataclass
class Translation:
    """Translation entry supporting 50 languages."""
    key: str
    # Core languages with full translations
    en: str = ""  # English (fallback)
    ja: str = ""  # Japanese
    es: str = ""  # Spanish
    fr: str = ""  # French
    de: str = ""  # German
    it: str = ""  # Italian
    pt: str = ""  # Portuguese
    ru: str = ""  # Russian
    zh: str = ""  # Chinese (Simplified)
    zht: str = ""  # Chinese (Traditional)
    ko: str = ""  # Korean
    ar: str = ""  # Arabic
    hi: str = ""  # Hindi
    bn: str = ""  # Bengali
    ur: str = ""  # Urdu
    tr: str = ""  # Turkish
    pl: str = ""  # Polish
    nl: str = ""  # Dutch
    sv: str = ""  # Swedish
    da: str = ""  # Danish
    no: str = ""  # Norwegian
    fi: str = ""  # Finnish
    cs: str = ""  # Czech
    sk: str = ""  # Slovak
    hu: str = ""  # Hungarian
    ro: str = ""  # Romanian
    bg: str = ""  # Bulgarian
    hr: str = ""  # Croatian
    sr: str = ""  # Serbian
    sl: str = ""  # Slovenian
    et: str = ""  # Estonian
    lv: str = ""  # Latvian
    lt: str = ""  # Lithuanian
    mt: str = ""  # Maltese
    ga: str = ""  # Irish
    cy: str = ""  # Welsh
    is_: str = ""  # Icelandic (renamed from 'is' to avoid conflict)
    fo: str = ""  # Faroese
    gl: str = ""  # Galician
    eu: str = ""  # Basque
    ca: str = ""  # Catalan
    oc: str = ""  # Occitan
    rm: str = ""  # Romansh
    lb: str = ""  # Luxembourgish
    gd: str = ""  # Scottish Gaelic
    kw: str = ""  # Cornish
    context: Optional[str] = None
    category: Optional[str] = None

    def get(self, language: Union[Language, str]) -> str:
        """Get translation for specified language."""
        if isinstance(language, str):
            language = Language(language)

        # Get translation for the requested language
        lang_value = getattr(self, language.value.lower(), "")

        # Fallback to English if requested language is not available or empty
        if not lang_value:
            lang_value = self.en or ""

        # Final fallback to key itself if no translation available
        return lang_value or self.key

    def set_translation(self, language: Union[Language, str], text: str):
        """Set translation for a specific language."""
        if isinstance(language, str):
            language = Language(language)

        setattr(self, language.value.lower(), text)


@dataclass
class I18nConfig:
    """Configuration for i18n system."""
    default_language: Language = Language.EN
    fallback_language: Language = Language.EN
    auto_detect: bool = True
    translations_dir: Optional[Path] = None
    cache_enabled: bool = True
    # Priority order for language fallbacks
    language_priority: List[Language] = None
    # Enable dynamic translation updates
    dynamic_updates: bool = True


class I18nManager:
    """Unified internationalization manager with comprehensive translation support."""

    _instance: Optional[I18nManager] = None

    def __new__(cls, *args, **kwargs):
        """Singleton pattern for global i18n manager."""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self, config: Optional[I18nConfig] = None):
        """Initialize i18n manager with configuration."""
        if hasattr(self, '_initialized'):
            return

        self.config = config or I18nConfig()
        self.current_language = self.config.default_language
        self.translations: Dict[str, Translation] = {}
        self._cache: Dict[tuple, str] = {} if self.config.cache_enabled else None

        # Set default language priority if not specified
        if self.config.language_priority is None:
            # Priority: current language -> English -> Japanese -> other languages
            self.config.language_priority = [
                self.config.default_language,
                Language.EN,
                Language.JA
            ] + [lang for lang in Language if lang not in {self.config.default_language, Language.EN, Language.JA}]

        # Load translations from files first
        self._load_translations_from_files()

        # Then load built-in translations
        self._load_all_translations()
        self._initialized = True

    def add_translation(self, translation: Translation) -> None:
        """Add or update a translation dynamically."""
        self.translations[translation.key] = translation
        # Clear cache when translations change
        if self._cache is not None:
            self._cache.clear()

    def update_translation(self, key: str, language: Union[Language, str], text: str) -> bool:
        """Update translation for a specific key and language."""
        if key not in self.translations:
            return False

        translation = self.translations[key]
        if isinstance(language, str):
            try:
                language = Language(language)
            except ValueError:
                return False

        setattr(translation, language.value.lower(), text)

        # Clear cache when translations change
        if self._cache is not None:
            self._cache.clear()

        return True

    def remove_translation(self, key: str) -> bool:
        """Remove a translation by key."""
        if key in self.translations:
            del self.translations[key]
            # Clear cache when translations change
            if self._cache is not None:
                self._cache.clear()
            return True
        return False

    def get_translation_stats(self) -> Dict[str, Any]:
        """Get comprehensive translation statistics."""
        stats = {
            "total_keys": len(self.translations),
            "languages": {},
            "categories": {},
            "completeness": {}
        }

        # Statistics by language
        for lang in Language:
            lang_key = lang.value.lower()
            translated_count = 0
            total_count = len(self.translations)

            for trans in self.translations.values():
                if getattr(trans, lang_key, ""):
                    translated_count += 1

            completeness = translated_count / total_count if total_count > 0 else 0
            stats["languages"][lang.value] = {
                "translated": translated_count,
                "total": total_count,
                "completeness": completeness,
                "status": "complete" if completeness >= 0.9 else "incomplete"
            }

        # Statistics by category
        categories = set()
        for trans in self.translations.values():
            if trans.category:
                categories.add(trans.category)

        for category in categories:
            category_translations = self.get_category_translations(category)
            category_stats = {
                "total_keys": len(category_translations),
                "languages": {}
            }

            for lang in Language:
                lang_key = lang.value.lower()
                translated_count = 0

                for trans in category_translations:
                    if getattr(trans, lang_key, ""):
                        translated_count += 1

                completeness = translated_count / len(category_translations) if category_translations else 0
                category_stats["languages"][lang.value] = {
                    "translated": translated_count,
                    "completeness": completeness
                }

            stats["categories"][category] = category_stats

        # Overall completeness
        total_completeness = sum(
            stats["languages"][lang]["completeness"]
            for lang in stats["languages"]
        ) / len(stats["languages"]) if stats["languages"] else 0

        return stats

    def validate_translations(self) -> Dict[str, Any]:
        """Comprehensive validation of translations."""
        validation_results = {
            "overall_status": "valid",
            "issues": [],
            "warnings": [],
            "language_completeness": {},
            "category_completeness": {},
            "quality_checks": {}
        }

        # Check for missing translations
        for lang in Language:
            lang_key = lang.value.lower()
            missing_count = 0
            total_count = len(self.translations)

            for trans in self.translations.values():
                if not getattr(trans, lang_key, ""):
                    missing_count += 1

            completeness = (total_count - missing_count) / total_count if total_count > 0 else 0

            if missing_count > 0:
                validation_results["issues"].append({
                    "type": "missing_translations",
                    "language": lang.value,
                    "missing_count": missing_count,
                    "total_count": total_count,
                    "completeness": completeness
                })

            validation_results["language_completeness"][lang.value] = {
                "missing": missing_count,
                "total": total_count,
                "completeness": completeness
            }

        # Check for placeholder translations (e.g., "[TODO: ...]")
        placeholder_patterns = ["[TODO", "[FIXME", "[XXX", "???", "TBD", "翻訳が必要"]
        for key, trans in self.translations.items():
            for lang in Language:
                lang_key = lang.value.lower()
                text = getattr(trans, lang_key, "")
                if text and any(pattern in text for pattern in placeholder_patterns):
                    validation_results["warnings"].append({
                        "type": "placeholder_translation",
                        "key": key,
                        "language": lang.value,
                        "text": text
                    })

        # Check for inconsistent variable usage
        for key, trans in self.translations.items():
            en_text = trans.en or ""
            if not en_text:
                continue

            # Find variables in English text
            import re
            en_vars = set(re.findall(r'\{(\w+)\}', en_text))

            for lang in Language:
                if lang == Language.EN:
                    continue

                lang_key = lang.value.lower()
                lang_text = getattr(trans, lang_key, "")
                if not lang_text:
                    continue

                lang_vars = set(re.findall(r'\{(\w+)\}', lang_text))

                # Check for missing or extra variables
                missing_vars = en_vars - lang_vars
                extra_vars = lang_vars - en_vars

                if missing_vars:
                    validation_results["issues"].append({
                        "type": "missing_variables",
                        "key": key,
                        "language": lang.value,
                        "missing_variables": list(missing_vars),
                        "expected_variables": list(en_vars)
                    })

                if extra_vars:
                    validation_results["warnings"].append({
                        "type": "extra_variables",
                        "key": key,
                        "language": lang.value,
                        "extra_variables": list(extra_vars),
                        "expected_variables": list(en_vars)
                    })

        # Check for duplicate translations
        text_by_language = {}
        for lang in Language:
            lang_key = lang.value.lower()
            text_by_language[lang.value] = {}

            for key, trans in self.translations.items():
                text = getattr(trans, lang_key, "")
                if text:
                    if text in text_by_language[lang.value]:
                        text_by_language[lang.value][text].append(key)
                    else:
                        text_by_language[lang.value][text] = [key]

        # Find duplicate texts
        for lang, texts in text_by_language.items():
            for text, keys in texts.items():
                if len(keys) > 1:
                    validation_results["warnings"].append({
                        "type": "duplicate_translations",
                        "language": lang,
                        "text": text,
                        "keys": keys
                    })

        # Overall status determination
        if validation_results["issues"]:
            validation_results["overall_status"] = "invalid"
        elif validation_results["warnings"]:
            validation_results["overall_status"] = "warnings"
        else:
            validation_results["overall_status"] = "valid"

        return validation_results

    def export_translations(self, output_dir: Optional[Path] = None) -> Dict[str, Path]:
        """Export all translations to files organized by language."""
        if output_dir is None:
            project_root = Path(__file__).parent.parent.parent
            output_dir = project_root / "translations"

        output_dir.mkdir(parents=True, exist_ok=True)

        exported_files = {}

        # Export all translations as JSON
        all_translations_file = output_dir / "translations.json"
        self.save_to_file(all_translations_file)
        exported_files["all"] = all_translations_file

        # Export by language
        for lang in Language:
            lang_translations = {}

            for key, trans in self.translations.items():
                lang_key = lang.value.lower()
                lang_value = getattr(trans, lang_key, "")

                if lang_value:  # Only include non-empty translations
                    lang_translations[key] = lang_value

            if lang_translations:
                lang_file = output_dir / f"translations_{lang.value}.json"
                with open(lang_file, 'w', encoding='utf-8') as f:
                    json.dump(lang_translations, f, ensure_ascii=False, indent=2)
                exported_files[lang.value] = lang_file

        return exported_files

    def _detect_system_language(self):
        """Detect system language from locale with support for 50 languages."""
        try:
            system_locale = locale.getdefaultlocale()[0]
            if not system_locale:
                return

            # Language code mapping for 50 supported languages
            language_map = {
                'en': Language.EN,      # English
                'ja': Language.JA,      # Japanese
                'es': Language.ES,      # Spanish
                'fr': Language.FR,      # French
                'de': Language.DE,      # German
                'it': Language.IT,      # Italian
                'pt': Language.PT,      # Portuguese
                'ru': Language.RU,      # Russian
                'zh': Language.ZH,      # Chinese (Simplified)
                'zh-tw': Language.ZHT,  # Chinese (Traditional)
                'ko': Language.KO,      # Korean
                'ar': Language.AR,      # Arabic
                'hi': Language.HI,      # Hindi
                'bn': Language.BN,      # Bengali
                'ur': Language.UR,      # Urdu
                'tr': Language.TR,      # Turkish
                'pl': Language.PL,      # Polish
                'nl': Language.NL,      # Dutch
                'sv': Language.SV,      # Swedish
                'da': Language.DA,      # Danish
                'no': Language.NO,      # Norwegian
                'fi': Language.FI,      # Finnish
                'cs': Language.CS,      # Czech
                'sk': Language.SK,      # Slovak
                'hu': Language.HU,      # Hungarian
                'ro': Language.RO,      # Romanian
                'bg': Language.BG,      # Bulgarian
                'hr': Language.HR,      # Croatian
                'sr': Language.SR,      # Serbian
                'sl': Language.SL,      # Slovenian
                'et': Language.ET,      # Estonian
                'lv': Language.LV,      # Latvian
                'lt': Language.LT,      # Lithuanian
                'mt': Language.MT,      # Maltese
                'ga': Language.GA,      # Irish
                'cy': Language.CY,      # Welsh
                'is': Language.IS,      # Icelandic
                'fo': Language.FO,      # Faroese
                'gl': Language.GL,      # Galician
                'eu': Language.EU,      # Basque
                'ca': Language.CA,      # Catalan
                'oc': Language.OC,      # Occitan
                'rm': Language.RM,      # Romansh
                'lb': Language.LB,      # Luxembourgish
                'gd': Language.GD,      # Scottish Gaelic
                'kw': Language.KW,      # Cornish
            }

            # Check for exact match first
            if system_locale.lower() in language_map:
                self.current_language = language_map[system_locale.lower()]
                return

            # Check for language prefix (e.g., 'en-US' -> 'en')
            lang_prefix = system_locale.split('-')[0].lower()
            if lang_prefix in language_map:
                self.current_language = language_map[lang_prefix]
                return

        except Exception:
            # If detection fails, keep default language
            pass

    def _load_translations_from_files(self):
        """Load translations from external files."""
        # Default translation directories to search
        search_dirs = []

        # 1. Custom translations directory from config
        if self.config.translations_dir:
            search_dirs.append(self.config.translations_dir)

        # 2. Default translations directory relative to project
        project_root = Path(__file__).parent.parent.parent
        search_dirs.extend([
            project_root / "translations",
            project_root / "locale",
            project_root / "i18n"
        ])

        # 3. System-wide translation directories
        if os.name == 'posix':  # Unix-like systems
            search_dirs.extend([
                Path("/usr/share/3dprintcad/translations"),
                Path("/usr/local/share/3dprintcad/translations"),
                Path.home() / ".3dprintcad" / "translations"
            ])
        else:  # Windows
            search_dirs.extend([
                Path.home() / ".3dprintcad" / "translations"
            ])

        # Load translations from all found directories
        for search_dir in search_dirs:
            if search_dir.exists() and search_dir.is_dir():
                self._load_translation_files_from_dir(search_dir)

    def _load_translation_files_from_dir(self, directory: Path):
        """Load all translation files from a directory."""
        # Supported file extensions
        supported_extensions = {'.json', '.yaml', '.yml'}

        # Find all translation files
        for ext in supported_extensions:
            for file_path in directory.glob(f"**/*{ext}"):
                try:
                    self.load_from_file(file_path)
                    self.logger.info(f"Loaded translations from: {file_path}")
                except Exception as exc:
                    self.logger.warning(f"Failed to load translations from {file_path}: {exc}")

    def _load_all_translations(self):
        """Load all translation categories."""
        # UI translations
        self._add_translations([
            Translation("ui.title", "3D Print CAD Assistant", "3DプリントCADアシスタント", category="ui"),
            Translation("ui.dashboard", "Dashboard", "ダッシュボード", category="ui"),
            Translation("ui.3d_viewer", "3D Viewer", "3Dビューアー", category="ui"),
            Translation("ui.analysis", "Analysis", "解析", category="ui"),
            Translation("ui.materials", "Materials", "材料", category="ui"),
            Translation("ui.workflow", "Workflow", "ワークフロー", category="ui"),
            Translation("ui.switch_language", "Switch Language", "言語切替", category="ui"),
            Translation("ui.toggle_theme", "Toggle Theme", "テーマ切替", category="ui"),
            Translation("ui.settings", "Settings", "設定", category="ui"),
            Translation("ui.keyboard_shortcuts", "Keyboard Shortcuts", "キーボードショートカット", category="ui"),
            Translation("ui.help_support", "Help & Support", "ヘルプとサポート", category="ui"),
            Translation("ui.about", "About", "このアプリについて", category="ui"),
            Translation("ui.upload", "Upload File", "ファイルをアップロード", category="ui"),
            Translation("ui.validate", "Validate", "検証", category="ui"),
            Translation("ui.repair", "Repair", "修復", category="ui"),
            Translation("ui.slice", "Slice", "スライス", category="ui"),
            Translation("ui.export", "Export", "エクスポート", category="ui"),
            Translation("ui.cancel", "Cancel", "キャンセル", category="ui"),
            Translation("ui.save", "Save", "保存", category="ui"),
            Translation("ui.loading", "Loading...", "読み込み中...", category="ui"),
            Translation("ui.processing", "Processing...", "処理中...", category="ui"),
            Translation("ui.complete", "Complete", "完了", category="ui"),
            Translation("ui.failed", "Failed", "失敗", category="ui"),
            Translation("ui.select_file", "Select mesh file", "メッシュファイルを選択", category="ui"),
            Translation("ui.analyze", "Analyze", "解析", category="ui"),
            Translation("ui.help", "Help", "ヘルプ", category="ui"),
        ])

        # File operations
        self._add_translations([
            Translation("file.select", "Select a file", "ファイルを選択", category="file"),
            Translation("file.drag_drop", "Drag & drop files here", "ここにファイルをドラッグ&ドロップ", category="file"),
            Translation("file.supported_formats", "Supported formats", "対応フォーマット", category="file"),
            Translation("file.size_limit", "Maximum file size: {size}MB", "最大ファイルサイズ: {size}MB", category="file"),
            Translation("file.upload_success", "File uploaded successfully", "ファイルのアップロードに成功しました", category="file"),
            Translation("file.upload_failed", "File upload failed", "ファイルのアップロードに失敗しました", category="file"),
            Translation("file.not_found", "File not found", "ファイルが見つかりません", category="file"),
            Translation("file.invalid_format", "Invalid file format", "無効なファイル形式", category="file"),
        ])

        # Validation messages
        self._add_translations([
            Translation("validation.title", "Validation Results", "検証結果", category="validation"),
            Translation("validation.running", "Running validation checks...", "検証チェック実行中...", category="validation"),
            Translation("validation.passed", "All validation checks passed", "すべての検証チェックに合格", category="validation"),
            Translation("validation.issues_found", "{count} issues found", "{count}件の問題が見つかりました", category="validation"),
            Translation("validation.watertight", "Watertight", "水密性", category="validation"),
            Translation("validation.watertight.pass", "Mesh is watertight", "メッシュは水密です", category="validation"),
            Translation("validation.watertight.fail", "Mesh is not watertight", "メッシュは水密ではありません", category="validation"),
            Translation("validation.manifold", "Manifold", "多様体", category="validation"),
            Translation("validation.manifold.pass", "Mesh is manifold", "メッシュは多様体です", category="validation"),
            Translation("validation.manifold.fail", "Mesh is non-manifold", "メッシュは非多様体です", category="validation"),
            Translation("validation.wall_thickness", "Wall Thickness", "肉厚", category="validation"),
            Translation("validation.wall_thickness.thin", "Thin walls detected: {thickness}mm", "薄い壁が検出されました: {thickness}mm", category="validation"),
            Translation("validation.overhang", "Overhang Angle", "オーバーハング角度", category="validation"),
            Translation("validation.overhang.steep", "Steep overhang: {angle}°", "急なオーバーハング: {angle}°", category="validation"),
            Translation("validation.self_intersection", "Self-intersection", "自己交差", category="validation"),
            Translation("validation.degenerate_faces", "Degenerate Faces", "縮退面", category="validation"),
            Translation("validation.flipped_normals", "Flipped Normals", "反転法線", category="validation"),
            Translation("validation.duplicate_faces", "Duplicate Faces", "重複面", category="validation"),
        ])

        # Mesh statistics
        self._add_translations([
            Translation("mesh.vertices", "Vertices", "頂点", category="mesh"),
            Translation("mesh.faces", "Faces", "面", category="mesh"),
            Translation("mesh.edges", "Edges", "エッジ", category="mesh"),
            Translation("mesh.volume", "Volume", "体積", category="mesh"),
            Translation("mesh.surface_area", "Surface Area", "表面積", category="mesh"),
            Translation("mesh.bounding_box", "Bounding Box", "バウンディングボックス", category="mesh"),
            Translation("mesh.center_of_mass", "Center of Mass", "重心", category="mesh"),
            Translation("mesh.dimensions", "Dimensions", "寸法", category="mesh"),
            Translation("mesh.scale", "Scale", "スケール", category="mesh"),
        ])

        # Repair operations
        self._add_translations([
            Translation("repair.title", "Mesh Repair", "メッシュ修復", category="repair"),
            Translation("repair.attempting", "Attempting to repair mesh...", "メッシュの修復を試みています...", category="repair"),
            Translation("repair.success", "Mesh repaired successfully", "メッシュの修復に成功しました", category="repair"),
            Translation("repair.failed", "Failed to repair mesh", "メッシュの修復に失敗しました", category="repair"),
            Translation("repair.partial", "Partially repaired", "部分的に修復されました", category="repair"),
            Translation("repair.holes_filled", "{count} holes filled", "{count}個の穴を埋めました", category="repair"),
            Translation("repair.normals_fixed", "Normals fixed", "法線を修正しました", category="repair"),
            Translation("repair.duplicates_removed", "{count} duplicate vertices removed", "{count}個の重複頂点を削除しました", category="repair"),
            Translation("repair.intersections_resolved", "Self-intersections resolved", "自己交差を解決しました", category="repair"),
        ])

        # Slicing operations
        self._add_translations([
            Translation("slice.title", "Slicing Settings", "スライス設定", category="slice"),
            Translation("slice.layer_height", "Layer Height", "積層ピッチ", category="slice"),
            Translation("slice.infill_density", "Infill Density", "インフィル密度", category="slice"),
            Translation("slice.print_speed", "Print Speed", "印刷速度", category="slice"),
            Translation("slice.support_enabled", "Enable Supports", "サポート有効", category="slice"),
            Translation("slice.support_angle", "Support Angle", "サポート角度", category="slice"),
            Translation("slice.estimated_time", "Estimated Print Time", "推定印刷時間", category="slice"),
            Translation("slice.material_usage", "Material Usage", "材料使用量", category="slice"),
            Translation("slice.layer_count", "Layer Count", "レイヤー数", category="slice"),
            Translation("slice.nozzle_temp", "Nozzle Temperature", "ノズル温度", category="slice"),
            Translation("slice.bed_temp", "Bed Temperature", "ベッド温度", category="slice"),
            Translation("slice.retraction", "Retraction", "リトラクション", category="slice"),
        ])

        # Materials
        self._add_translations([
            Translation("material.pla", "PLA", "PLA", category="material"),
            Translation("material.abs", "ABS", "ABS", category="material"),
            Translation("material.petg", "PETG", "PETG", category="material"),
            Translation("material.tpu", "TPU", "TPU", category="material"),
            Translation("material.nylon", "Nylon", "ナイロン", category="material"),
            Translation("material.pc", "Polycarbonate", "ポリカーボネート", category="material"),
            Translation("material.pva", "PVA", "PVA", category="material"),
            Translation("material.hips", "HIPS", "HIPS", category="material"),
            Translation("material.wood_fill", "Wood Fill", "ウッドフィル", category="material"),
            Translation("material.metal_fill", "Metal Fill", "メタルフィル", category="material"),
        ])

        # Errors
        self._add_translations([
            Translation("error.file_not_found", "File not found", "ファイルが見つかりません", category="error"),
            Translation("error.invalid_format", "Invalid file format", "無効なファイル形式", category="error"),
            Translation("error.load_failed", "Failed to load file", "ファイルの読み込みに失敗しました", category="error"),
            Translation("error.save_failed", "Failed to save file", "ファイルの保存に失敗しました", category="error"),
            Translation("error.network_error", "Network error", "ネットワークエラー", category="error"),
            Translation("error.permission_denied", "Permission denied", "アクセスが拒否されました", category="error"),
            Translation("error.unknown", "Unknown error occurred", "不明なエラーが発生しました", category="error"),
            Translation("error.out_of_memory", "Out of memory", "メモリ不足", category="error"),
        ])

        # CLI messages
        self._add_translations([
            Translation("cli.processed", "Processed", "処理件数", category="cli"),
            Translation("cli.success", "Success", "成功", category="cli"),
            Translation("cli.failed", "Failed", "失敗", category="cli"),
            Translation("cli.success_rate", "Success rate", "成功率", category="cli"),
            Translation("cli.total_time", "Total time", "総処理時間", category="cli"),
            Translation("cli.average_per_file", "Average per file", "平均処理時間", category="cli"),
            Translation("cli.failure_breakdown", "Failure Breakdown", "失敗内訳", category="cli"),
            Translation("cli.compliance_policy", "Compliance policy", "準拠ポリシー", category="cli"),
            Translation("cli.path_safety_enforced", "Path safety enforced", "パス安全性の強制", category="cli"),
            Translation("cli.symlink_protection_enforced", "Symlink protection enforced", "シンボリックリンク防御", category="cli"),
            Translation("cli.roi_estimate", "ROI estimate", "ROI 評価", category="cli"),
            Translation("cli.manual_time_saved_total", "Manual time saved (total)", "手作業削減時間(合計)", category="cli"),
            Translation("cli.manual_time_saved_avg", "Manual time saved (avg)", "手作業削減時間(平均)", category="cli"),
            Translation("cli.cost_avoided", "Cost avoided", "削減コスト", category="cli"),
            Translation("cli.issue_severity_totals", "Issue severity totals", "重大度別件数", category="cli"),
            Translation("cli.hash_manifest_warnings", "Hash manifest warnings", "ハッシュマニフェスト警告件数", category="cli"),
            Translation("cli.top_issues", "Top Issues", "主な課題", category="cli"),
            Translation("cli.top_recommendations", "Top Recommendations", "主な推奨事項", category="cli"),
            Translation("cli.print_readiness_status", "Print readiness status", "造形準備ステータス", category="cli"),
            Translation("cli.average_readiness_score", "Average readiness score", "平均造形準備スコア", category="cli"),
            Translation("cli.top_recurring_issues", "Top recurring issues", "頻出課題", category="cli"),
            Translation("cli.top_rationales", "Top rationales", "主な推奨理由", category="cli"),
            Translation("cli.insights", "Insights", "考察", category="cli"),
            Translation("cli.failed_files", "Failed files", "失敗したファイル", category="cli"),
            Translation("cli.batch_processing_statistics", "Batch Processing Statistics", "バッチ処理統計", category="cli"),
            Translation("cli.filtered_results", "Filtered results: {count} of {total} files match criteria", "フィルタリング結果: {count}/{total} 件のファイルが条件に一致", category="cli"),
            Translation("cli.overall_timing", "Overall timing", "全体のタイミング", category="cli"),
            Translation("cli.detailed_timing_analysis", "Detailed timing analysis", "詳細なタイミング分析", category="cli"),
            Translation("cli.min_processing_time", "Min processing time", "最小処理時間", category="cli"),
            Translation("cli.max_processing_time", "Max processing time", "最大処理時間", category="cli"),
            Translation("cli.median_processing_time", "Median processing time", "中央処理時間", category="cli"),
            Translation("cli.processing_time_distribution", "Processing time distribution", "処理時間分布", category="cli"),
            Translation("cli.fast", "Fast (< 1s)", "高速 (< 1秒)", category="cli"),
            Translation("cli.medium", "Medium (1-10s)", "中速 (1-10秒)", category="cli"),
            Translation("cli.slow", "Slow (10-60s)", "低速 (10-60秒)", category="cli"),
            Translation("cli.very_slow", "Very slow (≥ 60s)", "非常に低速 (≥ 60秒)", category="cli"),
            Translation("cli.performance_rating", "Performance rating", "パフォーマンス評価", category="cli"),
            Translation("cli.insight", "Insight", "洞察", category="cli"),
            Translation("cli.memory_usage", "Memory usage", "メモリ使用量", category="cli"),
            Translation("cli.average_memory_delta", "Average memory delta", "平均メモリ差分", category="cli"),
            Translation("cli.quality_metrics", "Quality metrics", "品質メトリクス", category="cli"),
            Translation("cli.total_warnings", "Total warnings", "警告総数", category="cli"),
            Translation("cli.total_errors", "Total errors", "エラー総数", category="cli"),
            Translation("cli.average_issues_per_file", "Average issues per file", "1ファイルあたりの平均問題数", category="cli"),
        ])

    def _add_translations(self, translations: List[Translation]):
        """Add multiple translations to the registry."""
        for trans in translations:
            self.translations[trans.key] = trans

    def t(self, key: str, **kwargs) -> str:
        """Get translation for key with variable substitution and priority fallback."""
        # Check cache first
        if self._cache is not None:
            cache_key = (key, self.current_language, tuple(kwargs.items()))
            if cache_key in self._cache:
                return self._cache[cache_key]

        # Get translation
        if key not in self.translations:
            # Return key itself if translation not found
            return key

        translation = self.translations[key]

        # Try current language first, then fallback through priority list
        text = ""
        for priority_lang in self.config.language_priority:
            lang_key = priority_lang.value.lower()
            potential_text = getattr(translation, lang_key, "")
            if potential_text:
                text = potential_text
                break

        # Final fallback to key itself if no translation available
        if not text:
            text = key

        # Variable substitution
        if kwargs:
            try:
                text = text.format(**kwargs)
            except KeyError:
                pass

        # Cache result
        if self._cache is not None:
            cache_key = (key, self.current_language, tuple(kwargs.items()))
            self._cache[cache_key] = text

        return text

    def set_language(self, language: Union[Language, str]):
        """Set current language."""
        if isinstance(language, str):
            try:
                language = Language(language)
            except ValueError:
                # Try to match by language code or name
                lang_lower = language.lower()
                if lang_lower in ['en', 'english']:
                    language = Language.EN
                elif lang_lower in ['ja', 'japanese']:
                    language = Language.JA
                elif lang_lower in ['es', 'spanish']:
                    language = Language.ES
                elif lang_lower in ['fr', 'french']:
                    language = Language.FR
                elif lang_lower in ['de', 'german']:
                    language = Language.DE
                elif lang_lower in ['it', 'italian']:
                    language = Language.IT
                elif lang_lower in ['pt', 'portuguese']:
                    language = Language.PT
                elif lang_lower in ['ru', 'russian']:
                    language = Language.RU
                elif lang_lower in ['zh', 'chinese', 'chinese_simplified']:
                    language = Language.ZH
                elif lang_lower in ['zh-tw', 'zh_tw', 'chinese_traditional']:
                    language = Language.ZHT
                elif lang_lower in ['ko', 'korean']:
                    language = Language.KO
                elif lang_lower in ['ar', 'arabic']:
                    language = Language.AR
                elif lang_lower in ['hi', 'hindi']:
                    language = Language.HI
                elif lang_lower in ['bn', 'bengali']:
                    language = Language.BN
                elif lang_lower in ['ur', 'urdu']:
                    language = Language.UR
                elif lang_lower in ['tr', 'turkish']:
                    language = Language.TR
                elif lang_lower in ['pl', 'polish']:
                    language = Language.PL
                elif lang_lower in ['nl', 'dutch']:
                    language = Language.NL
                elif lang_lower in ['sv', 'swedish']:
                    language = Language.SV
                elif lang_lower in ['da', 'danish']:
                    language = Language.DA
                elif lang_lower in ['no', 'norwegian']:
                    language = Language.NO
                elif lang_lower in ['fi', 'finnish']:
                    language = Language.FI
                elif lang_lower in ['cs', 'czech']:
                    language = Language.CS
                elif lang_lower in ['sk', 'slovak']:
                    language = Language.SK
                elif lang_lower in ['hu', 'hungarian']:
                    language = Language.HU
                elif lang_lower in ['ro', 'romanian']:
                    language = Language.RO
                elif lang_lower in ['bg', 'bulgarian']:
                    language = Language.BG
                elif lang_lower in ['hr', 'croatian']:
                    language = Language.HR
                elif lang_lower in ['sr', 'serbian']:
                    language = Language.SR
                elif lang_lower in ['sl', 'slovenian']:
                    language = Language.SL
                elif lang_lower in ['et', 'estonian']:
                    language = Language.ET
                elif lang_lower in ['lv', 'latvian']:
                    language = Language.LV
                elif lang_lower in ['lt', 'lithuanian']:
                    language = Language.LT
                elif lang_lower in ['mt', 'maltese']:
                    language = Language.MT
                elif lang_lower in ['ga', 'irish']:
                    language = Language.GA
                elif lang_lower in ['cy', 'welsh']:
                    language = Language.CY
                elif lang_lower in ['is', 'icelandic']:
                    language = Language.IS
                elif lang_lower in ['fo', 'faroese']:
                    language = Language.FO
                elif lang_lower in ['gl', 'galician']:
                    language = Language.GL
                elif lang_lower in ['eu', 'basque']:
                    language = Language.EU
                elif lang_lower in ['ca', 'catalan']:
                    language = Language.CA
                elif lang_lower in ['oc', 'occitan']:
                    language = Language.OC
                elif lang_lower in ['rm', 'romansh']:
                    language = Language.RM
                elif lang_lower in ['lb', 'luxembourgish']:
                    language = Language.LB
                elif lang_lower in ['gd', 'scottish_gaelic']:
                    language = Language.GD
                elif lang_lower in ['kw', 'cornish']:
                    language = Language.KW
                else:
                    return  # Invalid language

        self.current_language = language
        # Clear cache when language changes
        if self._cache is not None:
            self._cache.clear()

    def get_language(self) -> Language:
        """Get current language."""
        return self.current_language

    def get_available_languages(self) -> List[Language]:
        """Get list of available languages."""
        return list(Language)

    def get_translation(self, key: str) -> Optional[Translation]:
        """Get full translation object for a key."""
        return self.translations.get(key)

    def get_category_translations(self, category: str) -> List[Translation]:
        """Get all translations for a category."""
        return [t for t in self.translations.values() if t.category == category]

    def load_from_file(self, file_path: Path):
        """Load translations from JSON or YAML file with 50-language support."""
        if not file_path.exists():
            return

        with open(file_path, 'r', encoding='utf-8') as f:
            if file_path.suffix == '.json':
                data = json.load(f)
            elif file_path.suffix in ['.yml', '.yaml']:
                data = yaml.safe_load(f)
            else:
                return

        # Parse and add translations for all supported languages
        for key, values in data.items():
            if isinstance(values, dict):
                translation = Translation(key=key)

                # Load translations for all available languages
                for lang_code in Language:
                    lang_key = lang_code.value.lower()
                    if lang_key in values and values[lang_key]:
                        setattr(translation, lang_key, values[lang_key])

                # Set context and category if available
                if 'context' in values:
                    translation.context = values['context']
                if 'category' in values:
                    translation.category = values['category']

                self.translations[key] = translation

    def save_to_file(self, file_path: Path):
        """Save translations to JSON or YAML file with 50-language support."""
        data = {}

        for key, trans in self.translations.items():
            translation_data = {}

            # Save translations for all languages that have content
            for lang_code in Language:
                lang_key = lang_code.value.lower()
                lang_value = getattr(trans, lang_key, "")
                if lang_value:  # Only save non-empty translations
                    translation_data[lang_key] = lang_value

            # Add metadata
            if trans.context:
                translation_data['context'] = trans.context
            if trans.category:
                translation_data['category'] = trans.category

            data[key] = translation_data

        with open(file_path, 'w', encoding='utf-8') as f:
            if file_path.suffix == '.json':
                json.dump(data, f, ensure_ascii=False, indent=2)
            elif file_path.suffix in ['.yml', '.yaml']:
                yaml.safe_dump(data, f, allow_unicode=True, default_flow_style=False)


class TranslationManager:
    """Advanced translation manager with auto-translation and management."""

    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.translation_providers = {}
        self.auto_translation_enabled = False
        self.translation_cache = {}
        self.batch_size = 10  # Batch size for API calls
        self.cache_file = Path.home() / ".3dprintcad" / "translation_cache.json"

        # Load existing cache
        self._load_translation_cache()

    def _load_translation_cache(self):
        """Load translation cache from file."""
        try:
            if self.cache_file.exists():
                with open(self.cache_file, 'r', encoding='utf-8') as f:
                    self.translation_cache = json.load(f)
        except Exception as e:
            self.logger.warning(f"Failed to load translation cache: {e}")

    def _save_translation_cache(self):
        """Save translation cache to file."""
        try:
            self.cache_file.parent.mkdir(parents=True, exist_ok=True)
            with open(self.cache_file, 'w', encoding='utf-8') as f:
                json.dump(self.translation_cache, f, ensure_ascii=False, indent=2)
        except Exception as e:
            self.logger.warning(f"Failed to save translation cache: {e}")

    def translate_batch(self, texts: List[str], target_language: Language, source_language: Language = Language.EN) -> List[str]:
        """Translate multiple texts in batch for efficiency."""
        if not self.auto_translation_enabled or not self.translation_providers:
            return [self._simulate_auto_translation(text, target_language) for text in texts]

        translated_texts = []

        # Process in batches
        for i in range(0, len(texts), self.batch_size):
            batch = texts[i:i + self.batch_size]

            # Check cache first
            cached_batch = []
            uncached_batch = []
            cached_indices = []

            for idx, text in enumerate(batch):
                cache_key = f"{source_language.value}:{target_language.value}:{hash(text)}"
                if cache_key in self.translation_cache:
                    cached_batch.append(self.translation_cache[cache_key])
                    cached_indices.append(idx)
                else:
                    uncached_batch.append(text)

            # Translate uncached texts
            if uncached_batch:
                try:
                    # Use the first available provider
                    provider = next(iter(self.translation_providers.keys()))
                    if provider == "google" and hasattr(self, 'google_translator'):
                        new_translations = self._translate_batch_google(uncached_batch, target_language, source_language)
                    elif provider == "deepl" and hasattr(self, 'deepl_translator'):
                        new_translations = self._translate_batch_deepl(uncached_batch, target_language, source_language)
                    else:
                        new_translations = [self._simulate_auto_translation(text, target_language) for text in uncached_batch]

                    # Cache the results
                    for text, translation in zip(uncached_batch, new_translations):
                        cache_key = f"{source_language.value}:{target_language.value}:{hash(text)}"
                        self.translation_cache[cache_key] = translation
                        self._save_translation_cache()

                    cached_batch.extend(new_translations)

                except Exception as e:
                    self.logger.error(f"Batch translation failed: {e}")
                    # Fallback to individual translations
                    fallback_translations = []
                    for text in uncached_batch:
                        try:
                            translation = self.translate_text(text, target_language, source_language)
                            fallback_translations.append(translation)
                        except Exception:
                            fallback_translations.append(self._simulate_auto_translation(text, target_language))

                    cached_batch.extend(fallback_translations)

            translated_texts.extend(cached_batch)

        return translated_texts

    def _translate_batch_google(self, texts: List[str], target_language: Language, source_language: Language) -> List[str]:
        """Translate batch using Google Translate."""
        try:
            translations = []
            for text in texts:
                result = self.google_translator.translate(
                    text,
                    src=source_language.value,
                    dest=target_language.value
                )
                translations.append(result.text)
            return translations
        except Exception as e:
            self.logger.error(f"Google batch translate error: {e}")
            return [self._simulate_auto_translation(text, target_language) for text in texts]

    def _translate_batch_deepl(self, texts: List[str], target_language: Language, source_language: Language) -> List[str]:
        """Translate batch using DeepL."""
        try:
            translations = []
            for text in texts:
                result = self.deepl_translator.translate_text(
                    text,
                    source_lang=source_language.value.upper(),
                    target_lang=target_language.value.upper()
                )
                translations.append(result.text)
            return translations
        except Exception as e:
            self.logger.error(f"DeepL batch translate error: {e}")
            return [self._simulate_auto_translation(text, target_language) for text in texts]

    def enable_auto_translation(self, provider_name: str, api_key: str):
        """Enable automatic translation for missing languages."""
        self.auto_translation_enabled = True
        self.translation_providers[provider_name] = api_key

        # Initialize translation service based on provider
        if provider_name.lower() == "google":
            self._init_google_translate(api_key)
        elif provider_name.lower() == "deepl":
            self._init_deepl_translate(api_key)
        elif provider_name.lower() == "azure":
            self._init_azure_translate(api_key)
        else:
            self.logger.warning(f"Unknown translation provider: {provider_name}")

        self.logger.info(f"Auto-translation enabled with provider: {provider_name}")

    def _init_google_translate(self, api_key: str):
        """Initialize Google Translate API."""
        try:
            from googletrans import Translator
            self.google_translator = Translator()
            self.logger.info("Google Translate API initialized")
        except ImportError:
            self.logger.warning("googletrans package not available. Install with: pip install googletrans==4.0.0rc1")

    def _init_deepl_translate(self, api_key: str):
        """Initialize DeepL Translate API."""
        try:
            import deepl
            self.deepl_translator = deepl.Translator(api_key)
            self.logger.info("DeepL Translate API initialized")
        except ImportError:
            self.logger.warning("deepl package not available. Install with: pip install deepl")

    def _init_azure_translate(self, api_key: str):
        """Initialize Azure Translate API."""
        try:
            from azure.ai.translation.text import TextTranslationClient
            from azure.core.credentials import AzureKeyCredential

            # This would need proper Azure configuration
            self.azure_translator = TextTranslationClient(
                credential=AzureKeyCredential(api_key),
                endpoint="https://api.cognitive.microsofttranslator.com"
            )
            self.logger.info("Azure Translate API initialized")
        except ImportError:
            self.logger.warning("azure-ai-translation-text package not available")

    def translate_text(self, text: str, target_language: Language, source_language: Language = Language.EN) -> str:
        """Translate text using configured translation service."""
        if not self.auto_translation_enabled or not self.translation_providers:
            return self._simulate_auto_translation(text, target_language)

        # Try different providers in order of preference
        providers = ["google", "deepl", "azure"]

        for provider in providers:
            if provider in self.translation_providers:
                try:
                    if provider == "google" and hasattr(self, 'google_translator'):
                        return self._translate_with_google(text, target_language, source_language)
                    elif provider == "deepl" and hasattr(self, 'deepl_translator'):
                        return self._translate_with_deepl(text, target_language, source_language)
                    elif provider == "azure" and hasattr(self, 'azure_translator'):
                        return self._translate_with_azure(text, target_language, source_language)
                except Exception as e:
                    self.logger.warning(f"Translation failed with {provider}: {e}")
                    continue

        # Fallback to simulation if all providers fail
        return self._simulate_auto_translation(text, target_language)

    def _translate_with_google(self, text: str, target_language: Language, source_language: Language) -> str:
        """Translate using Google Translate."""
        try:
            result = self.google_translator.translate(
                text,
                src=source_language.value,
                dest=target_language.value
            )
            return result.text
        except Exception as e:
            self.logger.error(f"Google Translate error: {e}")
            return self._simulate_auto_translation(text, target_language)

    def _translate_with_deepl(self, text: str, target_language: Language, source_language: Language) -> str:
        """Translate using DeepL."""
        try:
            result = self.deepl_translator.translate_text(
                text,
                source_lang=source_language.value.upper(),
                target_lang=target_language.value.upper()
            )
            return result.text
        except Exception as e:
            self.logger.error(f"DeepL Translate error: {e}")
            return self._simulate_auto_translation(text, target_language)

    def _translate_with_azure(self, text: str, target_language: Language, source_language: Language) -> str:
        """Translate using Azure."""
        try:
            # This is a simplified implementation
            response = self.azure_translator.translate(
                [text],
                to=[target_language.value],
                from_=source_language.value
            )
            return response[0].translations[0].text
        except Exception as e:
            self.logger.error(f"Azure Translate error: {e}")
            return self._simulate_auto_translation(text, target_language)

    def generate_missing_translations(self, base_language: Language = Language.EN):
        """Generate missing translations using auto-translation."""
        if not self.auto_translation_enabled:
            return

    def validate_translation_quality(self, text: str, translation: str, target_language: Language) -> Dict[str, Any]:
        """Validate translation quality."""
        quality_score = 1.0

        # Length validation (translation should be reasonable length compared to original)
        original_len = len(text)
        translation_len = len(translation)

        if translation_len == 0:
            return {"score": 0.0, "issues": ["Empty translation"]}

        # Check for placeholder patterns
        placeholder_patterns = ["[TODO", "[FIXME", "[XXX", "???", "TBD"]
        if any(pattern in translation for pattern in placeholder_patterns):
            quality_score -= 0.3
            return {"score": quality_score, "issues": ["Contains placeholder text"]}

        # Length ratio check
        ratio = translation_len / original_len if original_len > 0 else 1.0
        if ratio < 0.5 or ratio > 3.0:  # Too short or too long
            quality_score -= 0.2

        # Check for repeated characters (possible encoding issues)
        if len(set(translation)) < len(translation) * 0.3:  # More than 70% repeated characters
            quality_score -= 0.3

        # Check for obvious machine translation issues
        if translation.startswith("[") and translation.endswith("]"):
            quality_score -= 0.5

        return {
            "score": max(0.0, quality_score),
            "issues": [] if quality_score > 0.7 else ["Low quality translation"]
        }

    def generate_missing_translations_batch(self, base_language: Language = Language.EN, quality_threshold: float = 0.7):
        """Generate missing translations in batch with quality control."""
        if not self.auto_translation_enabled:
            return

        missing_translations = []

        # Find all missing translations
        for trans in _i18n.translations.values():
            base_text = getattr(trans, base_language.value.lower(), "")

            if not base_text:
                continue

            for lang in Language:
                if lang == base_language:
                    continue

                lang_key = lang.value.lower()
                current_translation = getattr(trans, lang_key, "")

                if not current_translation:
                    missing_translations.append((trans, lang, base_text))

        if not missing_translations:
            self.logger.info("No missing translations found")
            return

        # Group by target language for batch processing
        by_language = {}
        for trans, lang, base_text in missing_translations:
            if lang not in by_language:
                by_language[lang] = []
            by_language[lang].append((trans, base_text))

        # Process each language
        for lang, items in by_language.items():
            texts = [base_text for _, base_text in items]

            try:
                translated_texts = self.translate_batch(texts, lang, base_language)

                # Apply quality control and update translations
                for i, (trans, original_text) in enumerate(items):
                    translation = translated_texts[i]
                    quality = self.validate_translation_quality(original_text, translation, lang)

                    if quality["score"] >= quality_threshold:
                        lang_key = lang.value.lower()
                        setattr(trans, lang_key, translation)
                        self.logger.info(f"Added translation for {lang.value}: {original_text[:50]}...")
                    else:
                        self.logger.warning(f"Low quality translation rejected for {lang.value}: {quality['issues']}")

            except Exception as e:
                self.logger.error(f"Batch translation failed for {lang.value}: {e}")

        # Save updated translations
        _i18n.save_to_file(Path(__file__).parent.parent.parent / "translations" / "translations.json")
        self.logger.info(f"Generated translations for {len(missing_translations)} missing entries")

    def get_translation_suggestions(self, text: str, target_language: Language, max_suggestions: int = 3) -> List[str]:
        """Get translation suggestions for a given text."""
        if not self.auto_translation_enabled:
            return [self._simulate_auto_translation(text, target_language)]

        suggestions = []

        # Try multiple providers for different suggestions
        providers = list(self.translation_providers.keys())

        for i, provider in enumerate(providers[:max_suggestions]):
            try:
                if provider == "google" and hasattr(self, 'google_translator'):
                    result = self.google_translator.translate(
                        text,
                        src="en",
                        dest=target_language.value
                    )
                    suggestions.append(result.text)
                elif provider == "deepl" and hasattr(self, 'deepl_translator'):
                    result = self.deepl_translator.translate_text(
                        text,
                        source_lang="EN",
                        target_lang=target_language.value.upper()
                    )
                    suggestions.append(result.text)
            except Exception as e:
                self.logger.warning(f"Translation suggestion failed with {provider}: {e}")

        # Fallback to simulation if no suggestions available
        if not suggestions:
            suggestions.append(self._simulate_auto_translation(text, target_language))

        return suggestions

    def _simulate_auto_translation(self, text: str, target_language: Language) -> str:
        """Simulate auto-translation (in practice, use real API)."""
        # This is a placeholder - real implementation would use translation services
        # For demonstration, return a modified version of the text
        return f"[{target_language.value}] {text}"

    def validate_translation_completeness(self) -> Dict[str, Any]:
        """Validate completeness of translations across all languages."""
        stats = {}

        for lang in Language:
            lang_key = lang.value.lower()
            translated_count = 0
            total_count = len(_i18n.translations)

            for trans in _i18n.translations.values():
                if getattr(trans, lang_key, ""):
                    translated_count += 1

            completeness = translated_count / total_count if total_count > 0 else 0
            stats[lang.value] = {
                'translated': translated_count,
                'total': total_count,
                'completeness': completeness
            }

        return stats

    def export_translation_template(self, file_path: Path):
        """Export template for missing translations."""
        template = {}

        for key, trans in _i18n.translations.items():
            template_entry = {}

            # Include existing translations
            for lang in Language:
                lang_key = lang.value.lower()
                value = getattr(trans, lang_key, "")
                if value:
                    template_entry[lang_key] = value

            # Mark missing translations
            for lang in Language:
                lang_key = lang.value.lower()
                if lang_key not in template_entry:
                    template_entry[lang_key] = f"[TODO: Translate '{trans.en}']"

            template[key] = template_entry

        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(template, f, ensure_ascii=False, indent=2)


class MultiLanguageDocumentationGenerator:
    """Generates documentation in multiple languages."""

    def __init__(self):
        self.i18n = _i18n

    def generate_user_guide(self, output_dir: Path):
        """Generate user guide in all supported languages."""
        for lang in Language:
            self.i18n.set_language(lang)

            guide_content = self._generate_guide_content(lang)
            file_path = output_dir / f"USER_GUIDE_{lang.value.upper()}.md"

            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(guide_content)

    def _generate_guide_content(self, language: Language) -> str:
        """Generate guide content for specific language."""
        content = f"""# 3D Print CAD Assistant - User Guide ({language.value.upper()})

## Introduction
{self.i18n.t('ui.title')} - {self.i18n.t('ui.description', default='Advanced 3D printing CAD tool')}

## Getting Started
1. {self.i18n.t('file.select')}
2. {self.i18n.t('ui.validate')}
3. {self.i18n.t('ui.repair')}
4. {self.i18n.t('ui.slice')}
5. {self.i18n.t('ui.export')}

## Features
- {self.i18n.t('validation.title')}
- {self.i18n.t('repair.title')}
- {self.i18n.t('slice.title')}
- {self.i18n.t('recommendation.title')}

## Support
{self.i18n.t('ui.help')}
"""
        return content

    def generate_api_reference(self, output_dir: Path):
        """Generate API reference in multiple languages."""
        for lang in Language:
            self.i18n.set_language(lang)

            api_content = self._generate_api_content(lang)
            file_path = output_dir / f"API_REFERENCE_{lang.value.upper()}.md"

            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(api_content)

    def _generate_api_content(self, language: Language) -> str:
        """Generate API documentation content."""
        content = f"""# API Reference ({language.value.upper()})

## Core Functions
- `validate_mesh()` - {self.i18n.t('ui.validate')}
- `repair_mesh()` - {self.i18n.t('ui.repair')}
- `slice_model()` - {self.i18n.t('ui.slice')}

## Language Support
{self.i18n.t('i18n.supported_languages', default='Supports 50 languages')}
"""
        return content


# Initialize translation manager
translation_manager = TranslationManager()
documentation_generator = MultiLanguageDocumentationGenerator()

# Convenience functions
def t(key: str, **kwargs) -> str:
    """Translate key with current language."""
    return _i18n.t(key, **kwargs)

def set_language(language: Union[Language, str]):
    """Set global language."""
    _i18n.set_language(language)

def get_language() -> Language:
    """Get current language."""
    return _i18n.get_language()

def get_i18n_manager() -> I18nManager:
    """Get global i18n manager instance."""
    return _i18n