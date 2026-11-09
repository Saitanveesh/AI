"""CLI intentionally binds to loopback; use authenticated SSH forwarding for access."""
from __future__ import annotations

import argparse
import json
import sys

from .config import Settings


def main() -> None:
    parser = argparse.ArgumentParser(
        description="EdgeWatch passive edge-vision observation service")
    parser.add_argument("command", choices=("serve", "check"), nargs="?", default="serve")
    parser.add_argument("--port", type=int, default=8090)
    args = parser.parse_args()
    try:
        settings = Settings.from_env()
        settings.validate_inputs()
    except (ValueError, FileNotFoundError) as exc:
        print(f"Configuration error: {exc}", file=sys.stderr)
        raise SystemExit(2) from exc
    if args.command == "check":
        print(json.dumps({
            "valid": True, "source": settings.source,
            "inference": settings.detector,
            "width": settings.width, "height": settings.height,
            "fps": settings.fps,
            "privacy_masks": len(settings.privacy_masks),
        }, indent=2))
        return
    if not (1 <= args.port <= 65535):
        parser.error("Port must be between 1 and 65535")
    import uvicorn
    from .api import create_app
    uvicorn.run(create_app(settings), host="127.0.0.1", port=args.port,
                access_log=False, server_header=False)


if __name__ == "__main__":
    main()
