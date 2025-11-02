#!/usr/bin/env python3
"""Run the web server for 3D Print CAD Assistant."""
import os
import sys
import logging
import argparse
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent))

from src.web import create_app
from src.core.graceful_shutdown import get_shutdown_handler, register_cleanup

logger = logging.getLogger(__name__)


def parse_args():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(description="Run 3D Print CAD Assistant web server")
    parser.add_argument('--host', default='127.0.0.1', help='Host to bind to')
    parser.add_argument('--port', type=int, default=5000, help='Port to listen on')
    parser.add_argument('--debug', action='store_true', help='Enable debug mode')
    parser.add_argument('--config', default='development', help='Configuration name')
    return parser.parse_args()


def cleanup_resources():
    """Cleanup resources on shutdown."""
    logger.info("Cleaning up application resources")
    # Add any cleanup logic here


def main():
    """Main entry point."""
    args = parse_args()

    # Setup logging
    logging.basicConfig(
        level=logging.DEBUG if args.debug else logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )

    # Initialize graceful shutdown
    shutdown_handler = get_shutdown_handler(grace_period_seconds=30)
    register_cleanup(cleanup_resources, name="cleanup_resources")
    logger.info("Graceful shutdown handler initialized")

    # Create app
    app = create_app(args.config)

    # Configure for development
    if args.debug:
        app.config['DEBUG'] = True
        app.config['TEMPLATES_AUTO_RELOAD'] = True

    print(f"""
╔════════════════════════════════════════════════════════╗
║         3D Print CAD Assistant - Web Server           ║
╠════════════════════════════════════════════════════════╣
║                                                        ║
║  Server starting at: http://{args.host}:{args.port:<5}              ║
║  Debug mode: {'ON' if args.debug else 'OFF'}                                  ║
║                                                        ║
║  API Endpoints:                                        ║
║  • POST /api/upload     - Upload mesh file            ║
║  • POST /api/validate   - Validate mesh               ║
║  • POST /api/repair     - Repair mesh issues          ║
║  • POST /api/slice      - Generate slicing data       ║
║  • POST /api/batch      - Batch process files         ║
║                                                        ║
║  Web Interface:                                        ║
║  • /         - Home & Upload                          ║
║  • /viewer   - 3D Model Viewer                        ║
║  • /analysis - Analysis Dashboard                     ║
║                                                        ║
║  Press Ctrl+C to stop the server                      ║
╚════════════════════════════════════════════════════════╝
    """)

    # Run server
    try:
        if args.config == 'production':
            logger.warning(
                "Using Flask development server. "
                "For production, use Gunicorn/uWSGI instead."
            )
        app.run(host=args.host, port=args.port, debug=args.debug, threaded=True)
    except KeyboardInterrupt:
        print("\nServer stopped by user.")
        shutdown_handler.initiate_shutdown()
        return 0
    except Exception as e:
        logger.exception(f"Server error: {e}")
        print(f"Error: {e}", file=sys.stderr)
        return 1


if __name__ == '__main__':
    sys.exit(main())