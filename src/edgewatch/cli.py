"""Safe CLI: localhost service, read-only diagnostics, and passive benchmarks."""
from __future__ import annotations

import argparse
import json
import sys

from .config import Settings


def main() -> None:
    parser = argparse.ArgumentParser(
        description="EdgeWatch passive edge-vision observation service")
    parser.add_argument("command", choices=("serve", "check", "doctor", "benchmark", "evaluate"),
                        nargs="?", default="serve")
    parser.add_argument("--port", type=int, default=8090)
    parser.add_argument("--frames", type=int, default=300,
                        help="Maximum offline benchmark frames (1..10000)")
    parser.add_argument("--dataset", default="", help="Offline JSONL annotation file")
    parser.add_argument("--iou", type=float, default=0.5)
    parser.add_argument("--confidence", type=float, default=0.5)
    args = parser.parse_args()

    if args.command == "evaluate":
        if not args.dataset:
            parser.error("Evaluation requires --dataset PATH")
        from .evaluation import evaluate_file
        try:
            print(json.dumps(evaluate_file(args.dataset, args.iou, args.confidence),
                             indent=2))
        except (OSError, ValueError) as exc:
            print(f"Evaluation failed: {type(exc).__name__}: {exc}", file=sys.stderr)
            raise SystemExit(1) from exc
        return

    if args.command == "doctor":
        from .diagnostics import collect_diagnostics
        print(json.dumps(collect_diagnostics(), indent=2))
        return

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

    if args.command == "benchmark":
        if not (1 <= args.frames <= 10000):
            parser.error("Benchmark frame count must be 1..10000")
        from .benchmark import benchmark
        try:
            print(json.dumps(benchmark(settings, max_frames=args.frames), indent=2))
        except (RuntimeError, OSError, ValueError) as exc:
            print(f"Benchmark failed: {type(exc).__name__}: {exc}", file=sys.stderr)
            raise SystemExit(1) from exc
        return

    if not (1 <= args.port <= 65535):
        parser.error("Port must be between 1 and 65535")
    import uvicorn
    from .api import create_app
    uvicorn.run(create_app(settings), host="127.0.0.1", port=args.port,
                access_log=False, server_header=False)


if __name__ == "__main__":
    main()
