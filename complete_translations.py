#!/usr/bin/env python3
"""Complete 50-language translations for 3D Print CAD Assistant."""

import json
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / 'src'))

from core.i18n_optimized import I18nManager, Language, TranslationManager

def main():
    """Complete translations for all 50 languages."""
    print("Completing 50-language translations...")

    # Create i18n manager and translation manager
    i18n_manager = I18nManager()
    translation_manager = TranslationManager()

    # Enable auto-translation (using simulation for now)
    print("Enabling auto-translation...")
    # Note: In production, you would use real API keys:
    # translation_manager.enable_auto_translation("google", "your-api-key")
    # translation_manager.enable_auto_translation("deepl", "your-api-key")

    # Generate missing translations
    print("Generating missing translations...")
    translation_manager.generate_missing_translations(Language.EN)

    # Export updated translations
    output_dir = Path(__file__).parent / 'translations'
    output_dir.mkdir(exist_ok=True)

    exported_files = i18n_manager.export_translations(output_dir)

    print("Translation completion completed!")
    print(f"Exported files: {list(exported_files.values())}")

    # Validate completeness
    validation = i18n_manager.validate_translations()
    print(f"\nValidation Status: {validation['overall_status']}")
    print(f"Issues: {len(validation['issues'])}")
    print(f"Warnings: {len(validation['warnings'])}")

    # Show completeness by language
    print("\nLanguage Completeness:")
    for lang, data in validation['language_completeness'].items():
        status = "✅ Complete" if data['completeness'] >= 0.9 else "⚠️  Incomplete"
        print(f"  {lang}: {data['completeness']*100:.1f}% {status}")

if __name__ == "__main__":
    main()
