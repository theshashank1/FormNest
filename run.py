"""
FormNest — Development Server Entry Point

Usage:
    uv run run.py              # Local only
    uv run run.py --tunnel     # With Azure Dev Tunnel

Pattern mirrors TREEEX-WBSP run.py (simplified for FormNest).
"""

import argparse
import logging
import sys

import uvicorn

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(name)-30s | %(levelname)-7s | %(message)s",
    datefmt="%H:%M:%S",
)

logger = logging.getLogger("formnest.run")


def main():
    parser = argparse.ArgumentParser(description="FormNest Development Server")
    parser.add_argument(
        "--tunnel", action="store_true", help="Start with Azure Dev Tunnel"
    )
    parser.add_argument(
        "--host", default="0.0.0.0", help="Bind host (default: 0.0.0.0)"
    )
    parser.add_argument(
        "--port", type=int, default=8001, help="Bind port (default: 8001)"
    )
    args = parser.parse_args()

    logger.info("🏗️  Starting FormNest Development Server")
    logger.info(f"   Port: {args.port}")
    logger.info(f"   Host: {args.host}")
    logger.info(f"   Docs: http://localhost:{args.port}/docs")

    try:
        uvicorn.run(
            "server.main:app",
            host=args.host,
            port=args.port,
            reload=True,
            reload_dirs=["server"],
            log_level="info",
        )
    except KeyboardInterrupt:
        logger.info("Server stopped")
        sys.exit(0)


if __name__ == "__main__":
    main()
