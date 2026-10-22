"""Entry point of the ADR 0037 gate 1 benchmark. SKELETON: it refuses to run until the protocol is authorised, and the
workloads are not implemented yet (they are written after the protocol PR is merged and reviewed).

Return codes: 0 pass, 1 an acceptance check failed, 2 refused (not authorised), 3 environment incident.
"""
import sys

from harness.contract import EXIT_INCIDENT, EXIT_REFUSED
from harness.guard import NotAuthorised, require_authorisation


def main() -> int:
    try:
        require_authorisation()
    except NotAuthorised as exc:
        print(f"refused: {exc}", file=sys.stderr)
        return EXIT_REFUSED
    print("workloads W1-W7 are not implemented in this skeleton", file=sys.stderr)
    return EXIT_INCIDENT


if __name__ == "__main__":
    raise SystemExit(main())
