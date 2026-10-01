import argparse
from pathlib import Path

import uvicorn

from infrastructure.operational.app import create_mvp_app


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Nexus MVP: demand to Spanish assets.")
    parser.add_argument("--artifacts", type=Path, required=True, help="verified operational corpus directory")
    parser.add_argument("--static", type=Path, help="built frontend (frontend/dist); API only when omitted")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8080)
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> None:
    args = parse_args(argv)
    uvicorn.run(create_mvp_app(args.artifacts, args.static), host=args.host, port=args.port)


if __name__ == "__main__":
    main()
