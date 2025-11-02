#!/usr/bin/env python3
"""Quick automation script for batch processing."""
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.core.automation import process_batch
import argparse


def main():
    parser = argparse.ArgumentParser(
        description='Automated batch processing for 3D models'
    )
    parser.add_argument(
        'input_dir',
        type=Path,
        help='Input directory containing mesh files'
    )
    parser.add_argument(
        '-o', '--output-dir',
        type=Path,
        help='Output directory for processed files'
    )
    parser.add_argument(
        '-r', '--repair',
        action='store_true',
        help='Enable auto-repair mode'
    )
    parser.add_argument(
        '-p', '--pattern',
        default='*.stl',
        help='File pattern to match (default: *.stl)'
    )

    args = parser.parse_args()

    print(f"Processing files in: {args.input_dir}")
    if args.repair:
        print("Auto-repair: ENABLED")

    result = process_batch(
        args.input_dir,
        output_dir=args.output_dir,
        auto_repair=args.repair
    )

    if result.get('success'):
        print(f"\n✓ Processing complete:")
        print(f"  Total files: {result['total_files']}")
        print(f"  Processed: {result['processed']}")
        print(f"  Valid: {result['valid']}")
        if args.repair:
            print(f"  Repaired: {result['repaired']}")
        print(f"  Failed: {result['failed']}")
    else:
        print(f"\n✗ Processing failed: {result.get('error')}")
        sys.exit(1)


if __name__ == '__main__':
    main()
