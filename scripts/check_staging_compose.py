#!/usr/bin/env python3
"""Checks docker-compose.staging.yml against the Workload Security Contract of the infrastructure repository.

The static staging of the white-space page must be: non-root, read-only rootfs, unprivileged with no-new-privileges, all capabilities
dropped, bounded in memory, CPU and PIDs, on a named network, published only on the Tailscale address, with no bind mount, no
volume, no secret and no environment. The rules are those of the contract, applied to the rendered configuration.

  python scripts/check_staging_compose.py [COMPOSE_FILE] [--local]
"""

import json
import os
import re
import subprocess
import sys
from pathlib import Path

DEFAULT = Path(__file__).resolve().parents[1] / "docker-compose.staging.yml"
EXPECTED_SERVICES = {"web"}
TAILSCALE_ADDRESS = "100.119.147.8"  # the Lenovo, as in the infrastructure repository
EXPECTED_PORT = {"published": "8081", "target": 8080, "protocol": "tcp"}


def violations(config: dict, local: bool = False) -> list[str]:
    """Contract violations of a rendered compose configuration (`docker compose config --format json`).

    Staging publishes exactly one port, 8081 to 8080/tcp, on the Tailscale address. `local` also allows 127.0.0.1 as the address, for
    a run on a developer machine; it is never the staging configuration.
    """
    found: list[str] = []
    services = config.get("services", {})
    if set(services) != EXPECTED_SERVICES:
        found.append(f"services must be exactly {sorted(EXPECTED_SERVICES)}, found {sorted(services)}")
    for name, svc in services.items():
        if not re.fullmatch(r"[1-9][0-9]*:[1-9][0-9]*", str(svc.get("user", ""))):
            found.append(f"{name}: rule 1, a numeric non-root uid:gid is required")
        if svc.get("read_only") is not True:
            found.append(f"{name}: rule 2, read_only must be true")
        if svc.get("privileged"):
            found.append(f"{name}: rule 3, privileged is forbidden")
        if not any(str(o).startswith("no-new-privileges") for o in svc.get("security_opt", [])):
            found.append(f"{name}: rule 3, no-new-privileges is required")
        if "ALL" not in svc.get("cap_drop", []) or svc.get("cap_add"):
            found.append(f"{name}: rule 4, cap_drop ALL and no cap_add are required")
        if not (svc.get("mem_limit") and (svc.get("cpus") or svc.get("cpu_quota")) and svc.get("pids_limit")):
            found.append(f"{name}: rule 5, memory, CPU and PID limits are required")
        if svc.get("network_mode") or not svc.get("networks"):
            found.append(f"{name}: rule 6, a named network is required and network_mode is forbidden")
        allowed_ips = {TAILSCALE_ADDRESS, "127.0.0.1"} if local else {TAILSCALE_ADDRESS}
        ports = svc.get("ports", [])
        if len(ports) != 1:
            found.append(f"{name}: rule 6, exactly one published port is expected, found {len(ports)}")
        for port in ports:
            if port.get("host_ip") not in allowed_ips:
                found.append(
                    f"{name}: rule 6, port {port.get('published')} must bind to {sorted(allowed_ips)}, found {port.get('host_ip')!r}"
                )
            wrong = {k: port.get(k) for k, v in EXPECTED_PORT.items() if str(port.get(k)) != str(v)}
            if wrong:
                found.append(f"{name}: rule 6, the published port must be 8081 to 8080/tcp, differs in {wrong}")
        if svc.get("volumes"):
            found.append(f"{name}: rule 7, no volume or bind mount is needed by a static page")
        if svc.get("environment") or svc.get("env_file") or svc.get("secrets"):
            found.append(f"{name}: a static page needs no environment, env_file or secret")
    if config.get("volumes") or config.get("secrets"):
        found.append("top-level volumes or secrets are not expected")
    return found


def main() -> int:
    args = [a for a in sys.argv[1:] if a != "--local"]
    local = len(args) < len(sys.argv) - 1
    compose = Path(args[0]) if args else DEFAULT
    env = {**os.environ, "TAILSCALE_BIND_IP": TAILSCALE_ADDRESS}
    rendered = subprocess.run(
        ["docker", "compose", "-f", str(compose), "config", "--format", "json"],
        env=env,
        capture_output=True,
        text=True,
        check=True,
    ).stdout
    problems = violations(json.loads(rendered), local)
    for problem in problems:
        print(problem)
    print("contract: FAIL" if problems else "contract: OK")
    return 1 if problems else 0


if __name__ == "__main__":
    raise SystemExit(main())
