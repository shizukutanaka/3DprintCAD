#!/usr/bin/env python3
"""Export translation data for 3D Print CAD Assistant."""

import json
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / 'src'))

from core.i18n_optimized import I18nManager, Language

def main():
    """Export translation data."""
    print("Exporting translation data...")

    # Create i18n manager
    i18n_manager = I18nManager()

    # Export translations to files
    output_dir = Path(__file__).parent / 'translations'
    output_dir.mkdir(exist_ok=True)

    exported_files = {}

    # Export all translations as JSON
    all_translations_file = output_dir / "translations.json"
    i18n_manager.save_to_file(all_translations_file)
    exported_files["all"] = all_translations_file
    print(f"Exported all translations to: {all_translations_file}")

    # Export by language
    for lang in Language:
        lang_translations = {}

        for key, trans in i18n_manager.translations.items():
            lang_key = lang.value.lower()
            lang_value = getattr(trans, lang_key, "")

            if lang_value:  # Only include non-empty translations
                lang_translations[key] = lang_value

        if lang_translations:
            lang_file = output_dir / f"translations_{lang.value}.json"
            with open(lang_file, 'w', encoding='utf-8') as f:
                json.dump(lang_translations, f, ensure_ascii=False, indent=2)
            exported_files[lang.value] = lang_file
            print(f"Exported {lang.value} translations to: {lang_file}")

    print(f"\nExported {len(exported_files)} translation files:")
    for lang, file_path in exported_files.items():
        print(f"  {lang}: {file_path}")

    # Show translation completeness stats
    print("\nTranslation completeness:")
    for lang in Language:
        lang_key = lang.value.lower()
        translated_count = 0
        total_count = len(i18n_manager.translations)

        for trans in i18n_manager.translations.values():
            if getattr(trans, lang_key, ""):
                translated_count += 1

        completeness = translated_count / total_count if total_count > 0 else 0
        status = "Complete" if completeness >= 0.9 else "Incomplete"
        print(f"  {lang.value}: {translated_count}/{total_count} ({completeness*100:.1f}%) - {status}")

if __name__ == "__main__":
    main()
